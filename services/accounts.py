"""Parameterized queries for the existing CultureLink users table."""

from mysql.connector import errorcode

from database import get_db_connection


MYSQL_LOGIN_ERRORS = {
    errorcode.ER_ACCESS_DENIED_ERROR,
    errorcode.ER_ACCESS_DENIED_NO_PASSWORD_ERROR,
}
_DATABASE_HINTS = {
    **dict.fromkeys(MYSQL_LOGIN_ERRORS, "Check the MySQL username and password."),
    errorcode.ER_BAD_DB_ERROR: "Check that DB_NAME in config.py points to the existing CultureLink database.",
    **dict.fromkeys(
        (errorcode.ER_DBACCESS_DENIED_ERROR, errorcode.ER_TABLEACCESS_DENIED_ERROR,
         errorcode.ER_COLUMNACCESS_DENIED_ERROR),
        "Check that the configured MySQL user can access the CultureLink database and its tables.",
    ),
    **dict.fromkeys(
        (errorcode.ER_NO_SUCH_TABLE, errorcode.ER_BAD_FIELD_ERROR),
        "Open the existing CultureLink schema in MySQL Workbench and check its tables and columns.",
    ),
    **dict.fromkeys(
        (errorcode.CR_CONNECTION_ERROR, errorcode.CR_CONN_HOST_ERROR, errorcode.CR_UNKNOWN_HOST,
         errorcode.CR_SERVER_GONE_ERROR, errorcode.CR_SERVER_LOST, errorcode.CR_SERVER_LOST_EXTENDED),
        "Check that the MySQL server is running and test the same host and port in MySQL Workbench.",
    ),
}


def log_database_problem(logger, operation, error):
    """Log actionable diagnostics without printing credentials or SQL."""
    hint = _DATABASE_HINTS.get(error.errno, "Test the CultureLink connection in MySQL Workbench.")
    logger.warning("CultureLink database problem during %s (MySQL %s). %s",
                   operation, error.errno, hint)


def _find_user(column, value, include_password=False):
    # Column names are selected here, never supplied by a website visitor.
    if column not in {"email", "user_id"}:
        raise ValueError("Unsupported account lookup")
    fields = "user_id, email, role, created_at"
    if include_password:
        fields += ", password_hash"
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute(
            f"SELECT {fields} FROM users WHERE {column} = %s LIMIT 1", (value,)
        )
        return cursor.fetchone()
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def find_user_by_email(email):
    return _find_user("email", email, include_password=True)


def find_user_by_id(user_id):
    return _find_user("user_id", user_id)


def create_account(email, password_hash):
    connection = get_db_connection()
    cursor = None
    try:
        cursor = connection.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash, role) VALUES (%s, %s, %s)",
            (email, password_hash, "pending"),
        )
        user_id = cursor.lastrowid
        connection.commit()
        return user_id
    except Exception:
        connection.rollback()
        raise
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
