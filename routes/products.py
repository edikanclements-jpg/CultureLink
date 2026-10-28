"""Akhil's product routes with the Discover form and input validation."""

from decimal import Decimal, InvalidOperation

from flask import Blueprint, abort, render_template, request
from services.products import get_all_products, get_product_by_id
from services.search import SORTS, search_products


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
    sizes = _values(products, "size", split=True)
    unknown_sizes = {"to be measured", "to be determined", "unknown", "not specified"}
    sizes = [size for size in sizes if size.casefold() not in unknown_sizes]
    size_order = {size: index for index, size in enumerate(["XXS", "XS", "S", "M", "L", "XL", "XXL", "XXXL"])}
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
