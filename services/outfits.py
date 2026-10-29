"""Private buyer outfits, using existing catalog pieces and isolated schema setup."""
from contextlib import contextmanager
from threading import Lock

from flask import current_app
from mysql.connector import Error

from database import get_db_connection
from services.closet import ClosetAccessError
from services.products import PRODUCT_SELECT, format_product

MAX_PIECES = 8
_schema_lock = Lock()
SCHEMA = (
    """CREATE TABLE IF NOT EXISTS buyer_outfits (
        outfit_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
        user_id INT UNSIGNED NOT NULL,
        name VARCHAR(80) NOT NULL,
        occasion VARCHAR(80) NOT NULL DEFAULT '',
        notes VARCHAR(500) NOT NULL DEFAULT '',
        request_key CHAR(32) NOT NULL,
        version INT UNSIGNED NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (outfit_id),
        UNIQUE KEY uq_buyer_outfits_request (user_id, request_key),
        CONSTRAINT fk_buyer_outfits_user FOREIGN KEY (user_id)
            REFERENCES users (user_id) ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci""",
    """CREATE TABLE IF NOT EXISTS buyer_outfit_items (
        outfit_id INT UNSIGNED NOT NULL,
        item_id INT UNSIGNED NOT NULL,
        position INT UNSIGNED NOT NULL,
        PRIMARY KEY (outfit_id, item_id),
        CONSTRAINT fk_buyer_outfit_items_outfit FOREIGN KEY (outfit_id)
            REFERENCES buyer_outfits (outfit_id) ON DELETE CASCADE ON UPDATE CASCADE,
        CONSTRAINT fk_buyer_outfit_items_item FOREIGN KEY (item_id)
            REFERENCES items (item_id) ON DELETE CASCADE ON UPDATE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci""",
)


class OutfitNotFound(Exception):
    pass


class OutfitSelectionError(Exception):
    pass


class OutfitConflict(Exception):
    pass


def ensure_schema():
    """Create only missing outfit tables, on a connection outside save transactions.

    MySQL DDL implicitly commits. Do not run it on a connection holding buyer
    locks or outfit edits. A failed setup can be retried without changing any
    existing account, profile, catalog, saved item, or comparison record.
    """
    if current_app.extensions.get("culturelink_outfits_ready"):
        return
    with _schema_lock:
        if current_app.extensions.get("culturelink_outfits_ready"):
            return
        connection = get_db_connection()
        cursor = None
        try:
            cursor = connection.cursor(dictionary=True)
            try:
                cursor.execute("SELECT outfit_id, user_id, name, occasion, notes, request_key, version, created_at, updated_at FROM buyer_outfits LIMIT 0")
                cursor.fetchall()
                cursor.execute("SELECT outfit_id, item_id, position FROM buyer_outfit_items LIMIT 0")
                cursor.fetchall()
            except Error as error:
                if error.errno != 1146:
                    raise
                for statement in SCHEMA:
                    cursor.execute(statement)
                connection.commit()
            current_app.extensions["culturelink_outfits_ready"] = True
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()


@contextmanager
def _database(write=False):
    ensure_schema()
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        if write:
            yield connection, cursor
        else:
            yield cursor
    except Exception:
        if write:
            connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def _products(cursor, ids):
    if not ids:
        return {}
    placeholders = ", ".join(["%s"] * len(ids))
    cursor.execute(PRODUCT_SELECT + " WHERE i.item_id IN (" + placeholders + ") GROUP BY i.item_id", tuple(ids))
    return {row["product_id"]: format_product(row) for row in cursor.fetchall()}


def _attach_pieces(cursor, user_id, outfits):
    if not outfits:
        return outfits
    ids = {outfit["outfit_id"] for outfit in outfits}
    placeholders = ", ".join(["%s"] * len(ids))
    cursor.execute("""SELECT link.outfit_id, link.item_id FROM buyer_outfit_items link
        JOIN buyer_outfits outfit ON outfit.outfit_id = link.outfit_id
        WHERE outfit.user_id = %s AND link.outfit_id IN (""" + placeholders + ") ORDER BY link.position, link.item_id", (user_id, *ids))
    links = cursor.fetchall()
    products = _products(cursor, list(dict.fromkeys(link["item_id"] for link in links)))
    grouped = {outfit_id: [] for outfit_id in ids}
    for link in links:
        if link["item_id"] in products:
            grouped[link["outfit_id"]].append(products[link["item_id"]])
    for outfit in outfits:
        outfit["products"] = grouped[outfit["outfit_id"]]
    return outfits


