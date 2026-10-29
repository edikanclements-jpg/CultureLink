"""Buyer-only Saved Closet, shared save controls, and HTML/JSON responses."""

from functools import wraps
import re
import secrets
from urllib.parse import unquote, urlsplit, urlunsplit

from flask import Blueprint, current_app, flash, g, jsonify, redirect, render_template, request, session, url_for
from mysql.connector import Error
from services.closet import ClosetAccessError, ClosetItemNotFound, saved_item_ids, saved_products, set_saved
from services.comparison import ComparisonItemError, ComparisonLimitError, change_selection, selection_ids

closet_bp = Blueprint("closet", __name__)


def _json_requested():
    return request.accept_mimetypes["application/json"] > request.accept_mimetypes["text/html"]


def _problem(message, status=503):
    if _json_requested():
        return jsonify(error=message), status
    return render_template("closet.html", products=[], problem=message, can_retry=status == 503), status


def buyer_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            if _json_requested():
                return jsonify(error="Log in to save pieces to your closet.", redirect=url_for("auth.login")), 401
            flash("Log in to save pieces and open your closet.", "info")
            return redirect(url_for("auth.login"), code=303 if request.method == "POST" else 302)
        if g.user["role"] == "pending":
            if _json_requested():
                return jsonify(error="Choose Buyer to start your closet.", redirect=url_for("onboarding.choose_role")), 409
            return redirect(url_for("onboarding.choose_role"), code=303 if request.method == "POST" else 302)
        if g.user["role"] != "customer":
            return _problem("Saved Closet is available with a buyer account. You can keep exploring the collection from Discover.", 403)
        return view(*args, **kwargs)
    return wrapped


@closet_bp.app_context_processor
def closet_template_helpers():
    def is_saved(product_id):
        if not g.user or g.user["role"] != "customer":
            return False
        if not hasattr(g, "_closet_ids"):
            try:
                g._closet_ids = saved_item_ids(g.user["user_id"])
            except Error:
                current_app.logger.warning("Could not read saveditems for the current buyer.")
                g._closet_ids = None
        return None if g._closet_ids is None else product_id in g._closet_ids
    return {
        "is_saved_to_closet": is_saved,
        "closet_return_to": request.full_path if request.query_string else request.path,
    }


def _return_url(value):
    """Keep filters and a piece anchor, while allowing only catalog paths."""
    fallback = url_for("closet.index")
    if not isinstance(value, str) or len(value) > 3000:
        return fallback
    decoded = unquote(value)
    if any(ord(char) < 32 or ord(char) == 127 or char == "\\" for char in decoded):
        return fallback
    try:
        parts = urlsplit(value)
    except ValueError:
        return fallback
    if parts.scheme or parts.netloc or not re.fullmatch(r"/(?:closet(?:/compare)?|(?:products|boutiques)(?:/[0-9]+)?)?", parts.path):
        return fallback
    fragment = parts.fragment if re.fullmatch(r"piece-[0-9]+", parts.fragment) else ""
    return urlunsplit(("", "", parts.path, parts.query, fragment))


@closet_bp.route("/closet")
@buyer_required
def index():
    try:
        products = saved_products(g.user["user_id"])
    except Error:
        current_app.logger.warning("Could not open the current buyer's saveditems collection.")
        return _problem("We couldn't open your closet right now. Please try again in a moment.")
    g._closet_ids = {product["product_id"] for product in products}
    try:
        selected = selection_ids(g.user["user_id"], _comparison_scope())
    except Error:
        current_app.logger.warning("Could not read comparisonselections for the current buyer.")
        selected = None
    return render_template("closet.html", products=products, problem=None, compare_ids=selected)


def _change(product_id, saved):
    if not 0 < product_id <= 4294967295:
        return _problem("This piece is no longer available.", 404)
    try:
        result = set_saved(g.user["user_id"], product_id, saved)
    except ClosetAccessError:
        return _problem("Saved Closet is available with a buyer account.", 403)
    except ClosetItemNotFound:
        return _problem("This piece is no longer available.", 404)
    except Error:
        current_app.logger.warning("Could not update saveditems for the current buyer.")
        return _problem("We couldn't update your closet. Please try again.")
    if _json_requested():
        return jsonify(result)
    flash("Saved to your closet." if saved else "Removed from your closet.", "success")
    return redirect(_return_url(request.form.get("return_to", "")), code=303)


@closet_bp.route("/closet/items/<int:product_id>/save", methods=["POST"])
@buyer_required
def save(product_id):
    return _change(product_id, True)


@closet_bp.route("/closet/items/<int:product_id>/remove", methods=["POST"])
@buyer_required
def remove(product_id):
    return _change(product_id, False)


def _comparison_scope():
    # Never accept a buyer ID or scope token from the submitted form.
    token = session.get("_comparison_token")
    if not isinstance(token, str) or not re.fullmatch(r"[0-9a-f]{48}", token):
        token = secrets.token_hex(24)
        session["_comparison_token"] = token
    return str(g.user["user_id"]) + ":" + token


@closet_bp.route("/closet/compare")
@buyer_required
def compare():
    try:
        ids = selection_ids(g.user["user_id"], _comparison_scope())
        owned = {product["product_id"]: product for product in saved_products(g.user["user_id"])}
    except Error:
        current_app.logger.warning("Could not open the current buyer's comparison.")
        return render_template("comparison.html", products=[], problem="We couldn't open your comparison. Please try again in a moment."), 503
    products = [owned[item] for item in ids if item in owned]
    return render_template("comparison.html", products=products, problem=None)


def _comparison_change(product_id=None, selected=None):
    if product_id is not None and not 0 < product_id <= 4294967295:
        return _problem("Choose a piece from your saved closet.", 404)
    try:
        ids = change_selection(g.user["user_id"], _comparison_scope(), product_id, selected)
    except ComparisonLimitError:
        return _comparison_error("You can compare up to 3 pieces. Remove one selection to choose another.", 409)
    except ComparisonItemError:
        return _comparison_error("Save this piece to your closet before adding it to a comparison.", 404)
    except ClosetAccessError:
        return _problem("Comparisons are available with a buyer account.", 403)
    except Error:
        current_app.logger.warning("Could not update comparisonselections for the current buyer.")
        return _comparison_error("We couldn't update the comparison. Please try again.", 503)
    if _json_requested():
        return jsonify(selected=ids, count=len(ids))
    flash("Comparison selection updated.", "success")
    target = "closet.compare" if request.form.get("view") == "comparison" else "closet.index"
    return redirect(url_for(target), code=303)


def _comparison_error(message, status):
    if _json_requested():
        return jsonify(error=message), status
    flash(message, "info")
    target = "closet.compare" if request.form.get("view") == "comparison" else "closet.index"
    return redirect(url_for(target), code=303)


@closet_bp.route("/closet/compare/items/<int:product_id>/add", methods=["POST"])
@buyer_required
def compare_add(product_id):
    return _comparison_change(product_id, True)


@closet_bp.route("/closet/compare/items/<int:product_id>/remove", methods=["POST"])
@buyer_required
def compare_remove(product_id):
    return _comparison_change(product_id, False)


@closet_bp.route("/closet/compare/clear", methods=["POST"])
@buyer_required
def compare_clear():
    return _comparison_change()
