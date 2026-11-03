"""Team decisions and seller appeals, separate from public evidence scores."""
from datetime import date, datetime, timedelta
import json
import re
from urllib.parse import urlsplit

from services.seller_review_schema import database

REASONS = {
    "identity": "Business identity or ownership could not be confirmed.",
    "contact": "Contact or business-location details need correction.",
    "catalog": "Product descriptions, sizing, or availability are incomplete or inconsistent.",
    "photos": "Product photos need to be clearer or ownership of the photos needs support.",
    "pricing": "Prices, currencies, or custom-order pricing need clarification.",
    "fulfillment": "Production, delivery, returns, or order-handling information needs clarification.",
    "other": "Another issue described in the team's notes needs to be resolved.",
}
STATUS_LABELS = {"pending": "Awaiting review", "approved": "Approved", "rejected": "Not approved", "appeal_pending": "Appeal awaiting review"}


class ReviewAccessError(Exception):
    pass


class ReviewNotFound(Exception):
    pass


class ReviewConflict(Exception):
    pass


class ReviewValidationError(ValueError):
    pass


def now():
    # This local app uses the same local calendar as its localhost MySQL server.
    return datetime.now().replace(microsecond=0)


def _date(value):
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))


def business_day(value, days):
    value = _date(value).date() if not isinstance(value, date) or isinstance(value, datetime) else value
    while days:
        value += timedelta(days=1)
        if value.weekday() < 5:
            days -= 1
    return value


def _json(value, fallback):
    try:
        return json.loads(value) if value else fallback
    except (ValueError, TypeError):
        return fallback


def present(row):
    if row is None:
        return None
    row = dict(row)
    row["reason_codes"] = [code for code in _json(row.get("reasons"), []) if code in REASONS]
    row["reason_labels"] = [REASONS[code] for code in row["reason_codes"]]
    row["links"] = _json(row.get("appeal_links"), [])
    row["label"] = STATUS_LABELS.get(row["status"], "Awaiting review")
    started = row.get("appealed_at") if row["status"] == "appeal_pending" else row["submitted_at"]
    row["review_from"] = business_day(started, 3).strftime("%b %d, %Y")
    row["review_until"] = business_day(started, 6).strftime("%b %d, %Y")
    return row


def lock_seller(cursor, user_id):
    cursor.execute("SELECT user_id, email, role FROM users WHERE user_id = %s FOR UPDATE", (user_id,))
    user = cursor.fetchone()
    if user is None or user["role"] != "seller":
        raise ReviewAccessError()
    cursor.execute("SELECT seller_id FROM seller_profiles WHERE user_id = %s", (user_id,))
    profile = cursor.fetchone()
    if profile is None:
        raise ReviewNotFound()
    return user, profile["seller_id"]


def _snapshot(cursor, user_id):
    cursor.execute("""SELECT s.seller_name, s.description, s.website_url, s.social_url, s.location,
        p.contact_name, p.phone, p.cultures, p.occasions, p.clothing_types, p.lead_time, p.price_info, p.shipping_regions
        FROM seller_profiles p JOIN sellers s ON s.seller_id = p.seller_id WHERE p.user_id = %s""", (user_id,))
    profile = cursor.fetchone() or {}
    cursor.execute("""SELECT i.item_id, i.item_name, i.category, i.color, i.size, i.price, i.price_notes,
        inv.photo_name, inv.version FROM seller_inventory inv JOIN items i ON i.item_id = inv.item_id
        WHERE inv.user_id = %s ORDER BY i.item_id""", (user_id,))
    return json.dumps({"profile": profile, "pieces": cursor.fetchall()}, default=str, ensure_ascii=False)


def record_event(cursor, user_id, actor_id, kind, status, reasons=(), notes=""):
    cursor.execute("""INSERT INTO seller_review_events (user_id, actor_id, kind, status, reasons, notes, evidence)
        VALUES (%s, %s, %s, %s, %s, %s, %s)""",
        (user_id, actor_id, kind, status, json.dumps(list(reasons)), notes, _snapshot(cursor, user_id)))
    event_id = cursor.lastrowid
    return event_id


def profile_saved(cursor, user_id, seller_id, recheck=False):
    """Called inside the profile transaction, after locking its owning user."""
    cursor.execute("SELECT status FROM seller_applications WHERE user_id = %s FOR UPDATE", (user_id,))
    existing = cursor.fetchone()
    if existing:
        status = existing["status"]
        if status == "approved" and recheck:
            status = "pending"
            cursor.execute("""UPDATE seller_applications SET status = 'pending', submitted_at = %s,
                updated_at = %s, reviewed_at = NULL, reviewer_id = NULL, appealed_at = NULL,
                reasons = '[]', reviewer_notes = '', appeal_text = '', appeal_links = '[]',
                version = version + 1 WHERE user_id = %s""", (now(),now(),user_id))
            record_event(cursor,user_id,user_id,"submitted",status)
        else:
            touch(cursor, user_id)
    else:
        status = "pending"
        cursor.execute("""INSERT INTO seller_applications
            (user_id, seller_id, status, reasons, reviewer_notes, appeal_text, appeal_links)
            VALUES (%s, %s, 'pending', '[]', '', '', '[]')""", (user_id, seller_id))
        record_event(cursor, user_id, user_id, "submitted", status)
    cursor.execute("UPDATE seller_profiles SET verification_status = %s WHERE user_id = %s", (status, user_id))


def touch(cursor, user_id):
    cursor.execute("UPDATE seller_applications SET version = version + 1, updated_at = CURRENT_TIMESTAMP WHERE user_id = %s", (user_id,))


