from getpass import getpass

from flask import Flask
from mysql.connector import Error
from config import Config

from routes.main import main_bp
from routes.products import products_bp
from routes.boutiques import boutiques_bp
from routes.auth import auth_bp
from routes.onboarding import onboarding_bp
from routes.closet import closet_bp
from services.account_security import configure_account_security
from services.accounts import MYSQL_LOGIN_ERRORS, find_user_by_id, log_database_problem
from services.indian_menswear import ASSET_ROOT, IMAGE_URLS, ITEMS
from services.products import get_all_products


def create_app(test_config=None):
    """
    Create and configure the CultureLink application.
    """

    app = Flask(__name__)

    # Load application configuration
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
    configure_account_security(app)

    # Register application routes
    app.register_blueprint(main_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(boutiques_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(onboarding_bp)
    app.register_blueprint(closet_bp)

    return app


app = create_app()


def _check_accounts_database(app):
    try:
        with app.app_context():
            # Verify the same read used by saved logins without loading a real account.
            find_user_by_id(0)
    except Error as error:
        return error
    return None


def _prepare_database(app):
    if not app.config.get("DB_PASSWORD"):
        app.config["DB_PASSWORD"] = getpass("MySQL password: ")
    error = _check_accounts_database(app)
    if error is not None and error.errno in MYSQL_LOGIN_ERRORS:
        print("MySQL rejected the login. Enter your MySQL password to try again.")
        app.config["DB_PASSWORD"] = getpass("MySQL password (retry): ")
        error = _check_accounts_database(app)
    if error is not None:
        log_database_problem(app.logger, "startup check", error)
        return False
    print("CultureLink database check passed.")
    return True


def _report_menswear(app):
    try:
        with app.app_context():
            catalog = get_all_products()
    except Error as error:
        log_database_problem(app.logger, "public catalog check", error)
        return
    visible = IMAGE_URLS.intersection(piece.get("image_url") for piece in catalog)
    print(f"Indian menswear check found {len(visible)} of {len(IMAGE_URLS)} public listings.", flush=True)
    if visible != IMAGE_URLS:
        missing = [item["name"] for item in ITEMS if "/" + ASSET_ROOT + item["asset"] not in visible]
        app.logger.warning("Indian menswear missing from the public catalog. %s", ", ".join(missing))


if __name__ == "__main__":
    if _prepare_database(app):
        _report_menswear(app)
    app.run(debug=True, use_reloader=False)
