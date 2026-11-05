"""Seller directory and public seller profiles."""

import re
from urllib.parse import urlsplit

from flask import Blueprint, abort, render_template, request, send_file
from services.boutiques import get_all_boutiques, get_boutique_by_id
from services.catalog_rules import canonical_location_query, COUNTRY_LOCATION_QUERIES
from services.indian_menswear import IMAGE_URLS as MENSWEAR_IMAGES
from services.profile_images import image_path
from services.profiles import public_seller_profiles

boutiques_bp = Blueprint("boutiques", __name__)

_INSTAGRAM_HANDLE = re.compile(r"[A-Za-z0-9_](?:[A-Za-z0-9_.]{0,28}[A-Za-z0-9_])?")
_INSTAGRAM_PAGES = {"accounts", "about", "api", "challenge", "direct", "explore",
                    "p", "reel", "reels", "share", "stories", "tv", "web"}


def _instagram_link(boutique):
    """Link to the supplied profile without affecting its evidence score."""
    account = boutique["verification"]["account"]
    if account:
        return account
    social = urlsplit(boutique["social_url"])
    if social.netloc.lower() not in {"instagram.com", "www.instagram.com", "m.instagram.com"}:
        return None
    handle = social.path.strip("/")
    if not _INSTAGRAM_HANDLE.fullmatch(handle) or ".." in handle or handle.casefold() in _INSTAGRAM_PAGES:
        return None
    return {"handle": handle, "url": f"https://www.instagram.com/{handle}/"}


@boutiques_bp.route("/boutiques")
def boutique_directory():
    boutiques = get_all_boutiques()
    cultures = sorted({culture for boutique in boutiques for culture in boutique["cultures"]})
    keyword = canonical_location_query(request.args.get("keyword", "").strip())
    culture = request.args.get("culture", "").strip()
    if culture:
        boutiques = [boutique for boutique in boutiques if culture in boutique["cultures"]]
    if keyword:
        def matches(boutique):
            if keyword.casefold() in COUNTRY_LOCATION_QUERIES:
                return keyword.casefold() in (boutique.get("location") or "").casefold()
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
    products = sorted(boutique["products"], key=lambda piece: piece.get("image_url") not in MENSWEAR_IMAGES)
    return render_template("boutique_details.html", boutique=boutique,
                           products=products, instagram=_instagram_link(boutique))


@boutiques_bp.route("/boutiques/<int:boutique_id>/images/<kind>")
def boutique_image(boutique_id, kind):
    if kind not in {"logo", "portrait"}:
        abort(404)
    profile = public_seller_profiles(boutique_id).get(boutique_id)
    if not profile or profile.get("verification_status") != "approved":
        abort(404)
    try:
        path = image_path(profile["user_id"], kind)
    except (OSError, ValueError):
        abort(404)
    if path is None:
        abort(404)
    # Revalidate every visit so replacement/removal is reflected immediately.
    response = send_file(path, mimetype="image/png", conditional=True, max_age=0)
    response.headers["Cache-Control"] = "public, no-cache"
    return response
