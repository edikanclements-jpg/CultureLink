
from flask import Flask
from config import Config

from routes.main import main_bp
from routes.products import products_bp
from routes.boutiques import boutiques_bp


def create_app():
    """
    Create and configure the CultureLink application.
    """

    app = Flask(__name__)

    # Load application configuration
    app.config.from_object(Config)

    # Register application routes
    app.register_blueprint(main_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(boutiques_bp)

    return app


app = create_app()


if __name__ == "__main__":
    from getpass import getpass

    app.config["DB_PASSWORD"] = getpass("MySQL password: ")
    app.run(debug=True, use_reloader=False)