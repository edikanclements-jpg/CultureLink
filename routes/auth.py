"""Registration, login, account summary, and POST-only logout."""

from functools import wraps
import hmac
import re

from flask import (
    Blueprint, abort, current_app, flash, g, redirect, render_template, request,
    send_file, session, url_for,
)
from mysql.connector import Error, IntegrityError, errorcode
from werkzeug.security import check_password_hash, generate_password_hash

from services.accounts import create_account, find_user_by_email, find_user_by_id
from services.account_security import csrf_token
from services.profiles import completed_profile_kind, get_buyer_profile, get_seller_profile
from services.profile_images import account_images, image_path, initials


auth_bp = Blueprint("auth", __name__)
EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?)+"
)
MIN_PASSWORD = 12
MAX_PASSWORD = 128


def _email_is_valid(email):
    if not email or len(email) > 150 or not EMAIL_PATTERN.fullmatch(email):
        return False
    local, domain = email.rsplit("@", 1)
    return (
        not local.startswith(".") and not local.endswith(".")
        and ".." not in local and len(local) <= 64
        and all(len(label) <= 63 for label in domain.split("."))
    )


def _message(title, message, status):
    return render_template("auth/message.html", title=title, message=message), status


@auth_bp.app_context_processor
def account_template_helpers():
    pictures = {}
    if getattr(g, "user", None):
        try:
            pictures = account_images(g.user["user_id"], g.user["role"])
        except (OSError, ValueError):
            current_app.logger.warning("Could not load account pictures.")
    return {"csrf_token": csrf_token, "account_photos": pictures, "picture_initials": initials}


@auth_bp.before_app_request
def load_signed_in_user():
    g.user = None
    if request.endpoint == "static":
        return None
    user_id = session.get("user_id")
    if user_id is None:
        return None
    if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id <= 0:
        session.clear()
        return None
    try:
        g.user = find_user_by_id(user_id)
    except Error:
        current_app.logger.warning("Could not load the signed-in CultureLink account.")
        return _message(
            "Please try again shortly",
            "We couldn't reach your account right now. Please refresh the page in a moment.",
            503,
        )
    if g.user is None:
        session.clear()
    return None


@auth_bp.before_app_request
def protect_account_forms():
    if request.method != "POST":
        return None
    picture_form = (request.endpoint in {"onboarding.buyer_profile", "onboarding.seller_profile", "onboarding.seller.item_new", "onboarding.seller.item_edit"}
                    and request.mimetype == "multipart/form-data")
    limit = 11 * 1024 * 1024 if picture_form else 128 * 1024
    if request.content_length is not None and request.content_length > limit:
        return _message("This upload is too large", "Choose pictures under 5 MB each, then return to your profile and try again.", 413)
    expected = session.get("_csrf_token")
    submitted = request.form.get("csrf_token", "")
    if (
        not isinstance(expected, str) or not expected
        or not submitted.isascii()
        or not hmac.compare_digest(expected, submitted)
    ):
        return _message(
            "Let's try that again",
            "This form has expired. Return to the form, refresh the page, and try again.",
            400,
        )
    return None


@auth_bp.after_app_request
def protect_account_responses(response):
    if (request.endpoint or "").startswith("auth.") or getattr(g, "user", None):
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    return response


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Log in to view your account.", "info")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


def _attempt_limit(kind, email=""):
    limiter = current_app.extensions["account_attempts"]
    ip = request.remote_addr or "local"
    if kind == "register":
        return limiter.consume((kind, ip), limit=10)
    retry = limiter.consume(("login-ip", ip), limit=40)
    if retry:
        return retry
    return limiter.consume(("login-email", ip, email), limit=8)


