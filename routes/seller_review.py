"""Seller Studio and staff review routes, nested under the existing setup blueprint."""
from functools import wraps
import secrets
from flask import Blueprint, abort, current_app, flash, g, redirect, render_template, request, send_file, url_for
from mysql.connector import Error

from services.profiles import get_seller_profile
from services.profile_images import image_path, prepare_images
from services import seller_reviews as reviews, seller_inventory as inventory

seller_bp = Blueprint("seller", __name__)


def _unavailable():
    current_app.logger.warning("Seller review storage is unavailable.")
    return render_template("auth/message.html",title="Please try again shortly",
                           message="We couldn't load the seller workspace. Your saved information is preserved. Please try again shortly."),503


def roles(*allowed):
    def decorate(view):
        @wraps(view)
        def wrapped(*args,**kwargs):
            if g.user is None:
                return redirect(url_for("auth.login"))
            if g.user["role"] not in allowed:
                abort(403)
            try:
                return view(*args,**kwargs)
            except reviews.ReviewAccessError:
                abort(403)
            except reviews.ReviewNotFound:
                abort(404)
            except (Error,OSError):
                return _unavailable()
        return wrapped
    return decorate


def _version():
    value = request.form.get("version","")
    if not 1 <= len(value) <= 10 or not value.isascii() or not value.isdigit() or not 0 < int(value) <= 2**31-1:
        raise reviews.ReviewValidationError("Refresh this page before submitting again.")
    return int(value)


def _dashboard(errors=None,status=200):
    if get_seller_profile(g.user["user_id"]) is None:
        return redirect(url_for("onboarding.seller_profile"))
    application = reviews.application_for(g.user["user_id"])
    return render_template("seller/dashboard.html",application=application,
        pieces=inventory.list_items(g.user["user_id"]),events=reviews.history_for(g.user["user_id"]),
        errors=errors or {}, appeal_text=request.form.get("appeal_text",""), appeal_links=request.form.get("appeal_links",""),
        ),status


@seller_bp.route("/seller")
@roles("seller")
def dashboard():
    return _dashboard()


@seller_bp.route("/seller/submitted")
@roles("seller")
def submitted():
    if get_seller_profile(g.user["user_id"]) is None:
        return redirect(url_for("onboarding.seller_profile"))
    application = reviews.application_for(g.user["user_id"])
    if application["status"] not in {"pending", "appeal_pending"}:
        return redirect(url_for("onboarding.seller.dashboard"))
    return render_template("seller/submitted.html", application=application)


@seller_bp.route("/seller/appeal",methods=["POST"])
@roles("seller")
def submit_appeal():
    try:
        reviews.appeal(g.user["user_id"],_version(),request.form.get("appeal_text",""),request.form.get("appeal_links",""))
    except reviews.ReviewValidationError as error:
        return _dashboard({"form":str(error)},400)
    except reviews.ReviewConflict:
        return _dashboard({"form":"Your application changed in another tab. Review its current status before submitting an appeal."},409)
    flash("Your appeal is submitted. Review usually takes 3–6 business days. Your pieces are preserved.","success")
    return redirect(url_for("onboarding.seller.dashboard"))


def _item_editor(item_id=None):
    if get_seller_profile(g.user["user_id"]) is None:
        return redirect(url_for("onboarding.seller_profile"))
    application=reviews.application_for(g.user["user_id"])
    existing=inventory.item_for(item_id) if item_id is not None else None
    if existing and existing["user_id"] != g.user["user_id"]:
        abort(404)
    errors={};status=200
    values=inventory.item_values(existing) if existing else {"size_mode":"custom","currency":"USD","occasion_ids":[]}
    key=existing["request_key"] if existing else secrets.token_hex(16)
    if request.method=="POST":
        values,errors=inventory.validate_item(request.form)
        changes,photo_errors=prepare_images(request.files,request.form,("item",))
        errors.update(photo_errors);key=request.form.get("request_key","")
        if existing:
            values["photo_url"]=existing["photo_url"]
        if not errors:
            try:
                inventory.save_item(g.user["user_id"],values,changes.get("item"),key,item_id,_version() if existing else None)
            except reviews.ReviewValidationError as error:
                errors["form"]=str(error);status=400
            except reviews.ReviewConflict:
                errors["form"]="This piece changed in another tab. Reload it before saving your changes.";status=409
            else:
                flash("Your piece is saved and published." if application["status"]=="approved" else "Your piece is saved privately for review.","success")
                return redirect(url_for("onboarding.seller.dashboard"))
        else:
            status=400
        if request.files.get("photo_item") and errors:
            errors["photo_notice"]="Choose the product photo again after correcting these fields."
    cultures,occasions=inventory.choices()
    return render_template("seller/item_form.html",values=values,errors=errors,existing=existing,
        request_key=key,cultures=cultures,occasions=occasions,application=application),status


