"""Akhil's parameterized product search, extended for location and currency."""

from database import get_db_connection
from services.products import INR_PATTERN, USD_PATTERN, format_product
from services.catalog_rules import SELLER_LOCATION_SQL, matches_size, canonical_location_query, COUNTRY_LOCATION_QUERIES
from services.seller_review_schema import PUBLIC_SELLER_SQL
from services.catalog_expansion import ensure_catalog


SORTS = {
    "name_asc": "i.item_name ASC, i.item_id ASC",
    "name_desc": "i.item_name DESC, i.item_id ASC",
    "seller": "s.seller_name ASC, i.item_name ASC, i.item_id ASC",
    "price_asc": "i.price ASC, i.item_id ASC",
    "price_desc": "i.price DESC, i.item_id ASC",
}


def search_products(keyword=None, culture=None, occasion=None, size=None,
                    color=None, min_price=None, max_price=None,
                    location=None, currency=None, sort="name_asc"):
    """Filter the existing tables; user-entered values remain SQL parameters."""
    ensure_catalog()
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        keyword = canonical_location_query(keyword)
        location = canonical_location_query(location)
        priced_only = bool(currency or min_price is not None or max_price is not None or sort in {"price_asc", "price_desc"})
        query = f"""
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
                {SELLER_LOCATION_SQL} AS seller_location,
                c.culture_name AS culture,
                GROUP_CONCAT(
                    DISTINCT o.occasion_name
                    ORDER BY o.occasion_name
                    SEPARATOR ', '
                ) AS occasion
            FROM items i
            JOIN sellers s ON i.seller_id = s.seller_id AND {PUBLIC_SELLER_SQL}
            JOIN cultures c ON i.culture_id = c.culture_id
            LEFT JOIN itemoccasions io ON i.item_id = io.item_id
            LEFT JOIN occasions o ON io.occasion_id = o.occasion_id
            WHERE 1 = 1
        """
        params = []

        if keyword and keyword.casefold() in COUNTRY_LOCATION_QUERIES:
            query += f" AND {SELLER_LOCATION_SQL} LIKE %s"
            params.append(f"%{keyword}%")
        elif keyword:
            query += f""" AND (
                i.item_name LIKE %s OR i.description LIKE %s
                OR i.category LIKE %s OR s.seller_name LIKE %s
                OR c.culture_name LIKE %s OR {SELLER_LOCATION_SQL} LIKE %s
            )"""
            params.extend([f"%{keyword}%"] * 6)
        if culture:
            query += " AND c.culture_name = %s"
            params.append(culture)
        if color:
            query += " AND i.color LIKE %s"
            params.append(f"%{color}%")
        if location == "__unlisted__":
            query += f" AND COALESCE(TRIM({SELLER_LOCATION_SQL}), '') = ''"
        elif location:
            query += f" AND {SELLER_LOCATION_SQL} = %s"
            params.append(location)

        # Currency is determined by explicit metadata in the team's price_notes.
        if currency == "INR":
            query += " AND UPPER(COALESCE(i.price_notes, '')) REGEXP %s"
            params.append(INR_PATTERN)
        elif currency == "USD":
            query += " AND UPPER(COALESCE(i.price_notes, '')) REGEXP %s"
            query += " AND NOT (UPPER(COALESCE(i.price_notes, '')) REGEXP %s)"
            params.extend([USD_PATTERN, INR_PATTERN])
        if priced_only:
            query += " AND i.price > 0"
        if min_price is not None:
            query += " AND i.price >= %s"
            params.append(min_price)
        if max_price is not None:
            query += " AND i.price <= %s"
            params.append(max_price)
        if occasion:
            query += """ AND EXISTS (
                SELECT 1 FROM itemoccasions io2
                JOIN occasions o2 ON io2.occasion_id = o2.occasion_id
                WHERE io2.item_id = i.item_id AND o2.occasion_name = %s
            )"""
            params.append(occasion)

        # This fixed allowlist keeps the ORDER BY clause separate from user text.
        query += " GROUP BY i.item_id ORDER BY " + SORTS.get(sort, SORTS["name_asc"])
        cursor.execute(query, tuple(params))
        products = [format_product(product) for product in cursor.fetchall()]
        # One shared normalization handles legacy labels, casing and whitespace.
        # The catalog is returned as a complete list, with no pre-filter LIMIT.
        if size:
            products = [product for product in products if matches_size(product["size"], size)]
        if priced_only:
            products = [product for product in products if product["price"] is not None and product["price"] > 0]
        return products
    finally:
        cursor.close()
        connection.close()
