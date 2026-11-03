"""Owned seller pieces can be prepared before a business has been approved."""
from decimal import Decimal, InvalidOperation
import hashlib
from pathlib import Path
import re

from flask import current_app, url_for
from services.catalog_rules import canonical_size, has_custom_size
from services.profile_images import _atomic_write
from services.seller_review_schema import database
from services.seller_reviews import lock_seller, touch, ReviewConflict, ReviewNotFound, ReviewValidationError

ITEM_SELECT = """SELECT i.*, inv.user_id, inv.photo_name, inv.version, inv.request_key,
    c.culture_name, s.seller_name, p.verification_status FROM seller_inventory inv
    JOIN items i ON i.item_id = inv.item_id JOIN sellers s ON s.seller_id = i.seller_id
    JOIN cultures c ON c.culture_id = i.culture_id JOIN seller_profiles p ON p.user_id = inv.user_id"""


def choices():
    with database() as (_, cursor):
        cursor.execute("SELECT culture_id, culture_name FROM cultures ORDER BY culture_name")
        cultures = cursor.fetchall()
        cursor.execute("SELECT occasion_id, occasion_name FROM occasions ORDER BY occasion_name")
        return cultures, cursor.fetchall()


def validate_item(form):
    values = {name: str(form.get(name, "") or "").strip() for name in
              ("item_name", "description", "category", "color", "size", "culture_id", "price", "currency", "size_mode")}
    values["occasion_ids"] = list(dict.fromkeys(form.getlist("occasion_ids")))
    errors = {}
    for name, maximum, label in (("item_name",200,"Piece name"),("category",100,"Clothing type"),
                                  ("description",2000,"Description"),("color",100,"Colors"),("size",100,"Sizes")):
        if len(values[name]) > maximum or re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", values[name]):
            errors[name] = f"Keep {label.lower()} within {maximum} characters and remove control characters."
    for name in ("item_name", "category", "description", "color"):
        if not values[name]:
            errors[name] = "Complete this field."
    cultures, occasions = choices()
    if values["culture_id"] not in {str(c["culture_id"]) for c in cultures}:
        errors["culture_id"] = "Choose a listed culture."
    allowed_occasions = {str(o["occasion_id"]) for o in occasions}
    if not values["occasion_ids"] or not set(values["occasion_ids"]) <= allowed_occasions:
        errors["occasion_ids"] = "Choose at least one listed occasion."
    if values["size_mode"] == "custom":
        values["size"] = "Custom Sizes"
    elif values["size_mode"] != "standard" or not canonical_size(values["size"]) or has_custom_size(values["size"]):
        errors["size"] = "Choose Custom Sizes or enter the standard sizes you offer."
    else:
        values["size"] = canonical_size(values["size"])
    values["stored_price"] = Decimal("0")
    values["price_notes"] = "Price to be determined."
    if values["size_mode"] == "custom":
        values["price"] = ""; values["currency"] = ""
        values["price_notes"] = "Custom sizing and final pricing will be confirmed together. Price to be determined."
    elif values["price"]:
        try:
            if len(values["price"]) > 12:
                raise ValueError()
            price = Decimal(values["price"])
            if (not price.is_finite() or not Decimal("0") < price <= Decimal("99999999.99")
                    or price != price.quantize(Decimal("0.01"))):
                raise ValueError()
            if values["currency"] not in {"USD", "INR"}:
                errors["currency"] = "Choose USD or INR for a fixed price."
            else:
                values["stored_price"] = price
                values["price_notes"] = values["currency"] + " fixed price."
        except (ValueError, InvalidOperation):
            errors["price"] = "Enter a positive price with at most two decimal places."
    return values, errors


def _present(row):
    row = dict(row)
    row["photo_url"] = url_for("onboarding.seller.item_photo", item_id=row["item_id"], v=row["photo_name"].removesuffix(".png")) if row["photo_name"] else ""
    row["display_price"] = "Price to be determined" if not row["price"] or has_custom_size(row["size"]) else f"{'INR' if 'INR' in (row['price_notes'] or '') else 'USD'} {row['price']:,.2f}"
    return row


def list_items(user_id):
    with database() as (_, cursor):
        cursor.execute(ITEM_SELECT + " WHERE inv.user_id = %s ORDER BY inv.item_id DESC", (user_id,))
        return [_present(row) for row in cursor.fetchall()]


