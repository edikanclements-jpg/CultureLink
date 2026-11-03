"""Akhil's product routes with the Discover form and input validation."""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, render_template, request, url_for
from services.products import get_all_products, get_product_by_id
from services.search import SORTS, search_products
from services.catalog_rules import canonical_size, size_labels, STANDARD_SIZES, CUSTOM_SIZE, canonical_location_query


products_bp = Blueprint("products", __name__)

SORT_LABELS = [
    ("name_asc", "Name: A to Z"),
    ("name_desc", "Name: Z to A"),
    ("seller", "Seller name"),
    ("price_asc", "Price: low to high"),
    ("price_desc", "Price: high to low"),
]


def _values(products, key, split=False):
    values = set()
    for product in products:
        text = product.get(key) or ""
        for value in text.split(",") if split else [text]:
            value = value.strip()
            if value:
                values.add(value)
    return sorted(values, key=str.casefold)


def _filter_options(products):
    """Build choices from the actual catalog rather than invented sample values."""
    sizes = sorted({label for product in products for label in size_labels(product.get("size"))})
    size_order = {size: index for index, size in enumerate(STANDARD_SIZES)}
    sizes.sort(key=lambda size: (size_order.get(size, 100), size.casefold()))
    locations = [(value, value) for value in _values(products, "seller_location")]
    if any(not (product.get("seller_location") or "").strip() for product in products):
        locations.append(("__unlisted__", "Location not provided"))
    return {
        "culture": [(value, value) for value in _values(products, "culture")],
        "occasion": [(value, value) for value in _values(products, "occasion", split=True)],
        "color": [(value, value) for value in _values(products, "color", split=True)],
        "size": [(value, value) for value in sizes],
        "location": locations,
        "currency": [(value, "USD — US dollar" if value == "USD" else "INR — Indian rupee")
                     for value in _values(products, "price_currency")],
    }


def _read_price(text, label, errors):
    if not text:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        errors.append(f"Enter a number for {label.lower()}.")
        return None
    if not value.is_finite() or value < 0:
        errors.append(f"{label} must be a finite number of zero or more.")
        return None
    return value


@products_bp.route("/products")
def product_catalog():
    """Show Discover and apply the submitted filters through Python."""
    keys = ("keyword", "culture", "occasion", "size", "color", "location", "currency", "min_price", "max_price")
    filters = {key: request.args.get(key, "").strip() for key in keys}
    # Keep old bookmarked size links working, with the canonical option selected.
    if filters["size"]:
        filters["size"] = canonical_size(filters["size"]) or filters["size"]
    filters["location"] = canonical_location_query(filters["location"])
    filters["sort"] = request.args.get("sort", "name_asc").strip()
    errors = []
    min_price = _read_price(filters["min_price"], "Minimum price", errors)
    max_price = _read_price(filters["max_price"], "Maximum price", errors)
    if filters["currency"] not in {"", "USD", "INR"}:
        errors.append("Choose USD or INR from the currency list.")
    if filters["sort"] not in SORTS:
        errors.append("Choose one of the listed sorting options.")
    price_filter = bool(filters["min_price"] or filters["max_price"])
    price_sort = filters["sort"] in {"price_asc", "price_desc"}
    if (price_filter or price_sort) and not filters["currency"]:
        errors.append("Choose a currency when filtering or sorting by price.")
    if min_price is not None and max_price is not None and min_price > max_price:
        errors.append("Minimum price must be less than or equal to maximum price.")

    catalog = get_all_products()
    custom_price_restricted = filters["size"] == CUSTOM_SIZE and bool(filters["currency"] or price_filter or price_sort)
    custom_filters = {key: value for key, value in filters.items() if value and key not in {"currency", "min_price", "max_price", "sort"}}
    custom_filters["sort"] = "name_asc" if price_sort else filters["sort"]
    if errors:
        products = []
    else:
        products = search_products(
            keyword=filters["keyword"], culture=filters["culture"],
            occasion=filters["occasion"], size=filters["size"],
            color=filters["color"], location=filters["location"],
            currency=filters["currency"], min_price=min_price, max_price=max_price,
            sort=filters["sort"],
        )
    return render_template(
        "products.html", products=products, filters=filters,
        options=_filter_options(catalog), errors=errors, sort_labels=SORT_LABELS,
        custom_price_restricted=custom_price_restricted,
        custom_price_url=url_for('products.product_catalog', **custom_filters),
    )


@products_bp.route("/products/<int:product_id>")
def product_details(product_id):
    """Display a real catalog piece and its seller information."""
    product = get_product_by_id(product_id)
    if product is None:
        abort(404)
    return render_template("product_details.html", product=product)


@products_bp.app_errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404
