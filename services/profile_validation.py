"""Validate buyer and seller profile fields before writing to MySQL."""

from decimal import Decimal, InvalidOperation
import re
from urllib.parse import urlsplit


ADDRESS_FIELDS = {
    "address_line1": (255, "Street address"),
    "address_line2": (255, "Address line 2"),
    "city": (100, "City"), "state": (100, "State or region"),
    "postal_code": (20, "Postal code"), "country": (100, "Country"),
}
BUYER_FIELDS = {
    "full_name": (150, "Full name"), "phone": (40, "Phone number"),
    "color_preferences": (255, "Favorite colors"),
    "culture_preferences": (255, "Cultures you shop for"),
    "occasion_preferences": (255, "Occasions you shop for"),
}
SELLER_FIELDS = {
    "contact_name": (150, "Contact name"), "business_name": (150, "Business name"),
    "phone": (40, "Phone number"), "description": (2000, "About your business"),
    "website_url": (255, "Website"), "social_url": (255, "Social page"),
    "cultures": (255, "Cultures represented"), "occasions": (255, "Occasions"),
    "clothing_types": (255, "Clothing types"), "lead_time": (150, "Typical lead time"),
    "price_info": (255, "Price guide"), "shipping_regions": (255, "Delivery areas"),
}
MEASUREMENTS = {"chest": "Chest / bust", "waist": "Waist", "hips": "Hips", "height": "Height"}


def _text_values(form, fields, errors):
    values = {}
    for name, (maximum, label) in fields.items():
        value = str(form.get(name, "") or "").strip()
        values[name] = value
        if len(value) > maximum:
            errors[name] = f"{label} must be {maximum} characters or fewer."
        elif re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", value):
            errors[name] = f"Please remove special control characters from {label.lower()}."
    return values


def _address(form, errors, seller=False):
    values = _text_values(form, ADDRESS_FIELDS, errors)
    required = ["city", "country"] if seller else (["address_line1", "city", "country"] if any(values.values()) else [])
    for name in required:
        if not values[name]:
            errors[name] = ADDRESS_FIELDS[name][1] + " is required for this address."
    if seller:
        location = ", ".join(values[name] for name in ["city", "state", "country"] if values[name])
        if len(location) > 150:
            errors["city"] = "Keep the city, state/region, and country within 150 characters combined."
    return values


def validate_buyer_profile(form):
    errors = {}
    values = _text_values(form, BUYER_FIELDS, errors)
    values.update(_address(form, errors))
    if not values["full_name"]:
        errors["full_name"] = "Enter your full name."
    values["measurement_unit"] = form.get("measurement_unit", "in")
    if values["measurement_unit"] not in {"in", "cm"}:
        errors["measurement_unit"] = "Choose inches or centimeters."
    for name, label in MEASUREMENTS.items():
        value = str(form.get(name, "") or "").strip()
        values[name] = value
        if not value:
            continue
        try:
            if len(value) > 12:
                raise ValueError()
            number = Decimal(value)
            if not number.is_finite() or not Decimal("0") < number <= Decimal("999.99"):
                raise ValueError()
            if number != number.quantize(Decimal("0.01")):
                raise ValueError()
        except (ValueError, InvalidOperation):
            errors[name] = f"Enter a positive {label.lower()} measurement, up to 999.99 with two decimal places."
    return values, errors


def _valid_link(value):
    if not value:
        return True
    if "\\" in value or any(character.isspace() for character in value):
        return False
    try:
        url = urlsplit(value)
        return url.scheme in {"http", "https"} and bool(url.hostname) and not url.username and not url.password and bool(url.netloc)
    except ValueError:
        return False


def validate_seller_profile(form):
    errors = {}
    values = _text_values(form, SELLER_FIELDS, errors)
    values.update(_address(form, errors, seller=True))
    for name in ["contact_name", "business_name", "cultures", "occasions", "clothing_types", "lead_time"]:
        if not values[name]:
            errors[name] = "Enter " + SELLER_FIELDS[name][1].lower() + "."
    for name in ["website_url", "social_url"]:
        if not _valid_link(values[name]):
            errors[name] = "Use a full http:// or https:// address."
    return values, errors