def application_for(user_id, enroll=True):
    with database(write=True) as (connection, cursor):
        if enroll:
            _, seller_id = lock_seller(cursor, user_id)
            cursor.execute("SELECT user_id FROM seller_applications WHERE user_id = %s", (user_id,))
            if cursor.fetchone() is None:
                profile_saved(cursor, user_id, seller_id)
        cursor.execute("""SELECT a.*, u.email, s.seller_name AS business_name FROM seller_applications a
            JOIN users u ON u.user_id = a.user_id JOIN sellers s ON s.seller_id = a.seller_id
            WHERE a.user_id = %s""", (user_id,))
        result = cursor.fetchone()
        connection.commit()
        return present(result)


def history_for(user_id):
    with database() as (_, cursor):
        cursor.execute("""SELECT e.* FROM seller_review_events e
            WHERE e.user_id = %s ORDER BY e.event_id DESC""", (user_id,))
        result = cursor.fetchall()
    for event in result:
        event["reason_labels"] = [REASONS[c] for c in _json(event["reasons"], []) if c in REASONS]
        event["snapshot"] = _json(event["evidence"], {})
    return result


def review_queue(status="pending"):
    if status not in {*STATUS_LABELS, "all"}:
        status = "pending"
    # Profiles created before this update enter the same review process.
    with database() as (_, cursor):
        cursor.execute("""SELECT p.user_id FROM seller_profiles p JOIN users u ON u.user_id = p.user_id
            LEFT JOIN seller_applications a ON a.user_id = p.user_id
            WHERE a.user_id IS NULL AND u.role = 'seller'""")
        legacy = [row["user_id"] for row in cursor.fetchall()]
    for user_id in legacy:
        application_for(user_id)
    with database() as (_, cursor):
        query = """SELECT a.*, s.seller_name AS business_name, u.email FROM seller_applications a
            JOIN sellers s ON s.seller_id = a.seller_id JOIN users u ON u.user_id = a.user_id"""
        params = ()
        if status != "all":
            query += " WHERE a.status = %s"; params = (status,)
        cursor.execute(query + " ORDER BY a.updated_at, a.user_id", params)
        return [present(row) for row in cursor.fetchall()]


def decide(reviewer_id, user_id, version, action, reasons, notes):
    if action not in {"approved", "rejected"}:
        raise ReviewValidationError("Choose Approve or Request changes.")
    reasons = list(dict.fromkeys(reasons))
    notes = str(notes or "").strip()
    if len(notes) > 2000 or any(code not in REASONS for code in reasons):
        raise ReviewValidationError("Use the listed reasons and keep notes within 2,000 characters.")
    if action == "rejected" and (not reasons or ("other" in reasons and not notes)):
        raise ReviewValidationError("Choose at least one reason. Add notes when selecting Another issue.")
    if reviewer_id == user_id:
        raise ReviewAccessError()
    with database(write=True) as (connection, cursor):
        cursor.execute("SELECT role FROM users WHERE user_id = %s FOR UPDATE", (reviewer_id,))
        admin = cursor.fetchone()
        if not admin or admin["role"] != "admin":
            raise ReviewAccessError()
        lock_seller(cursor, user_id)
        cursor.execute("SELECT status, version FROM seller_applications WHERE user_id = %s FOR UPDATE", (user_id,))
        existing = cursor.fetchone()
        if not existing:
            raise ReviewNotFound()
        if existing["version"] != version or existing["status"] not in {"pending", "appeal_pending"}:
            raise ReviewConflict()
        reasons = reasons if action == "rejected" else []
        cursor.execute("""UPDATE seller_applications SET status = %s, reasons = %s, reviewer_notes = %s,
            reviewer_id = %s, reviewed_at = %s, updated_at = %s, version = version + 1 WHERE user_id = %s""",
            (action, json.dumps(reasons), notes, reviewer_id, now(), now(), user_id))
        cursor.execute("UPDATE seller_profiles SET verification_status = %s WHERE user_id = %s", (action, user_id))
        record_event(cursor, user_id, reviewer_id, action, action, reasons, notes)
        connection.commit()


def appeal(user_id, version, text, links):
    text = str(text or "").strip()
    if not 30 <= len(text) <= 3000:
        raise ReviewValidationError("Explain the corrections in 30–3,000 characters.")
    links = [line.strip() for line in str(links or "").splitlines() if line.strip()]
    if len(links) > 5:
        raise ReviewValidationError("Add no more than five supporting links, one per line.")
    for link in links:
        try:
            url = urlsplit(link)
            valid = (len(link) <= 500 and url.scheme in {"https", "http"} and url.hostname
                     and not url.username and not url.password and not re.search(r"[\s\\\x00-\x1f]", link))
        except ValueError:
            valid = False
        if not valid:
            raise ReviewValidationError("Use complete http:// or https:// supporting links without spaces or account credentials.")
    with database(write=True) as (connection, cursor):
        lock_seller(cursor, user_id)
        cursor.execute("SELECT status, version FROM seller_applications WHERE user_id = %s FOR UPDATE", (user_id,))
        existing = cursor.fetchone()
        if not existing:
            raise ReviewNotFound()
        if existing["status"] != "rejected" or existing["version"] != version:
            raise ReviewConflict()
        cursor.execute("""UPDATE seller_applications SET status = 'appeal_pending', appeal_text = %s,
            appeal_links = %s, appealed_at = %s, updated_at = %s, version = version + 1 WHERE user_id = %s""",
            (text, json.dumps(links), now(), now(), user_id))
        cursor.execute("UPDATE seller_profiles SET verification_status = 'appeal_pending' WHERE user_id = %s", (user_id,))
        record_event(cursor, user_id, user_id, "appealed", "appeal_pending", notes=text)
        connection.commit()
