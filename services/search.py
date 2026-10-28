"""Akhil's parameterized product search, extended for location and currency."""

from database import get_db_connection
from services.products import INR_PATTERN, USD_PATTERN, format_product


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
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    try:
        query = """
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
            WHERE 1 = 1
        """
        params = []

        if keyword:
            query += """ AND (
                i.item_name LIKE %s OR i.description LIKE %s
                OR i.category LIKE %s OR s.seller_name LIKE %s
                OR c.culture_name LIKE %s OR s.location LIKE %s
            )"""
            params.extend([f"%{keyword}%"] * 6)
        if culture:
            query += " AND c.culture_name = %s"
            params.append(culture)
        if size:
            query += " AND FIND_IN_SET(%s, REPLACE(i.size, ', ', ',')) > 0"
            params.append(size)
        if color:
            query += " AND i.color LIKE %s"
            params.append(f"%{color}%")
        if location == "__unlisted__":
            query += " AND COALESCE(TRIM(s.location), '') = ''"
        elif location:
            query += " AND s.location = %s"
            params.append(location)

        # Currency is determined by explicit metadata in the team's price_notes.
        if currency == "INR":
            query += " AND UPPER(COALESCE(i.price_notes, '')) REGEXP %s"
            params.append(INR_PATTERN)
        elif currency == "USD":
            query += " AND UPPER(COALESCE(i.price_notes, '')) REGEXP %s"
            query += " AND NOT (UPPER(COALESCE(i.price_notes, '')) REGEXP %s)"
            params.extend([USD_PATTERN, INR_PATTERN])
        if currency or min_price is not None or max_price is not None:
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
        return [format_product(product) for product in cursor.fetchall()]
    finally:
        cursor.close()
        connection.close()
