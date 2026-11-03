"""Invented prototype averages, never measured seller or carrier performance.

Edit the six records here to adjust the demo. The scenario assumes shipping
from each company's project location to a US address. No buyer address is read.
"""
from services.catalog_rules import seller_location


DEMO_TIMINGS = {
    1: {"name": "Anita Dongre", "production_days": 7, "shipping_days": 8},
    2: {"name": "Anu Attires", "production_days": 10, "shipping_days": 4},
    5: {"name": "The India Craft House", "production_days": 6, "shipping_days": 10},
    6: {"name": "Klothouse", "production_days": 15, "shipping_days": 3},
    7: {"name": "Olis Collections", "production_days": 20, "shipping_days": 12},
    8: {"name": "Priscer Luxe", "production_days": 12, "shipping_days": 7},
}


def timing_for(seller_id, name):
    if not isinstance(seller_id, int) or isinstance(seller_id, bool):
        return None
    row = DEMO_TIMINGS.get(seller_id)
    if not isinstance(row, dict) or not isinstance(name, str) or not isinstance(row.get("name"), str):
        return None
    if name.strip().casefold() != row["name"].casefold():
        return None
    production, shipping = row.get("production_days"), row.get("shipping_days")
    if not all(isinstance(days, int) and not isinstance(days, bool) and 1 <= days <= 120 for days in (production, shipping)):
        return None
    origin = seller_location(seller_id, name, "")
    if not origin:
        return None
    total = production + shipping
    return {
        "is_demo": True, "origin": origin, "destination": "USA",
        "production_days": production, "shipping_days": shipping, "total_days": total,
        "production_label": f"{production} business days", "shipping_label": f"{shipping} business days",
        "total_label": f"{total} business days",
    }
