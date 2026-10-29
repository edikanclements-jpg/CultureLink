"""Catalog-grounded shopping guide, with optional AI interpretation only."""
from decimal import Decimal, InvalidOperation
import re

from flask import current_app

from services.account_security import AttemptLimiter
from services.products import get_all_products
from services import shopping_ai

TEXT_FIELDS = shopping_ai.FILTER_TEXT
PRICE_FIELDS = ("min_price", "max_price")
HELP = {
    "help": "Tell me a culture, occasion, color, seller, or budget. For example: Indian wedding pieces under USD 150. Turn off Refine these results to start a different search.",
    "price_help": "Price to be determined means the catalog doesn't have a confirmed price. Contact the seller before deciding. I leave unknown prices out of budget matches.",
    "size_help": "Catalog sizes are listing labels, not a fit guarantee. Size to be determined means measurements still need confirmation. Open the piece and confirm sizing with the seller.",
    "verification_help": "CultureLink's seller verification system is still being developed. A catalog listing does not mean a seller has been verified. You can open the seller's page to review the links currently provided.",
    "unsupported": "I can help you find catalog pieces by culture, occasion, color, size label, seller, location, or budget. Try naming what you'd like. For detailed comparisons, save pieces and use Compare in your Closet.",
}
NUMBER = r"(\d[\d,]*(?:\.\d{1,2})?)"
MONEY = r"(?:(USD|INR|\$|₹)\s*)?" + NUMBER
STOP_WORDS = set("i im i'm am a an the me my for to of in on at with and or please show find looking look want need like something some pieces piece clothes clothing outfit outfits options option can could you recommend recommendations wearing wear shopping buy get see only just instead actually now about what how more any is it under below up less than maximum max minimum min budget within most least from between above over usd inr dollars dollar rupees rupee us wedding weddings festival festivals formal casual party parties blue red green yellow gold pink purple black white ivory cream orange brown beige burgundy maroon navy silver lavender teal mustard offwhite indian india nigerian nigeria korean korea dress dresses saree sarees sari saris lehenga lehengas kurta kurtas anarkali gown gowns skirt skirts top tops set sets suit suits sarees saree".split())
STOP_WORDS.update("do have has available that are as will would should be color colors colours coloured colored prefer preferably maybe then also these this those such guest guests remove clear all no price prices size label labels culture cultures occasion occasions".split())


class GuideInputError(Exception):
    pass


def empty_filters():
    return {**{key: "" for key in TEXT_FIELDS}, **{key: None for key in PRICE_FIELDS}}


def validate_filters(value):
    if not isinstance(value, dict) or set(value) != set(TEXT_FIELDS + PRICE_FIELDS):
        raise GuideInputError("Please start a new search and try again.")
    result = {}
    for key in TEXT_FIELDS:
        text = value[key]
        if not isinstance(text, str) or len(text) > 100 or any(ord(char) < 32 or ord(char) == 127 for char in text):
            raise GuideInputError("Please use short, normal search terms.")
        result[key] = text.strip()
    if result["currency"] not in {"", "USD", "INR"}:
        raise GuideInputError("Choose USD or INR for a budget search.")
    for key in PRICE_FIELDS:
        price = value[key]
        if price is None:
            result[key] = None
            continue
        if isinstance(price, bool) or not isinstance(price, (str, int, float, Decimal)):
            raise GuideInputError("Use a number for your budget.")
        try:
            number = Decimal(str(price))
        except InvalidOperation:
            raise GuideInputError("Use a number for your budget.") from None
        if not number.is_finite() or not 0 <= number <= 10000000:
            raise GuideInputError("Use a budget between 0 and 10,000,000.")
        result[key] = format(number, "f")
    if result["min_price"] is not None and result["max_price"] is not None and Decimal(result["min_price"]) > Decimal(result["max_price"]):
        raise GuideInputError("The minimum budget must be less than the maximum.")
    return result


def catalog_facets(products):
    mapping = {"culture": "culture", "occasion": "occasion", "color": "color", "clothing_type": "clothing_type", "size": "size", "location": "seller_location", "seller": "boutique_name"}
    return {key: sorted({part.strip()[:100] for product in products for part in str(product.get(field) or "").split(",") if part.strip()})[:50] for key, field in mapping.items()}


