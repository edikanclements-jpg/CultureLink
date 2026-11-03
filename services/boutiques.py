"""Akhil's seller queries, enriched with each seller's real catalog items."""

from database import get_db_connection
from services.products import get_all_products, get_products_for_seller, safe_http_url
from services.profiles import public_seller_profiles
from services.instagram_review import account_for
from services.seller_verification import review_for
from services.catalog_rules import seller_location
from services.seller_timing import timing_for
from services.profile_images import public_seller_images, initials


SELLER_SELECT = """
    SELECT seller_id AS boutique_id, seller_name AS boutique_name,
           website_url, social_url, description, location
    FROM sellers
"""


def _catalog_details(boutique, products, profile=None):
    boutique["location"] = seller_location(boutique.get("boutique_id"), boutique.get("boutique_name"), boutique.get("location"))
    boutique["products"] = products
    boutique["product_count"] = len(products)
    boutique["cultures"] = sorted({product["culture"] for product in products})
    boutique["occasions"] = sorted({
        occasion.strip() for product in products
        for occasion in (product.get("occasion") or "").split(",") if occasion.strip()
    })
    boutique["clothing_types"] = sorted({product["clothing_type"] for product in products if product.get("clothing_type")})
    boutique["website_url"] = safe_http_url(boutique.get("website_url"))
    boutique["social_url"] = safe_http_url(boutique.get("social_url"))
    instagram = account_for(boutique)
    if instagram:
        boutique["social_url"] = instagram["url"]
    boutique["cover_product"] = products[0] if products else None
    price_ranges = []
    currencies = sorted({product["price_currency"] for product in products if product["price_currency"]})
    for currency in currencies:
        prices = [product["price"] for product in products if product["price_currency"] == currency and product["price"] and product["price"] > 0]
        if prices:
            low, high = min(prices), max(prices)
            label = f"{currency} {low:,.2f}" if low == high else f"{currency} {low:,.2f}–{high:,.2f}"
            price_ranges.append(label)
    boutique["price_ranges"] = price_ranges
    if profile:
        for name in ["cultures", "occasions", "clothing_types"]:
            supplied = [value.strip() for value in (profile.get(name) or "").split(",") if value.strip()]
            boutique[name] = sorted(set(boutique[name]) | set(supplied))
        boutique["lead_time"] = profile.get("lead_time")
        boutique["price_info"] = profile.get("price_info")
        boutique["shipping_regions"] = profile.get("shipping_regions")
        boutique["verification_status"] = profile.get("verification_status")
    boutique["verification"] = review_for(boutique)
    boutique["timing"] = timing_for(boutique.get("boutique_id"), boutique.get("boutique_name"))
    boutique["pictures"] = public_seller_images(boutique["boutique_id"], (profile or {}).get("user_id"), boutique["boutique_name"])
    boutique["initials"] = initials(boutique["boutique_name"])
    return boutique


def get_all_boutiques():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(SELLER_SELECT + " ORDER BY seller_name")
        boutiques = cursor.fetchall()
    finally:
        cursor.close()
        connection.close()
    products = get_all_products()
    profiles = public_seller_profiles()
    return [_catalog_details(boutique, [product for product in products if product["boutique_id"] == boutique["boutique_id"]], profiles.get(boutique["boutique_id"])) for boutique in boutiques
            if boutique["boutique_id"] not in profiles or profiles[boutique["boutique_id"]].get("verification_status") == "approved"]


def get_boutique_by_id(boutique_id):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(SELLER_SELECT + " WHERE seller_id = %s", (boutique_id,))
        boutique = cursor.fetchone()
    finally:
        cursor.close()
        connection.close()
    if boutique is None:
        return None
    profile = public_seller_profiles(boutique_id).get(boutique_id)
    if profile and profile.get("verification_status") != "approved":
        return None
    return _catalog_details(boutique, get_products_by_boutique(boutique_id), profile)


def get_products_by_boutique(boutique_id):
    return get_products_for_seller(boutique_id)
