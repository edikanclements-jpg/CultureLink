"""Akhil's product queries and the catalog's shared display labels."""

import re
from urllib.parse import urlsplit

from database import get_db_connection


INR_PATTERN = r"(^|[^A-Z])INR([^A-Z]|$)"
USD_PATTERN = r"(^|[^A-Z])USD([^A-Z]|$)"

PRODUCT_SELECT = """
    SELECT
        i.item_id AS product_id,
        i.item_name AS product_name,
        i.description,
        i.category AS clothing_type,
        i.price,
        i.price_notes,
        i.image_url,
        i.purchase_url,
        i.color,
        i.size,
        i.seller_id AS boutique_id,
        s.seller_name AS boutique_name,
        s.location AS seller_location,
        s.website_url AS seller_website_url,
        s.social_url AS seller_social_url,
        c.culture_name AS culture,
        GROUP_CONCAT(
            DISTINCT o.occasion_name
            ORDER BY o.occasion_name
            SEPARATOR ', '
        ) AS occasion
    FROM items i
    JOIN sellers s ON i.seller_id = s.seller_id
    JOIN cultures c ON i.culture_id = c.culture_id
    LEFT JOIN itemoccasions io ON i.item_id = io.item_id
    LEFT JOIN occasions o ON io.occasion_id = o.occasion_id
"""


def safe_http_url(value):
    """Use only genuine HTTP/HTTPS URLs supplied in the existing records."""
    value = (value or "").strip()
    try:
        parts = urlsplit(value)
    except ValueError:
        return ""
    return value if parts.scheme.lower() in {"https", "http"} and parts.netloc else ""


def currency_for(product):
    notes = (product.get("price_notes") or "").upper()
    # INR notes sometimes also say NOT USD.
    if re.search(INR_PATTERN, notes):
        return "INR"
    if re.search(USD_PATTERN, notes):
        return "USD"
    return ""


def format_product(product):
    """Add presentation labels while retaining the original values and IDs."""
    product["price_currency"] = currency_for(product)
    price = product.get("price")
    if price is None or price <= 0:
        product["display_price"] = "Price to be determined"
    elif product["price_currency"]:
        product["display_price"] = f"{product['price_currency']} {price:,.2f}"
    else:
        product["display_price"] = f"{price:,.2f} (currency not provided)"
    size = (product.get("size") or "").strip()
    unknown_sizes = {"", "to be measured", "to be determined", "unknown", "not specified"}
    product["display_size"] = "Size to be determined" if size.casefold() in unknown_sizes else size
    product["storefront_url"] = (
        safe_http_url(product.get("purchase_url"))
        or safe_http_url(product.get("seller_website_url"))
        or safe_http_url(product.get("seller_social_url"))
    )
    return product


def _fetch_products(where="", parameters=()):
    """Use Akhil's joins for the homepage, one item, or one seller."""
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        cursor.execute(PRODUCT_SELECT + where + " GROUP BY i.item_id ORDER BY i.item_id", parameters)
        return [format_product(product) for product in cursor.fetchall()]
    finally:
        cursor.close()
        connection.close()


def get_all_products():
    return _fetch_products()


def get_product_by_id(product_id):
    products = _fetch_products(" WHERE i.item_id = %s", (product_id,))
    return products[0] if products else None


def get_products_for_seller(boutique_id):
    return _fetch_products(" WHERE i.seller_id = %s", (boutique_id,))
