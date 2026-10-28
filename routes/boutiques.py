"""Akhil's seller-directory and seller-detail routes."""

from flask import Blueprint, abort, render_template, request
from services.boutiques import get_all_boutiques, get_boutique_by_id


boutiques_bp = Blueprint("boutiques", __name__)


@boutiques_bp.route("/boutiques")
def boutique_directory():
    boutiques = get_all_boutiques()
    cultures = sorted({culture for boutique in boutiques for culture in boutique["cultures"]})
    keyword = request.args.get("keyword", "").strip()
    culture = request.args.get("culture", "").strip()
    if culture:
        boutiques = [boutique for boutique in boutiques if culture in boutique["cultures"]]
    if keyword:
        def matches(boutique):
            text = " ".join([boutique["boutique_name"], boutique.get("location") or "",
                             boutique.get("description") or "", *boutique["cultures"]])
            return keyword.casefold() in text.casefold()
        boutiques = [boutique for boutique in boutiques if matches(boutique)]
    return render_template("boutiques.html", boutiques=boutiques,
                           cultures=cultures, keyword=keyword, culture=culture)


@boutiques_bp.route("/boutiques/<int:boutique_id>")
def boutique_details(boutique_id):
    boutique = get_boutique_by_id(boutique_id)
    if boutique is None:
        abort(404)
    return render_template("boutique_details.html", boutique=boutique,
                           products=boutique["products"])