def item_for(item_id):
    with database() as (_, cursor):
        cursor.execute(ITEM_SELECT + " WHERE inv.item_id = %s", (item_id,))
        row = cursor.fetchone()
        if row is None:
            raise ReviewNotFound()
        row = _present(row)
        cursor.execute("SELECT occasion_id FROM itemoccasions WHERE item_id = %s", (item_id,))
        row["occasion_ids"] = [str(o["occasion_id"]) for o in cursor.fetchall()]
        return row


def item_values(item):
    return {**item, "culture_id": str(item["culture_id"]),
            "size_mode": "custom" if has_custom_size(item["size"]) else "standard",
            "price": str(item["price"]) if item["price"] else "",
            "currency": "INR" if "INR" in (item["price_notes"] or "") else "USD"}


def photo_path(item):
    name = item.get("photo_name", "")
    if not re.fullmatch(r"[a-f0-9]{64}\.png", name):
        return None
    path = Path(current_app.instance_path) / "seller-items" / ("user-" + str(item["user_id"])) / name
    return path if path.is_file() else None


def save_item(user_id, values, photo, request_key, item_id=None, version=None):
    if not re.fullmatch(r"[a-f0-9]{32}", request_key or ""):
        raise ReviewValidationError("Refresh the piece form and try again.")
    with database(write=True) as (connection, cursor):
        _, seller_id = lock_seller(cursor, user_id)
        cursor.execute("SELECT user_id FROM seller_applications WHERE user_id = %s FOR UPDATE", (user_id,))
        if cursor.fetchone() is None:
            raise ReviewNotFound()
        if item_id is None:
            cursor.execute("SELECT item_id FROM seller_inventory WHERE user_id = %s AND request_key = %s", (user_id, request_key))
            duplicate = cursor.fetchone()
            if duplicate:
                connection.commit(); return duplicate["item_id"]
            cursor.execute("SELECT COUNT(*) AS total FROM seller_inventory WHERE user_id = %s", (user_id,))
            if cursor.fetchone()["total"] >= 100:
                raise ReviewValidationError("This prototype supports up to 100 pieces per seller.")
            old = None
        else:
            cursor.execute("SELECT version, photo_name FROM seller_inventory WHERE user_id = %s AND item_id = %s FOR UPDATE", (user_id, item_id))
            old = cursor.fetchone()
            if old is None:
                raise ReviewNotFound()
            if old["version"] != version:
                raise ReviewConflict()
        photo_name = old["photo_name"] if old else ""
        if photo is not None:
            directory = Path(current_app.instance_path) / "seller-items" / ("user-" + str(user_id))
            directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            photo_name = hashlib.sha256(photo).hexdigest() + ".png"
            # The DB publishes this filename only after all item writes commit.
            _atomic_write(directory / photo_name, photo)
        if not photo_name:
            raise ReviewValidationError("Add a product photo before saving this piece.")
        data = (int(values["culture_id"]), values["item_name"], values["description"], values["category"],
                values["stored_price"], values["price_notes"], values["color"], values["size"])
        if old:
            cursor.execute("""UPDATE items SET culture_id = %s, item_name = %s, description = %s,
                category = %s, price = %s, price_notes = %s, color = %s, size = %s
                WHERE item_id = %s AND seller_id = %s""", data + (item_id, seller_id))
            cursor.execute("UPDATE seller_inventory SET photo_name = %s, version = version + 1, updated_at = CURRENT_TIMESTAMP WHERE item_id = %s AND user_id = %s", (photo_name,item_id,user_id))
        else:
            cursor.execute("""INSERT INTO items (seller_id, culture_id, item_name, description, category,
                price, price_notes, color, size) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""", (seller_id,) + data)
            item_id = cursor.lastrowid
            cursor.execute("INSERT INTO seller_inventory (item_id, user_id, photo_name, request_key) VALUES (%s, %s, %s, %s)", (item_id,user_id,photo_name,request_key))
        image_url = url_for("onboarding.seller.item_photo", item_id=item_id, v=photo_name.removesuffix(".png"))
        cursor.execute("UPDATE items SET image_url = %s WHERE item_id = %s AND seller_id = %s", (image_url,item_id,seller_id))
        cursor.execute("DELETE FROM itemoccasions WHERE item_id = %s", (item_id,))
        for occasion in values["occasion_ids"]:
            cursor.execute("INSERT INTO itemoccasions (item_id, occasion_id) VALUES (%s, %s)", (item_id,int(occasion)))
        touch(cursor, user_id)
        connection.commit()
        return item_id
