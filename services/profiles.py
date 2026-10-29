"""Account-owned profiles, role selection, and shared address-table storage."""

from decimal import Decimal
from mysql.connector import Error, errorcode
from database import get_db_connection


class ProfileAccessError(ValueError):
    pass


def _completed_kind(cursor, user_id):
    cursor.execute("SELECT user_id FROM buyer_profiles WHERE user_id = %s", (user_id,))
    if cursor.fetchone() is not None:
        return "buyer"
    cursor.execute("SELECT user_id FROM seller_profiles WHERE user_id = %s", (user_id,))
    return "seller" if cursor.fetchone() is not None else None


def completed_profile_kind(user_id):
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        return _completed_kind(cursor, user_id)
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def choose_account_type(user_id, account_type):
    if account_type not in {"buyer", "seller"}:
        raise ProfileAccessError("Choose Buyer or Seller.")
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT role FROM users WHERE user_id = %s FOR UPDATE", (user_id,))
        user = cursor.fetchone()
        if user is None or user["role"] not in {"pending", "customer", "seller"}:
            raise ProfileAccessError("This account cannot change its type here.")
        if _completed_kind(cursor, user_id) is not None:
            raise ProfileAccessError("This account already has a completed profile.")
        role = "customer" if account_type == "buyer" else "seller"
        cursor.execute("UPDATE users SET role = %s WHERE user_id = %s", (role, user_id))
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def _default_address(cursor, user_id):
    cursor.execute("""
        SELECT l.location_id, l.address_line1, l.address_line2, l.city,
               l.state, l.postal_code, l.country
        FROM userlocations ul JOIN locations l ON l.location_id = ul.location_id
        WHERE ul.user_id = %s AND ul.is_default = 1
        ORDER BY ul.user_location_id DESC LIMIT 1
    """, (user_id,))
    return cursor.fetchone() or {}


def get_buyer_profile(user_id):
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM buyer_profiles WHERE user_id = %s", (user_id,))
        profile = cursor.fetchone()
        if profile is not None:
            profile.update(_default_address(cursor, user_id))
        return profile
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def get_seller_profile(user_id):
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT p.*, s.seller_name AS business_name, s.description,
                   s.website_url, s.social_url, s.location
            FROM seller_profiles p JOIN sellers s ON s.seller_id = p.seller_id
            WHERE p.user_id = %s
        """, (user_id,))
        profile = cursor.fetchone()
        if profile is not None:
            profile.update(_default_address(cursor, user_id))
        return profile
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def _check_role(cursor, user_id, role):
    cursor.execute("SELECT role FROM users WHERE user_id = %s FOR UPDATE", (user_id,))
    row = cursor.fetchone()
    if row is None or row["role"] != role:
        raise ProfileAccessError("Choose the matching account type before saving this profile.")
    completed = _completed_kind(cursor, user_id)
    expected = "buyer" if role == "customer" else "seller"
    if completed is not None and completed != expected:
        raise ProfileAccessError("This account has a different profile type.")


def _save_default_address(cursor, user_id, values, seller=False):
    cursor.execute("SELECT location_id FROM userlocations WHERE user_id = %s AND is_default = 1 FOR UPDATE", (user_id,))
    old_ids = [row["location_id"] for row in cursor.fetchall()]
    new_id = None
    address_fields = ["address_line1", "address_line2", "city", "state", "postal_code", "country"]
    if any(values.get(name) for name in address_fields):
        cursor.execute("""
            INSERT INTO locations (location_name, address_line1, address_line2, city, state, postal_code, country)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, ("Business address" if seller else "Buyer address", values.get("address_line1") or "",
              values.get("address_line2") or None, values.get("city") or "",
              values.get("state") or None, values.get("postal_code") or None,
              values.get("country") or ""))
        new_id = cursor.lastrowid
    # Replace only this account's default address; never edit another owner's row.
    cursor.execute("DELETE FROM userlocations WHERE user_id = %s AND is_default = 1", (user_id,))
    if new_id is not None:
        cursor.execute("INSERT INTO userlocations (user_id, location_id, is_default) VALUES (%s, %s, 1)", (user_id, new_id))
    for old_id in old_ids:
        cursor.execute("""
            DELETE FROM locations WHERE location_id = %s
            AND NOT EXISTS (SELECT 1 FROM userlocations WHERE location_id = %s)
        """, (old_id, old_id))


