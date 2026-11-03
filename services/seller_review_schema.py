"""Isolated, additive storage for simulated reviews and private listings."""
from contextlib import contextmanager
from threading import Lock
from flask import current_app
from mysql.connector import Error
from database import get_db_connection

# Existing curated sellers have no account-owned seller_profiles row. Account
# sellers become public only when a team decision marks that profile approved.
PUBLIC_SELLER_SQL = """(NOT EXISTS (
    SELECT 1 FROM seller_profiles public_profile WHERE public_profile.seller_id = s.seller_id
) OR EXISTS (
    SELECT 1 FROM seller_profiles approved_profile
    WHERE approved_profile.seller_id = s.seller_id AND approved_profile.verification_status = 'approved'
))"""

SCHEMA = (
    """CREATE TABLE IF NOT EXISTS seller_applications (
        user_id INT UNSIGNED NOT NULL,
        seller_id INT UNSIGNED NOT NULL,
        status VARCHAR(20) NOT NULL DEFAULT 'pending',
        version INT UNSIGNED NOT NULL DEFAULT 1,
        submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        reviewed_at DATETIME DEFAULT NULL,
        appealed_at DATETIME DEFAULT NULL,
        reviewer_id INT UNSIGNED DEFAULT NULL,
        reasons TEXT NOT NULL,
        reviewer_notes TEXT NOT NULL,
        appeal_text TEXT NOT NULL,
        appeal_links TEXT NOT NULL,
        PRIMARY KEY (user_id),
        UNIQUE KEY uq_seller_application_seller (seller_id),
        CONSTRAINT fk_seller_application_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
        CONSTRAINT fk_seller_application_seller FOREIGN KEY (seller_id) REFERENCES sellers (seller_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci""",
    """CREATE TABLE IF NOT EXISTS seller_review_events (
        event_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
        user_id INT UNSIGNED NOT NULL,
        actor_id INT UNSIGNED NOT NULL,
        kind VARCHAR(30) NOT NULL,
        status VARCHAR(20) NOT NULL,
        reasons TEXT NOT NULL,
        notes TEXT NOT NULL,
        evidence TEXT NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (event_id),
        CONSTRAINT fk_seller_event_application FOREIGN KEY (user_id) REFERENCES seller_applications (user_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci""",
    """CREATE TABLE IF NOT EXISTS seller_inventory (
        item_id INT UNSIGNED NOT NULL,
        user_id INT UNSIGNED NOT NULL,
        photo_name VARCHAR(80) NOT NULL DEFAULT '',
        version INT UNSIGNED NOT NULL DEFAULT 1,
        request_key CHAR(32) NOT NULL,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (item_id),
        UNIQUE KEY uq_seller_inventory_request (user_id, request_key),
        CONSTRAINT fk_seller_inventory_item FOREIGN KEY (item_id) REFERENCES items (item_id) ON DELETE CASCADE,
        CONSTRAINT fk_seller_inventory_user FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci""",
)
_schema_lock = Lock()


def ensure_schema():
    if current_app.extensions.get("culturelink_seller_review_ready"):
        return
    with _schema_lock:
        if current_app.extensions.get("culturelink_seller_review_ready"):
            return
        connection = get_db_connection()
        cursor = None
        try:
            cursor = connection.cursor(dictionary=True)
            try:
                for table in ("seller_applications", "seller_review_events", "seller_inventory"):
                    cursor.execute("SELECT * FROM " + table + " LIMIT 0")
                    cursor.fetchall()
            except Error as error:
                if error.errno != 1146:
                    raise
                # MySQL DDL implicitly commits, so this is a separate connection
                # from every application, item, appeal, and decision transaction.
                for statement in SCHEMA:
                    cursor.execute(statement)
                connection.commit()
            current_app.extensions["culturelink_seller_review_ready"] = True
        finally:
            if cursor is not None:
                cursor.close()
            connection.close()


@contextmanager
def database(write=False):
    ensure_schema()
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        yield connection, cursor
    except Exception:
        if write:
            connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
