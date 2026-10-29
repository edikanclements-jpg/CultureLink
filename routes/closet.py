"""Buyer-only Saved Closet, shared save controls, and HTML/JSON responses."""

from functools import wraps
import re
import secrets
from urllib.parse import unquote, urlsplit, urlunsplit

from flask import Blueprint, abort, current_app, flash, g, jsonify, make_response, redirect, render_template, request, session, url_for
from mysql.connector import Error
from services.closet import ClosetAccessError, ClosetItemNotFound, saved_item_ids, saved_products, set_saved
from services.comparison import ComparisonItemError, ComparisonLimitError, change_selection, selection_ids
from services import outfits as outfit_service
from services import shopping as shopping_service
from services import shopping_ai
from services.account_security import AttemptLimiter

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
    if parts.scheme or parts.netloc or not re.fullmatch(r"/(?:closet(?:/(?:compare|assistant))?|(?:products|boutiques)(?:/[0-9]+)?)?", parts.path):
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


def _outfit_problem():
    current_app.logger.warning("Could not open the current buyer's outfit planner.")
    return render_template("outfits/index.html", outfits=[], problem="We couldn't open your outfit planner right now. Your saved pieces are still in your Closet. Please try again in a moment."), 503


def _positive_integer(value):
    if not isinstance(value, str) or not re.fullmatch(r"[1-9][0-9]{0,9}", value):
        return None
    number = int(value)
    return number if number <= 4294967295 else None


@closet_bp.route("/closet/outfits")
@buyer_required
def outfits():
    try:
        looks = outfit_service.list_outfits(g.user["user_id"])
    except Error:
        return _outfit_problem()
    return render_template("outfits/index.html", outfits=looks, problem=None)


@closet_bp.route("/closet/outfits/<int:outfit_id>")
@buyer_required
def outfit_detail(outfit_id):
    try:
        outfit = outfit_service.get_outfit(g.user["user_id"], outfit_id)
    except outfit_service.OutfitNotFound:
        abort(404)
    except Error:
        return _outfit_problem()
    return render_template("outfits/detail.html", outfit=outfit, problem=None)


def _outfit_editor(outfit_id=None):
    try:
        outfit = outfit_service.get_outfit(g.user["user_id"], outfit_id) if outfit_id is not None else None
        outfit_service.ensure_schema()
        saved = saved_products(g.user["user_id"])
    except outfit_service.OutfitNotFound:
        abort(404)
    except Error:
        return _outfit_problem()
    saved_ids = {piece["product_id"] for piece in saved}
    choices = {piece["product_id"]: piece for piece in (outfit["products"] if outfit else [])}
    choices.update({piece["product_id"]: piece for piece in saved})
    values = {key: outfit[key] if outfit else "" for key in ("name", "occasion", "notes")}
    selected = [piece["product_id"] for piece in outfit["products"]] if outfit else []
    request_key = secrets.token_hex(16)
    errors, status = [], 200
    if request.method == "POST":
        values = {key: request.form.get(key, "").strip() for key in values}
        for key, maximum, label in (("name", 80, "Outfit name"), ("occasion", 80, "Occasion"), ("notes", 500, "Notes")):
            if len(values[key]) > maximum or any((ord(char) < 32 and (key != "notes" or char not in "\t\n\r")) or ord(char) == 127 for char in values[key]):
                errors.append(f"{label} must use normal text and no more than {maximum} characters.")
        if not values["name"]:
            errors.append("Give your outfit a name.")
        submitted = request.form.getlist("item_ids")
        parsed = [_positive_integer(value) for value in submitted]
        selected = list(dict.fromkeys(value for value in parsed if value is not None))
        if not 1 <= len(submitted) <= outfit_service.MAX_PIECES or None in parsed or len(selected) != len(submitted):
            errors.append("Choose between 1 and 8 different pieces.")
        request_key = request.form.get("request_key", "")
        version = _positive_integer(request.form.get("version", ""))
        if outfit is None and not re.fullmatch(r"[0-9a-f]{32}", request_key):
            errors.append("This form is incomplete. Review your outfit and save again.")
            request_key = secrets.token_hex(16)
        if outfit is not None and version is None:
            errors.append("This form is out of date. Review your outfit and save again.")
        if not errors:
            try:
                saved_id = outfit_service.save_outfit(g.user["user_id"], values, selected, request_key, outfit_id, version)
            except outfit_service.OutfitNotFound:
                abort(404)
            except outfit_service.OutfitSelectionError:
                errors.append("A selected piece is no longer in your Closet. Choose your pieces again. Existing outfit pieces can still be kept.")
                status = 409
            except outfit_service.OutfitConflict:
                errors.append("This outfit changed in another tab. Review your choices against the latest saved outfit before saving again.")
                status = 409
                try:
                    outfit = outfit_service.get_outfit(g.user["user_id"], outfit_id)
                    choices = {piece["product_id"]: piece for piece in outfit["products"]}
                    choices.update({piece["product_id"]: piece for piece in saved})
                except outfit_service.OutfitNotFound:
                    abort(404)
                except Error:
                    return _outfit_problem()
            except ClosetAccessError:
                return _problem("The outfit planner is available with a buyer account.", 403)
            except Error:
                current_app.logger.warning("Could not save the current buyer's outfit.")
                errors.append("We couldn't save your outfit. Your entries are still here. Please try again.")
                status = 503
            else:
                flash("Outfit updated." if outfit else "Outfit saved. Make it yours whenever you're ready.", "success")
                return redirect(url_for("closet.outfit_detail", outfit_id=saved_id), code=303)
        if errors and status == 200:
            status = 400
    selected = [item_id for item_id in selected if item_id in choices]
    return render_template("outfits/editor.html", outfit=outfit, values=values, choices=list(choices.values()), saved_ids=saved_ids,
                           selected=selected, request_key=request_key, errors=errors, max_pieces=outfit_service.MAX_PIECES), status


