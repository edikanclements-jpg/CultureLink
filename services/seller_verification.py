"""Ten source-backed checks; an integer evidence score for every seller.

No network, API token, paid service, buyer data, or database writes. Missing
evidence earns zero for a check rather than withholding an overall score.
"""
from datetime import date
import re
from urllib.parse import urlsplit

from services.instagram_review import account_for
from services.seller_evidence_data import REVIEWS


CATEGORIES = (
    ("presence", "Account presence", (
        ("profile_supplied", "Instagram link supplied"),
        ("profile_public", "Public account corroborated"),
    )),
    ("catalog", "Catalog & ordering", (
        ("catalog_records", "Three complete CultureLink listings"),
        ("order_method", "Ordering or booking instructions"),
    )),
    ("contact_terms", "Contact & policies", (
        ("contact", "Public contact channel"),
        ("terms", "Return or transaction terms disclosed"),
    )),
    ("activity", "Public activity & references", (
        ("posting_history", "At least three public posts listed"),
        ("outside_reference", "Outside publication or reference"),
    )),
    ("customer", "Customer & fulfillment evidence", (
        ("client_experience", "Specific published client experience"),
        ("order_record", "Redacted order and fulfillment evidence reviewed"),
    )),
)


def _review_date(value):
    try:
        return date.fromisoformat(value) if isinstance(value, str) else None
    except ValueError:
        return None


def _source(value, today):
    if not isinstance(value, dict):
        return None
    url = value.get("url")
    label = value.get("label")
    checked = _review_date(value.get("checked_on"))
    if (not isinstance(url, str) or not isinstance(label, str) or not label.strip()
            or len(url) > 1500 or any(ord(c) < 32 or c == "\\" for c in url)
            or not checked or checked > today):
        return None
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
                or parsed.port is not None):
            return None
    except ValueError:
        return None
    kind = value.get("kind", "seller_page")
    return {"label": label[:160], "url": url, "kind": kind[:40] if isinstance(kind, str) else "unknown",
            "checked_on": checked.isoformat(), "redacted": value.get("redacted") is True,
            "reviewed_by_team": value.get("reviewed_by_team") is True}


