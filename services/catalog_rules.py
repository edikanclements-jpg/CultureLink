"""Shared catalog labels and project locations for the six curated companies.

Original database sizes and prices are retained. Custom-size pieces use a
quote-based public price, consistently across browsing, budgets and the Guide.
"""
import re

CUSTOM_SIZE = "Custom Sizes"
UNKNOWN_SIZES = {"", "to be determined", "unknown", "not specified", "not provided"}
CUSTOM_ALIASES = {"custom", "custom size", "custom sizes", "custom sizing",
                  "to be measured", "made to measure", "bespoke"}
STANDARD_SIZES = ("XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL")
COUNTRY_LOCATION_QUERIES = {"india", "nigeria", "united kingdom", "usa"}
KLOTHOUSE_LOCATION = "Houston, Texas, USA"
LOCATION_OVERRIDES = {
    1: ("Anita Dongre", "Navi Mumbai, India"),
    2: ("Anu Attires", "Dallas, Texas, USA"),
    5: ("The India Craft House", "Gurgaon, Haryana, India"),
    6: ("Klothouse", KLOTHOUSE_LOCATION),
    7: ("Olis Collections", "Nigeria"),
    8: ("Priscer Luxe", "United Kingdom"),
}


def _sql_literal(value):
    return "'" + value.replace("'", "''") + "'"


# Only these code-owned values are interpolated; request values stay parameters.
SELLER_LOCATION_SQL = "(CASE " + " ".join(
    f"WHEN s.seller_id = {identifier} AND LOWER(TRIM(s.seller_name)) = {_sql_literal(name.casefold())} "
    f"THEN {_sql_literal(location)}"
    for identifier, (name, location) in LOCATION_OVERRIDES.items()
) + " ELSE s.location END)"


def canonical_location_query(value):
    if isinstance(value, str) and value.strip().casefold() in {"uk", "u.k.", "britain", "united kingdom"}:
        return "United Kingdom"
    return value


def _key(value):
    return " ".join(re.sub(r"[-_]", " ", value).casefold().split())


def size_labels(value):
    """Normalize known labels; a missing size does not imply custom tailoring."""
    if not isinstance(value, str):
        return []
    labels, seen = [], set()
    for part in value.split(","):
        part = " ".join(part.split())
        key = _key(part)
        if key in UNKNOWN_SIZES:
            continue
        label = CUSTOM_SIZE if key in CUSTOM_ALIASES else part.upper() if part.upper() in STANDARD_SIZES else part
        if label.casefold() not in seen:
            labels.append(label)
            seen.add(label.casefold())
    return labels


def canonical_size(value):
    labels = size_labels(value)
    return ", ".join(labels)


def has_custom_size(value):
    return CUSTOM_SIZE in size_labels(value)


def matches_size(value, requested):
    choices = {label.casefold() for label in size_labels(value)}
    requested_labels = size_labels(requested)
    return len(requested_labels) == 1 and requested_labels[0].casefold() in choices


def seller_location(seller_id, name, location):
    row = LOCATION_OVERRIDES.get(seller_id) if isinstance(seller_id, int) and not isinstance(seller_id, bool) else None
    if row and isinstance(name, str) and name.strip().casefold() == row[0].casefold():
        return row[1]
    return location.strip() if isinstance(location, str) else ""
