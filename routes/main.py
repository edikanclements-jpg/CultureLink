"""Akhil's homepage route, with featured pieces selected from the real catalog."""

from flask import Blueprint, render_template
from services.products import get_all_products
from services.boutiques import get_all_boutiques


main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def home():
    products = get_all_products()
    boutiques = get_all_boutiques()
    featured = []
    featured_sellers = set()
    for product in products:
        if product["boutique_id"] not in featured_sellers:
            featured.append(product)
            featured_sellers.add(product["boutique_id"])
    # This is the supplied Klothouse red dress, an editorial hero selection.
    hero_product = next((product for product in products if product["product_id"] == 45), None)
    if hero_product is None:
        hero_product = next((product for product in products if product["culture"] == "Nigerian"), products[0] if products else None)
    cultures = sorted({product["culture"] for product in products})
    occasions = sorted({occasion.strip() for product in products for occasion in (product.get("occasion") or "").split(",") if occasion.strip()})
    return render_template("index.html", products=products, boutiques=boutiques,
                           featured=featured, hero_product=hero_product,
                           cultures=cultures, occasions=occasions)