@closet_bp.route("/closet/outfits/new", methods=["GET", "POST"])
@buyer_required
def outfit_new():
    return _outfit_editor()


@closet_bp.route("/closet/outfits/<int:outfit_id>/edit", methods=["GET", "POST"])
@buyer_required
def outfit_edit(outfit_id):
    return _outfit_editor(outfit_id)


@closet_bp.route("/closet/outfits/<int:outfit_id>/delete", methods=["POST"])
@buyer_required
def outfit_delete(outfit_id):
    version = _positive_integer(request.form.get("version", ""))
    if version is None or request.form.get("confirm_delete") != "yes":
        abort(400)
    try:
        outfit_service.delete_outfit(g.user["user_id"], outfit_id, version)
    except outfit_service.OutfitNotFound:
        abort(404)
    except outfit_service.OutfitConflict:
        flash("This outfit changed in another tab. Review the latest version before deleting it.", "info")
        return redirect(url_for("closet.outfit_detail", outfit_id=outfit_id), code=303)
    except ClosetAccessError:
        return _problem("The outfit planner is available with a buyer account.", 403)
    except Error:
        current_app.logger.warning("Could not delete the current buyer's outfit.")
        flash("We couldn't delete your outfit. Please try again.", "info")
        return redirect(url_for("closet.outfit_detail", outfit_id=outfit_id), code=303)
    flash("Outfit deleted. Your saved Closet pieces are still there.", "success")
    return redirect(url_for("closet.outfits"), code=303)


def _guide_state():
    state = session.get("_shopping_guide")
    if not isinstance(state, dict) or state.get("user_id") != g.user["user_id"]:
        return {"filters": shopping_service.empty_filters(), "query": "", "mode": "catalog", "action": "search", "notice": ""}
    try:
        state["filters"] = shopping_service.validate_filters(state["filters"])
        if not isinstance(state.get("query"), str) or len(state["query"]) > 400:
            raise ValueError()
        if state.get("mode") not in {"catalog", "ai"} or state.get("action") not in shopping_ai.ACTIONS:
            raise ValueError()
    except (shopping_service.GuideInputError, KeyError, TypeError, ValueError):
        session.pop("_shopping_guide", None)
        return {"filters": shopping_service.empty_filters(), "query": "", "mode": "catalog", "action": "search", "notice": ""}
    return state


def _guide_response(result=None, error=None, status=200, draft="", retry_after=None):
    response = make_response(render_template("shopping.html", result=result, error=error, draft=draft,
                                           ai_configured=bool(shopping_ai.settings()["key"]), has_context=bool(_guide_state()["query"]),
                                           refine_checked=request.method != "POST" or request.form.get("refine") == "yes",
                                           use_ai_checked=request.method != "POST" or request.form.get("use_ai") == "yes"), status)
    response.headers["Cache-Control"] = "no-store"
    if retry_after is not None:
        response.headers["Retry-After"] = str(retry_after)
    return response


@closet_bp.route("/closet/assistant", methods=["GET", "POST"])
@buyer_required
def assistant():
    state = _guide_state()
    if request.method == "POST":
        text = request.form.get("example") or request.form.get("query", "")
        limiter = current_app.extensions.setdefault("shopping_attempts", AttemptLimiter())
        retry_after = limiter.consume(g.user["user_id"], 30, 60)
        if retry_after:
            return _guide_response(error="Let's pause for a moment. Try your search again in a minute.", status=429, draft=text[:400], retry_after=retry_after)
        previous = state["filters"] if request.form.get("refine") == "yes" and not request.form.get("example") else shopping_service.empty_filters()
        try:
            result = shopping_service.answer(text, previous, g.user["user_id"], use_ai=request.form.get("use_ai") == "yes")
        except shopping_service.GuideInputError as error:
            return _guide_response(error=str(error), status=400, draft=text[:400])
        except Error:
            current_app.logger.warning("Could not read catalog data for the shopping guide.")
            return _guide_response(error="We couldn't open the catalog right now. Your search text is still here. Please try again in a moment.", status=503, draft=text[:400])
        session["_shopping_guide"] = {"user_id": g.user["user_id"], **{key: result[key] for key in ("filters", "query", "mode", "action", "notice")}}
        # Refreshing the result page never resubmits an AI request.
        return redirect(url_for("closet.assistant"), code=303)
    try:
        result = shopping_service.result_for(state["filters"], state["query"], state["mode"], state.get("notice", ""), state["action"])
    except Error:
        current_app.logger.warning("Could not read catalog data for the shopping guide.")
        return _guide_response(error="We couldn't open the catalog right now. Please try again in a moment.", status=503)
    return _guide_response(result=result)


@closet_bp.route("/closet/assistant/reset", methods=["POST"])
@buyer_required
def assistant_reset():
    session.pop("_shopping_guide", None)
    return redirect(url_for("closet.assistant"), code=303)
