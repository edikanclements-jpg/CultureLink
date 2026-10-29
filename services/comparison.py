"""Temporary, buyer-session comparisons using the supplied comparison table."""
from datetime import datetime, timedelta, timezone

from database import get_db_connection
from services.closet import ClosetAccessError


class ComparisonLimitError(Exception):
    pass


class ComparisonItemError(Exception):
    pass


def _selected(cursor, user_id, scope, now):
    cursor.execute("""
        SELECT selection.item_id FROM comparisonselections selection
        WHERE selection.session_id = %s
          AND (selection.expires_at IS NULL OR selection.expires_at > %s)
          AND EXISTS (SELECT 1 FROM saveditems saved
                      WHERE saved.user_id = %s AND saved.item_id = selection.item_id)
        ORDER BY selection.comparison_id
    """, (scope, now, user_id))
    return [row["item_id"] for row in cursor.fetchall()][:3]


def selection_ids(user_id, scope):
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        return _selected(cursor, user_id, scope, datetime.now(timezone.utc).replace(tzinfo=None))
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def change_selection(user_id, scope, product_id=None, selected=None):
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT role FROM users WHERE user_id = %s FOR UPDATE", (user_id,))
        user = cursor.fetchone()
        if user is None or user["role"] != "customer":
            raise ClosetAccessError()
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        cursor.execute("DELETE FROM comparisonselections WHERE session_id = %s AND expires_at <= %s", (scope, now))
        cursor.execute("""
            DELETE FROM comparisonselections WHERE session_id = %s
            AND NOT EXISTS (SELECT 1 FROM saveditems saved
                            WHERE saved.user_id = %s AND saved.item_id = comparisonselections.item_id)
        """, (scope, user_id))
        if selected is None:
            cursor.execute("DELETE FROM comparisonselections WHERE session_id = %s", (scope,))
        else:
            ids = _selected(cursor, user_id, scope, now)
            if selected:
                cursor.execute("SELECT item_id FROM saveditems WHERE user_id = %s AND item_id = %s", (user_id, product_id))
                if cursor.fetchone() is None:
                    raise ComparisonItemError()
                if product_id not in ids:
                    if len(ids) >= 3:
                        raise ComparisonLimitError()
                    cursor.execute("""
                        INSERT INTO comparisonselections (session_id, item_id, expires_at)
                        VALUES (%s, %s, %s)
                    """, (scope, product_id, now + timedelta(hours=12)))
            else:
                cursor.execute("DELETE FROM comparisonselections WHERE session_id = %s AND item_id = %s", (scope, product_id))
        ids = _selected(cursor, user_id, scope, now)
        connection.commit()
        return ids
    except Exception:
        connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