@seller_bp.route("/seller/pieces/new",methods=["GET","POST"])
@roles("seller")
def item_new():
    return _item_editor()


@seller_bp.route("/seller/pieces/<int:item_id>/edit",methods=["GET","POST"])
@roles("seller")
def item_edit(item_id):
    return _item_editor(item_id)


@seller_bp.route("/seller/items/<int:item_id>/photo")
def item_photo(item_id):
    try:
        item=inventory.item_for(item_id)
        allowed=item["verification_status"]=="approved" or (g.user and (g.user["role"]=="admin" or g.user["user_id"]==item["user_id"]))
        if not allowed:
            abort(404)
        path=inventory.photo_path(item)
        if path is None:
            abort(404)
        response=send_file(path,mimetype="image/png",conditional=True,max_age=0)
        response.headers["Cache-Control"]="no-store"
        return response
    except reviews.ReviewNotFound:
        abort(404)
    except (Error,OSError):
        abort(503)


@seller_bp.route("/team/seller-reviews")
@roles("admin")
def review_queue():
    status=request.args.get("status","pending")
    return render_template("seller/team_queue.html",applications=reviews.review_queue(status),
                           selected_status=status,review_statuses=reviews.STATUS_LABELS)


def _review_page(user_id,errors=None,status=200):
    application=reviews.application_for(user_id,enroll=False)
    if application is None:
        abort(404)
    profile=get_seller_profile(user_id)
    pictures={kind:url_for("onboarding.seller.applicant_image",user_id=user_id,kind=kind)
              for kind in ("logo","portrait") if image_path(user_id,kind)}
    return render_template("seller/team_review.html",application=application,profile=profile,pictures=pictures,
        pieces=inventory.list_items(user_id),events=reviews.history_for(user_id),rejection_reasons=reviews.REASONS,
        errors=errors or {}),status


@seller_bp.route("/team/seller-reviews/<int:user_id>")
@roles("admin")
def review_detail(user_id):
    return _review_page(user_id)


@seller_bp.route("/team/seller-reviews/<int:user_id>/decision",methods=["POST"])
@roles("admin")
def review_decision(user_id):
    try:
        reviews.decide(g.user["user_id"],user_id,_version(),request.form.get("action"),
                       request.form.getlist("reasons"),request.form.get("notes",""))
    except reviews.ReviewValidationError as error:
        return _review_page(user_id,{"form":str(error)},400)
    except reviews.ReviewConflict:
        return _review_page(user_id,{"form":"The seller's information or decision changed. Review the current application before deciding again."},409)
    flash("Decision saved. The seller can see it in Seller Studio.","success")
    return redirect(url_for("onboarding.seller.review_detail",user_id=user_id))


@seller_bp.route("/team/seller-reviews/<int:user_id>/images/<kind>")
@roles("admin")
def applicant_image(user_id,kind):
    if kind not in {"logo","portrait"} or get_seller_profile(user_id) is None:
        abort(404)
    path=image_path(user_id,kind)
    if path is None:
        abort(404)
    response=send_file(path,mimetype="image/png",conditional=True,max_age=0)
    response.headers["Cache-Control"]="no-store"
    return response