def review_for(boutique, today=None, reviews=None):
    today = today or date.today()
    identifier = boutique.get("boutique_id")
    valid_id = isinstance(identifier, int) and not isinstance(identifier, bool) and 0 < identifier <= 4294967295
    account = account_for(boutique) if valid_id else None
    collection = REVIEWS if reviews is None else reviews if isinstance(reviews, dict) else {}
    raw = collection.get(identifier, {}) if valid_id else {}
    if (not account or not isinstance(raw, dict) or raw.get("name") != account["name"]
            or raw.get("handle") != account["handle"]):
        raw = {}
    reviewed = _review_date(raw.get("reviewed_on"))
    if reviewed and reviewed > today:
        raw, reviewed = {}, None
    raw_sources = raw.get("sources", {})
    sources = {key: normalized for key, value in raw_sources.items()
               if isinstance(key, str) and (normalized := _source(value, today))} if isinstance(raw_sources, dict) else {}
    products = boutique.get("products")
    products = products if isinstance(products, (list, tuple)) else []
    complete = {p["product_id"]: p for p in products if valid_id and isinstance(p, dict)
                and isinstance(p.get("product_id"), int) and not isinstance(p["product_id"], bool)
                and p["product_id"] > 0 and all(isinstance(p.get(key), str) and p[key].strip()
                for key in ("product_name", "description", "image_url"))}
    catalog_source = {"label": "CultureLink catalog (team-entered records)",
                      "url": "/boutiques/" + str(identifier) + "#collection-heading" if valid_id else "/boutiques",
                      "kind": "team_catalog", "checked_on": today.isoformat()}
    if len(complete) >= 3:
        sources["catalog"] = catalog_source
    if account:
        sources["supplied"] = {"label": "Instagram link supplied by the project team", "url": account["url"],
                               "kind": "team_provided", "checked_on": "2026-11-02"}
    observations = raw.get("checks", {})
    if not isinstance(observations, dict):
        observations = {}
    confirmed_profile = sources.get("profile")
    if confirmed_profile and account:
        parsed = urlsplit(confirmed_profile["url"])
        if (parsed.hostname not in {"instagram.com", "www.instagram.com"}
                or parsed.path.rstrip("/").casefold() != "/" + account["handle"]
                or confirmed_profile["kind"] != "public_profile"):
            confirmed_profile = None
    results = []
    for key, label, definitions in CATEGORIES:
        checks = []
        for check_id, check_label in definitions:
            observation = observations.get(check_id, {})
            if not isinstance(observation, dict):
                observation = {}
            references = observation.get("sources", [])
            references = [ref for ref in references if isinstance(ref, str) and ref in sources] if isinstance(references, list) else []
            passed = observation.get("confirmed") is True and bool(references)
            note = observation.get("note", "")
            note = note[:600] if isinstance(note, str) else ""
            if check_id == "profile_supplied":
                passed, references, note = bool(account), ["supplied"] if account else [], "The project team supplied this profile link. This does not prove account ownership."
            elif check_id == "catalog_records":
                passed = len(complete) >= 3
                references = ["catalog"] if passed else []
                note = f"{len(complete)} catalog records have a name, description and image reference. These are project-entered listings, not sales records."
            elif check_id == "profile_public":
                passed = passed and confirmed_profile is not None and "profile" in references
            elif check_id == "posting_history":
                count = raw.get("post_count")
                passed = confirmed_profile is not None and isinstance(count, int) and not isinstance(count, bool) and count >= 3
                references = ["profile"] if passed else []
                note = f"The reviewed public profile listed {count:,} cumulative posts. This is not a count of recent posts or customer interactions." if passed else "A usable public post total has not been confirmed."
            elif check_id == "outside_reference":
                passed = passed and any(sources[ref]["kind"] in {"outside_reference", "customer_report"} for ref in references)
            elif check_id == "client_experience":
                passed = passed and any(sources[ref]["kind"] == "customer_report" for ref in references)
            elif check_id == "order_record":
                passed = passed and any(sources[ref]["kind"] == "reviewed_fulfillment" and sources[ref]["redacted"]
                                        and sources[ref]["reviewed_by_team"] for ref in references)
            checks.append({"id": check_id, "label": check_label, "points": 10 if passed else 0,
                           "maximum": 10, "state": "Documented" if passed else "Not confirmed",
                           "note": note or ("Evidence has not been confirmed for this check." if not passed else ""),
                           "sources": [sources[ref] for ref in dict.fromkeys(references)] if passed else []})
        results.append({"id": key, "label": label, "score": sum(c["points"] for c in checks),
                        "maximum": 20, "checks": checks})
    score = sum(category["score"] for category in results)
    checks = [check for category in results for check in category["checks"]]
    follower_label = raw.get("followers_label")
    if not confirmed_profile or not isinstance(follower_label, str) or not re.fullmatch(r"[0-9][0-9,.]*[KMB]?", follower_label):
        follower_label = None
    source_urls = {s["url"] for check in checks for s in check["sources"] if s["kind"] not in {"team_catalog", "team_provided"}}
    return {"score": int(score), "maximum": 100, "categories": results,
            "tier": "Well documented" if score >= 80 else "Partly documented" if score >= 50 else "Limited evidence",
            "documented_checks": sum(check["points"] > 0 for check in checks), "total_checks": 10,
            "reviewed_on": reviewed.isoformat() if reviewed else None,
            "review_due": bool(reviewed and (today - reviewed).days > 90),
            "public_source_count": len(source_urls), "account": account,
            "followers_label": follower_label, "followers_approximate": raw.get("followers_approximate") is True,
            "post_count": raw.get("post_count") if confirmed_profile and isinstance(raw.get("post_count"), int) and not isinstance(raw.get("post_count"), bool) and 0 <= raw["post_count"] <= 10**9 else None,
            "order_records_reviewed": next(c["points"] > 0 for c in checks if c["id"] == "order_record"),
            "notes": [n[:400] for n in raw.get("notes", []) if isinstance(n, str)] if isinstance(raw.get("notes", []), list) else []}