def _throttled(retry):
    html, status = _message(
        "Take a short pause",
        "There have been several attempts. Please try again in 15 minutes.",
        429,
    )
    return html, status, {"Retry-After": str(retry)}


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user is not None:
        return redirect(url_for("auth.account"))
    errors = {}
    email = ""
    status = 200
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        retry = _attempt_limit("register")
        if retry:
            return _throttled(retry)
        password = request.form.get("password", "")
        confirmation = request.form.get("confirm_password", "")
        if not _email_is_valid(email):
            errors["email"] = "Enter a valid email address of 150 characters or fewer."
        if not MIN_PASSWORD <= len(password) <= MAX_PASSWORD:
            errors["password"] = "Use a password between 12 and 128 characters."
        elif password != confirmation:
            errors["confirm_password"] = "Your passwords don't match."
        if not errors:
            try:
                password_hash = generate_password_hash(password, method="scrypt:32768:8:1")
                user_id = create_account(email, password_hash)
            except IntegrityError as error:
                if error.errno == errorcode.ER_DUP_ENTRY:
                    errors["email"] = "An account already uses this email. Please log in instead."
                else:
                    current_app.logger.warning("Could not create a CultureLink account.")
                    errors["form"] = "We couldn't create your account right now. Please try again."
                    status = 503
            except Error:
                current_app.logger.warning("Could not connect to the CultureLink accounts database.")
                errors["form"] = "We couldn't create your account right now. Please try again."
                status = 503
            else:
                session.clear()
                session["user_id"] = int(user_id)
                session.permanent = True
                return redirect(url_for("onboarding.choose_role"))
        if errors and status == 200:
            status = 400
    return render_template("auth/register.html", email=email, errors=errors), status


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for("auth.account"))
    errors = {}
    email = ""
    status = 200
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        retry = _attempt_limit("login", email)
        if retry:
            return _throttled(retry)
        password = request.form.get("password", "")
        if not _email_is_valid(email) or not password or len(password) > MAX_PASSWORD:
            errors["form"] = "The email or password isn't correct. Please try again."
        else:
            try:
                user = find_user_by_email(email)
            except Error:
                current_app.logger.warning("Could not look up a CultureLink account.")
                errors["form"] = "We couldn't log you in right now. Please try again."
                status = 503
            else:
                stored_hash = (user or {}).get("password_hash") or current_app.extensions["account_dummy_hash"]
                try:
                    correct = check_password_hash(stored_hash, password)
                except (ValueError, TypeError):
                    correct = False
                if user is None or not correct:
                    errors["form"] = "The email or password isn't correct. Please try again."
                else:
                    session.clear()
                    session["user_id"] = int(user["user_id"])
                    session.permanent = True
                    current_app.extensions["account_attempts"].reset(
                        ("login-email", request.remote_addr or "local", email)
                    )
                    flash("You're logged in.", "success")
                    return redirect(url_for("auth.account"))
        if errors and status == 200:
            status = 400
    return render_template("auth/login.html", email=email, errors=errors), status


@auth_bp.route("/account")
@login_required
def account():
    if g.user["role"] == "admin":
        return redirect(url_for("onboarding.seller.review_queue"))
    profile = None
    account_type = None
    if g.user["role"] in {"pending", "customer", "seller"}:
        try:
            account_type = completed_profile_kind(g.user["user_id"])
            if account_type is None:
                return redirect(url_for("onboarding.choose_role"))
            profile = (get_buyer_profile if account_type == "buyer" else get_seller_profile)(g.user["user_id"])
        except Error:
            current_app.logger.warning("Could not load profile storage. Check sql/02_buyer_seller_profiles.sql has been run.")
            return _message("Please try again shortly", "We couldn't load your profile right now. Please try again in a moment.", 503)
    application = None
    if account_type == "seller":
        from services.seller_reviews import application_for
        try:
            application = application_for(g.user["user_id"])
        except Error:
            return _message("Please try again shortly", "We couldn't load your seller application. Please try again shortly.", 503)
    return render_template("auth/account.html", profile=profile, account_type=account_type,
                           application=application)


@auth_bp.route("/account/images/<kind>")
@login_required
def account_image(kind):
    allowed = {"avatar"} if g.user["role"] == "customer" else {"logo", "portrait"} if g.user["role"] == "seller" else set()
    if kind not in allowed:
        abort(404)
    try:
        path = image_path(g.user["user_id"], kind)
    except (OSError, ValueError):
        abort(404)
    if path is None:
        abort(404)
    response = send_file(path, mimetype="image/png", conditional=True, max_age=0)
    response.headers["Cache-Control"] = "private, no-store"
    return response


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You've logged out.", "success")
    return redirect(url_for("main.home"))
