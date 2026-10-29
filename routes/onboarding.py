"""Choose Buyer/Seller after registration, then complete the matching profile."""

from flask import Blueprint, current_app, flash, g, redirect, render_template, request, url_for
from mysql.connector import Error
from routes.auth import login_required
from services.profiles import (
    ProfileAccessError, choose_account_type, completed_profile_kind,
    get_buyer_profile, get_seller_profile, save_buyer_profile, save_seller_profile,
)
from services.profile_validation import (
    ADDRESS_FIELDS, BUYER_FIELDS, SELLER_FIELDS, MEASUREMENTS,
    validate_buyer_profile, validate_seller_profile,
)


onboarding_bp = Blueprint("onboarding", __name__)


def _unavailable():
    current_app.logger.warning("Profile storage is unavailable. Run sql/02_buyer_seller_profiles.sql in the local database.")
    return render_template("auth/message.html", title="Please try again shortly",
                           message="We couldn't load your profile right now. Please try again in a moment."), 503


def _forbidden():
    return render_template("auth/message.html", title="Use your account's profile",
                           message="This profile belongs to a different account type. Return to My Account to continue."), 403


@onboarding_bp.route("/onboarding/role", methods=["GET", "POST"])
@login_required
def choose_role():
    if g.user["role"] not in {"pending", "customer", "seller"}:
        return _forbidden()
    errors = {}
    status = 200
    try:
        if completed_profile_kind(g.user["user_id"]) is not None:
            return redirect(url_for("auth.account"))
        if request.method == "POST":
            account_type = request.form.get("account_type", "")
            if account_type not in {"buyer", "seller"}:
                errors["account_type"] = "Choose Buyer or Seller to continue."
                status = 400
            else:
                try:
                    choose_account_type(g.user["user_id"], account_type)
                except ProfileAccessError:
                    return redirect(url_for("auth.account"))
                return redirect(url_for("onboarding." + account_type + "_profile"))
    except Error:
        return _unavailable()
    return render_template("onboarding/choose_role.html", errors=errors), status


def _initial_values(profile, fields):
    values = {name: "" for name in fields}
    if profile:
        for name in values:
            values[name] = profile.get(name) if profile.get(name) is not None else ""
    return values


@onboarding_bp.route("/profile/buyer", methods=["GET", "POST"])
@login_required
def buyer_profile():
    if g.user["role"] != "customer":
        return _forbidden()
    try:
        profile = get_buyer_profile(g.user["user_id"])
        values = _initial_values(profile, [*BUYER_FIELDS, *ADDRESS_FIELDS, *MEASUREMENTS, "measurement_unit"])
        values["measurement_unit"] = values["measurement_unit"] or "in"
        errors = {}
        status = 200
        if request.method == "POST":
            values, errors = validate_buyer_profile(request.form)
            if not errors:
                try:
                    save_buyer_profile(g.user["user_id"], values)
                except ProfileAccessError:
                    return _forbidden()
                flash("Your buyer profile has been updated." if profile else "Your buyer profile is ready.", "success")
                return redirect(url_for("auth.account"))
            status = 400
    except Error:
        return _unavailable()
    return render_template("onboarding/buyer_profile.html", values=values, errors=errors,
                           completed=profile is not None), status


@onboarding_bp.route("/profile/seller", methods=["GET", "POST"])
@login_required
def seller_profile():
    if g.user["role"] != "seller":
        return _forbidden()
    try:
        profile = get_seller_profile(g.user["user_id"])
        values = _initial_values(profile, [*SELLER_FIELDS, *ADDRESS_FIELDS])
        errors = {}
        status = 200
        if request.method == "POST":
            values, errors = validate_seller_profile(request.form)
            if not errors:
                try:
                    save_seller_profile(g.user["user_id"], values)
                except ProfileAccessError:
                    return _forbidden()
                flash("Your seller profile has been updated." if profile else "Your seller profile is ready.", "success")
                return redirect(url_for("auth.account"))
            status = 400
    except Error:
        return _unavailable()
    return render_template("onboarding/seller_profile.html", values=values, errors=errors,
                           completed=profile is not None), status