def list_outfits(user_id):
    with _database() as cursor:
        cursor.execute("""SELECT outfit_id, name, occasion, notes, version, created_at, updated_at
            FROM buyer_outfits WHERE user_id = %s ORDER BY updated_at DESC, outfit_id DESC""", (user_id,))
        return _attach_pieces(cursor, user_id, cursor.fetchall())


def get_outfit(user_id, outfit_id):
    with _database() as cursor:
        cursor.execute("""SELECT outfit_id, name, occasion, notes, version, created_at, updated_at
            FROM buyer_outfits WHERE user_id = %s AND outfit_id = %s""", (user_id, outfit_id))
        outfit = cursor.fetchone()
        if outfit is None:
            raise OutfitNotFound()
        return _attach_pieces(cursor, user_id, [outfit])[0]


def _lock_buyer(cursor, user_id):
    # The same buyer lock is used by Closet saves/removals and comparisons.
    cursor.execute("SELECT role FROM users WHERE user_id = %s FOR UPDATE", (user_id,))
    buyer = cursor.fetchone()
    if buyer is None or buyer["role"] != "customer":
        raise ClosetAccessError()


def save_outfit(user_id, values, item_ids, request_key, outfit_id=None, version=None):
    with _database(write=True) as (connection, cursor):
        _lock_buyer(cursor, user_id)
        if outfit_id is None:
            # Retrying the same submitted creation never produces a duplicate.
            cursor.execute("SELECT outfit_id FROM buyer_outfits WHERE user_id = %s AND request_key = %s", (user_id, request_key))
            existing = cursor.fetchone()
            if existing:
                connection.commit()
                return existing["outfit_id"]
            retained = set()
        else:
            cursor.execute("SELECT version FROM buyer_outfits WHERE user_id = %s AND outfit_id = %s FOR UPDATE", (user_id, outfit_id))
            existing = cursor.fetchone()
            if existing is None:
                raise OutfitNotFound()
            if version != existing["version"]:
                raise OutfitConflict()
            cursor.execute("SELECT item_id FROM buyer_outfit_items WHERE outfit_id = %s", (outfit_id,))
            retained = {row["item_id"] for row in cursor.fetchall()}
        cursor.execute("SELECT item_id FROM saveditems WHERE user_id = %s", (user_id,))
        allowed = retained | {row["item_id"] for row in cursor.fetchall()}
        if not 1 <= len(item_ids) <= MAX_PIECES or len(set(item_ids)) != len(item_ids) or not set(item_ids) <= allowed:
            raise OutfitSelectionError()
        if outfit_id is None:
            cursor.execute("""INSERT INTO buyer_outfits (user_id, name, occasion, notes, request_key)
                VALUES (%s, %s, %s, %s, %s)""", (user_id, values["name"], values["occasion"], values["notes"], request_key))
            outfit_id = cursor.lastrowid
        else:
            cursor.execute("""UPDATE buyer_outfits SET name = %s, occasion = %s, notes = %s,
                version = version + 1, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s AND outfit_id = %s""", (values["name"], values["occasion"], values["notes"], user_id, outfit_id))
            cursor.execute("DELETE FROM buyer_outfit_items WHERE outfit_id = %s", (outfit_id,))
        for position, item_id in enumerate(item_ids):
            cursor.execute("INSERT INTO buyer_outfit_items (outfit_id, item_id, position) VALUES (%s, %s, %s)", (outfit_id, item_id, position))
        connection.commit()
        return outfit_id


def delete_outfit(user_id, outfit_id, version):
    with _database(write=True) as (connection, cursor):
        _lock_buyer(cursor, user_id)
        cursor.execute("SELECT version FROM buyer_outfits WHERE user_id = %s AND outfit_id = %s FOR UPDATE", (user_id, outfit_id))
        existing = cursor.fetchone()
        if existing is None:
            raise OutfitNotFound()
        if version != existing["version"]:
            raise OutfitConflict()
        cursor.execute("DELETE FROM buyer_outfits WHERE user_id = %s AND outfit_id = %s", (user_id, outfit_id))
        connection.commit()