def save_buyer_profile(user_id, values):
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        _check_role(cursor, user_id, "customer")
        cursor.execute("SELECT user_id FROM buyer_profiles WHERE user_id = %s", (user_id,))
        exists = cursor.fetchone() is not None
        fields = ["full_name", "phone", "measurement_unit", "chest", "waist", "hips", "height",
                  "color_preferences", "culture_preferences", "occasion_preferences"]
        data = []
        for name in fields:
            value = values.get(name) or None
            if name in {"chest", "waist", "hips", "height"} and value is not None:
                value = Decimal(str(value))
            data.append(value)
        if exists:
            cursor.execute("UPDATE buyer_profiles SET " + ", ".join(name + " = %s" for name in fields)
                           + ", updated_at = CURRENT_TIMESTAMP WHERE user_id = %s", tuple(data) + (user_id,))
        else:
            cursor.execute("INSERT INTO buyer_profiles (user_id, " + ", ".join(fields) + ") VALUES ("
                           + ", ".join(["%s"] * (len(fields) + 1)) + ")", (user_id,) + tuple(data))
        _save_default_address(cursor, user_id, values)
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def save_seller_profile(user_id, values):
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        _check_role(cursor, user_id, "seller")
        cursor.execute("SELECT seller_id FROM seller_profiles WHERE user_id = %s", (user_id,))
        existing = cursor.fetchone()
        location = ", ".join(values[name] for name in ["city", "state", "country"] if values.get(name))
        public_values = (values["business_name"], values.get("website_url") or None,
                         values.get("social_url") or None, values.get("description") or None, location)
        if existing is not None:
            seller_id = existing["seller_id"]
            cursor.execute("UPDATE sellers SET seller_name = %s, website_url = %s, social_url = %s, description = %s, location = %s WHERE seller_id = %s", public_values + (seller_id,))
        else:
            cursor.execute("INSERT INTO sellers (seller_name, website_url, social_url, description, location) VALUES (%s, %s, %s, %s, %s)", public_values)
            seller_id = cursor.lastrowid
        fields = ["contact_name", "phone", "cultures", "occasions", "clothing_types", "lead_time", "price_info", "shipping_regions"]
        data = tuple(values.get(name) or None for name in fields)
        if existing is not None:
            cursor.execute("UPDATE seller_profiles SET " + ", ".join(name + " = %s" for name in fields)
                           + ", updated_at = CURRENT_TIMESTAMP WHERE user_id = %s", data + (user_id,))
        else:
            cursor.execute("INSERT INTO seller_profiles (user_id, seller_id, " + ", ".join(fields) + ") VALUES ("
                           + ", ".join(["%s"] * (len(fields) + 2)) + ")", (user_id, seller_id) + data)
        _save_default_address(cursor, user_id, values, seller=True)
        connection.commit()
        return seller_id
    except Exception:
        connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def public_seller_profiles(seller_id=None):
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        query = "SELECT seller_id, cultures, occasions, clothing_types, lead_time, price_info, shipping_regions, verification_status FROM seller_profiles"
        parameters = ()
        if seller_id is not None:
            query += " WHERE seller_id = %s"
            parameters = (seller_id,)
        cursor.execute(query, parameters)
        return {row["seller_id"]: row for row in cursor.fetchall()}
    except Error as error:
        if error.errno == errorcode.ER_NO_SUCH_TABLE:
            return {}
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
