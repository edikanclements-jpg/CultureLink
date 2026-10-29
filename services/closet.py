"""Owned saves in the original saveditems table; no schema changes."""

from database import get_db_connection
from services.products import PRODUCT_SELECT, format_product


class ClosetAccessError(Exception):
    pass


class ClosetItemNotFound(Exception):
    pass


def saved_item_ids(user_id):
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT item_id FROM saveditems WHERE user_id = %s", (user_id,))
        return {row["item_id"] for row in cursor.fetchall()}
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def saved_products(user_id):
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(PRODUCT_SELECT + """
            JOIN saveditems saved ON saved.item_id = i.item_id
            WHERE saved.user_id = %s
            GROUP BY i.item_id
            ORDER BY MAX(saved.date_saved) DESC, MAX(saved.saved_item_id) DESC
        """, (user_id,))
        return [format_product(row) for row in cursor.fetchall()]
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def set_saved(user_id, product_id, saved):
    """Set an explicit state, so repeated requests cannot toggle it twice."""
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        # Serializes this buyer's changes and rechecks the role in the write
        # transaction, including a role change from another open tab.
        cursor.execute("SELECT role FROM users WHERE user_id = %s FOR UPDATE", (user_id,))
        user = cursor.fetchone()
        if user is None or user["role"] != "customer":
            raise ClosetAccessError()
        cursor.execute("SELECT item_id FROM items WHERE item_id = %s", (product_id,))
        if cursor.fetchone() is None:
            raise ClosetItemNotFound()
        cursor.execute("SELECT saved_item_id FROM saveditems WHERE user_id = %s AND item_id = %s",
                       (user_id, product_id))
        exists = cursor.fetchone() is not None
        if saved and not exists:
            cursor.execute("INSERT INTO saveditems (user_id, item_id) VALUES (%s, %s)", (user_id, product_id))
        elif not saved and exists:
            cursor.execute("DELETE FROM saveditems WHERE user_id = %s AND item_id = %s", (user_id, product_id))
        cursor.execute("SELECT COUNT(*) AS saved_count FROM saveditems WHERE user_id = %s", (user_id,))
        count = cursor.fetchone()["saved_count"]
        connection.commit()
        return {"product_id": product_id, "saved": saved, "count": count}
    except Exception:
        connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
