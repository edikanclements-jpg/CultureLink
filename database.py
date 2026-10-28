
import mysql.connector
from flask import current_app

def get_db_connection():
    """Connect to the CultureLink MySQL database."""

    config = current_app.config

    return mysql.connector.connect(
        host=config["DB_HOST"],
        port=config["DB_PORT"],
        user=config["DB_USER"],
        password=config["DB_PASSWORD"],
        database=config["DB_NAME"]
    )
