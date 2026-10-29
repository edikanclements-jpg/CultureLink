"""Parameterized queries for the existing CultureLink users table."""

from database import get_db_connection


def _find_user(column, value, include_password=False):
    # Column names are selected here, never supplied by a website visitor.
    if column not in {"email", "user_id"}:
        raise ValueError("Unsupported account lookup")
    fields = "user_id, email, role, created_at"
    if include_password:
        fields += ", password_hash"
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            f"SELECT {fields} FROM users WHERE {column} = %s LIMIT 1", (value,)
        )
        return cursor.fetchone()
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def find_user_by_email(email):
    return _find_user("email", email, include_password=True)


def find_user_by_id(user_id):
    return _find_user("user_id", user_id)


def create_account(email, password_hash):
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, %s)",
            (email, password_hash, "pending"),
        )
        user_id = cursor.lastrowid
        connection.commit()
        return user_id
    except Exception:
        connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