def _contains(text, value):
    return bool(re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", text, flags=re.I))


def requested_currency(text):
    if re.search(r"\b(?:EUR|GBP|CAD|AUD|NGN|naira|euros?|pounds?|(?:Canadian|Australian)\s+dollars?)\b|[€£₦]", text, flags=re.I):
        raise GuideInputError("This catalog supports budget searches in USD or INR. Choose one of those currencies.")
    has_inr = bool(re.search(r"\binr\b|\brupees?\b|₹", text, flags=re.I))
    has_usd = bool(re.search(r"\busd\b|\bdollars?\b|\$", text, flags=re.I))
    if has_inr and has_usd:
        raise GuideInputError("Choose one currency per search: USD or INR.")
    return "INR" if has_inr else "USD" if has_usd else ""


def local_intent(text, previous, facets):
    lower = text.casefold()
    result = dict(previous)
    if re.search(r"\b(tbd|determined|unknown price|price mean)\b", lower):
        return {"action": "price_help", "filters": result}
    if re.search(r"\b(fit me|my measurements|my size|size mean|sizing|measurements)\b", lower):
        return {"action": "size_help", "filters": result}
    if re.search(r"\b(verified|verification|trustworthy|trust|reviews|real sales|followers)\b", lower):
        return {"action": "verification_help", "filters": result}
    if re.fullmatch(r"\s*(help|hi|hello|how does this work|what can you do)[?!.\s]*", lower):
        return {"action": "help", "filters": result}
    if re.search(r"\b(not|without|except|excluding|cheapest|cheaper|best|compare)\b", lower):
        return {"action": "unsupported", "filters": result}
    consumed = lower
    for field in ("color", "culture", "occasion", "size", "location"):
        consumed, cleared = re.subn(r"\b(?:any|all|remove|clear)\s+(?:the\s+)?" + field + r"s?\b", " ", consumed)
        if cleared:
            result[field] = ""
    consumed, cleared_budget = re.subn(r"\b(?:(?:no|remove|clear)\s+(?:the\s+)?budget|(?:any|all)\s+prices?)\b", " ", consumed)
    if cleared_budget:
        result.update(min_price=None, max_price=None, currency="")
    aliases = {"india": "Indian", "nigeria": "Nigerian", "korea": "Korean", "weddings": "Wedding", "festivals": "Festival", "parties": "Party", "dresses": "Dress", "gowns": "Gown", "sari": "Saree", "saris": "Saree", "sarees": "Saree", "lehengas": "Lehenga", "kurtas": "Kurta", "tops": "Top", "skirts": "Skirt", "sets": "Set", "suits": "Suit"}
    for alias, canonical in aliases.items():
        consumed = re.sub(r"(?<!\w)" + re.escape(alias) + r"(?!\w)", canonical.casefold(), consumed)
    known_colors = "blue red green yellow gold pink purple black white ivory cream orange brown beige burgundy maroon navy silver lavender teal mustard".split()
    def canonical_values(known, extra):
        canonical = {value.casefold(): value for value in extra}
        canonical.update({value.casefold(): value for value in known})
        return list(canonical.values())
    choices = {**facets, "culture": canonical_values(facets["culture"], ["Indian", "Nigerian", "Korean"]),
               "color": canonical_values(facets["color"], known_colors),
               "clothing_type": canonical_values(facets["clothing_type"], ["Dress", "Gown", "Saree", "Lehenga", "Kurta", "Anarkali", "Skirt", "Top", "Set", "Suit"])}
    for field in ("culture", "occasion", "color", "clothing_type", "size", "location", "seller"):
        matches = [value for value in choices[field] if _contains(consumed, value)]
        if matches:
            # Multiple distinct requested values need a clarification, not a guess.
            matches.sort(key=lambda value: (-len(value), value.casefold()))
            chosen = matches[0]
            unrelated = [value for value in matches[1:] if value.casefold() not in chosen.casefold()]
            if unrelated and field in {"culture", "occasion", "color"}:
                return {"action": "unsupported", "filters": result}
            result["keyword" if field == "seller" else field] = chosen
            consumed = re.sub(re.escape(chosen.casefold()), " ", consumed)
    currency = requested_currency(text)
    if currency:
        result["currency"] = currency
    if re.search(r"\b(under|below|over|above|budget|max|minimum)\s*(?:usd|inr|\$|₹)?\s*-", lower):
        raise GuideInputError("Use a positive number for your budget.")
    pair = re.search(r"\bbetween\s*" + MONEY + r"\s*(?:and|to|-)\s*" + MONEY, text, flags=re.I)
    upper = re.search(r"\b(?:under|below|up to|at most|less than|no more than|max(?:imum)?|budget(?: of)?|within)\s*" + MONEY, text, flags=re.I)
    lower_bound = re.search(r"\b(?:over|above|at least|min(?:imum)?)\s*" + MONEY, text, flags=re.I)
    single = re.search(r"(?:USD|INR|\$|₹)\s*" + NUMBER, text, flags=re.I)
    if pair:
        result["min_price"], result["max_price"] = pair[2].replace(",", ""), pair[4].replace(",", "")
    else:
        if upper:
            result["max_price"] = upper[2].replace(",", "")
        elif single and not lower_bound:
            result["max_price"] = single[1].replace(",", "")
        if lower_bound:
            result["min_price"] = lower_bound[2].replace(",", "")
    residual = [word for word in re.findall(r"[a-z]+", consumed) if word not in STOP_WORDS and len(word) > 1]
    if residual:
        result["keyword"] = " ".join(residual)[:100]
    return {"action": "search", "filters": validate_filters(result)}


def match_products(products, filters):
    matches = []
    unknown_prices = 0
    has_budget = any(filters[key] is not None for key in PRICE_FIELDS)
    for product in products:
        if filters["culture"] and (product.get("culture") or "").casefold() != filters["culture"].casefold():
            continue
        if filters["occasion"] and filters["occasion"].casefold() not in [value.strip().casefold() for value in (product.get("occasion") or "").split(",")]:
            continue
        if any(filters[key] and filters[key].casefold() not in (product.get(field) or "").casefold() for key, field in (("color", "color"), ("clothing_type", "clothing_type"), ("location", "seller_location"))):
            continue
        if filters["size"] and filters["size"].casefold() not in [value.strip().casefold() for value in (product.get("size") or "").split(",")]:
            continue
        words = filters["keyword"].casefold().split()
        haystack = " ".join(str(product.get(key) or "") for key in ("product_name", "description", "boutique_name", "clothing_type")).casefold()
        if any(word not in haystack for word in words):
            continue
        price = product.get("price")
        if has_budget and (price is None or price <= 0):
            unknown_prices += 1
            continue
        if filters["currency"] and product["price_currency"] != filters["currency"]:
            continue
        if filters["min_price"] is not None and price < Decimal(filters["min_price"]):
            continue
        if filters["max_price"] is not None and price > Decimal(filters["max_price"]):
            continue
        matches.append(product)
    return sorted(matches, key=lambda product: (product["product_name"].casefold(), product["product_id"])), unknown_prices


def result_for(filters, query="", mode="catalog", notice="", action="search"):
    products = get_all_products()
    filters = validate_filters(filters)
    needs_currency = any(filters[key] is not None for key in PRICE_FIELDS) and not filters["currency"]
    if action in HELP:
        reply, matches, unknown = HELP[action], [], 0
    elif needs_currency:
        reply, matches, unknown = "Which currency is your budget in: USD or INR? Choose one below so I can compare the right prices.", [], 0
    else:
        matches, unknown = match_products(products, filters)
        count = len(matches)
        if not query:
            reply, matches = "Tell me what you're looking for, and we'll find a starting point together.", []
        elif count:
            reply = f"I found {count} {'piece' if count == 1 else 'pieces'} matching the search details below. Open a piece for more information or save a favorite to your Closet."
        else:
            reply = "I couldn't find a piece matching all those details in the current catalog. Try changing a color or budget, or start a new search."
    criteria = []
    labels = {"culture": "Culture", "occasion": "Occasion", "color": "Color", "clothing_type": "Clothing", "size": "Size label", "location": "Location", "keyword": "Keywords", "currency": "Currency"}
    for key in TEXT_FIELDS:
        if filters[key]:
            criteria.append(labels[key] + ": " + filters[key])
    for key, label in (("min_price", "From"), ("max_price", "Up to")):
        if filters[key] is not None:
            criteria.append(label + ": " + (filters["currency"] + " " if filters["currency"] else "") + filters[key])
    return {"filters": filters, "query": query, "mode": mode, "notice": notice, "action": action, "reply": reply,
            "needs_currency": needs_currency and action == "search", "products": matches[:6], "total": len(matches), "unknown_prices": unknown, "criteria": criteria}


def answer(text, previous, user_id, use_ai=True):
    if not isinstance(text, str) or not text.strip() or len(text) > 400 or any((ord(char) < 32 and char not in "\n\r\t") or ord(char) == 127 for char in text):
        raise GuideInputError("Describe what you'd like in 1 to 400 characters.")
    text = " ".join(text.split())
    explicit_currency = requested_currency(text)
    previous = validate_filters(previous)
    products = get_all_products()
    facets = catalog_facets(products)
    mode, notice = "catalog", ""
    config = shopping_ai.settings()
    if config["key"] and use_ai:
        limiter = current_app.extensions.setdefault("shopping_ai_attempts", AttemptLimiter())
        blocked = limiter.consume("buyer:" + str(user_id), 20, 3600) or limiter.consume("all-buyers", 100, 3600)
        if blocked:
            notice = "AI requests are paused for a little while. Catalog search is still available."
        else:
            try:
                intent = shopping_ai.extract_intent(text, previous, facets, config)
                filters = validate_filters(intent["filters"])
                # An AI extraction cannot guess or silently change the currency.
                cleared_budget = any(previous[key] is not None for key in PRICE_FIELDS) and all(filters[key] is None for key in PRICE_FIELDS)
                filters["currency"] = explicit_currency or ("" if cleared_budget else previous["currency"])
                mode = "ai"
            except (shopping_ai.AIUnavailable, GuideInputError):
                notice = "AI language understanding isn't available right now. These results use catalog search."
    if mode == "catalog":
        intent = local_intent(text, previous, facets)
        filters = intent["filters"]
    return result_for(filters, text, mode, notice, intent["action"])
