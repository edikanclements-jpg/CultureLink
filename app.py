
from flask import Flask
from config import Config

from routes.main import main_bp
from routes.products import products_bp
from routes.boutiques import boutiques_bp
from routes.auth import auth_bp
from routes.onboarding import onboarding_bp
from routes.closet import closet_bp
from services.account_security import configure_account_security


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


if __name__ == "__main__":
    from getpass import getpass

    if not app.config.get("DB_PASSWORD"):
        app.config["DB_PASSWORD"] = getpass("MySQL password: ")
    app.run(debug=True, use_reloader=False)
