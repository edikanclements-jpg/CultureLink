"""Akhil's seller queries, enriched with each seller's real catalog items."""

from database import get_db_connection
from services.products import get_all_products, get_products_for_seller, safe_http_url


SELLER_SELECT = """
    SELECT seller_id AS boutique_id, seller_name AS boutique_name,
           website_url, social_url, description, location
    FROM sellers
"""


def _catalog_details(boutique, products):
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
    return [_catalog_details(boutique, [product for product in products if product["boutique_id"] == boutique["boutique_id"]]) for boutique in boutiques]


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
    return _catalog_details(boutique, get_products_by_boutique(boutique_id))


def get_products_by_boutique(boutique_id):
    return get_products_for_seller(boutique_id)
