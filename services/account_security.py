"""Local session keys, form tokens, and bounded login attempt tracking."""

from collections import OrderedDict, deque
from datetime import timedelta
import math
import os
from pathlib import Path
import secrets
from threading import Lock
import time

from flask import session
from werkzeug.security import generate_password_hash


class AttemptLimiter:
    """Small per-process limiter for this local demonstration application."""

    def __init__(self):
        self._attempts = OrderedDict()
        self._lock = Lock()

    def consume(self, key, limit, window=900):
        now = time.monotonic()
        with self._lock:
            attempts = self._attempts.pop(key, deque())
            while attempts and attempts[0] <= now - window:
                attempts.popleft()
            self._attempts[key] = attempts
            while len(self._attempts) > 2048:
                self._attempts.popitem(last=False)
            if len(attempts) >= limit:
                return max(1, math.ceil(window - (now - attempts[0])))
            attempts.append(now)
        return 0

    def reset(self, key):
        with self._lock:
            self._attempts.pop(key, None)


def _local_session_key(app):
    directory = Path(app.instance_path)
    directory.mkdir(parents=True, exist_ok=True)
    key_file = directory / "session.key"
    try:
        descriptor = os.open(str(key_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        value = key_file.read_text(encoding="ascii").strip()
        if len(value) < 64:
            raise RuntimeError("The local session key is incomplete. Remove instance/session.key and restart the app.")
        return value
    value = secrets.token_hex(32)
    with os.fdopen(descriptor, "w", encoding="ascii") as output:
        output.write(value + "\n")
    return value


def configure_account_security(app):
    key = app.config.get("SECRET_KEY")
    if not key or key in {"local-development-only", "dev", "change-me"}:
        app.config["SECRET_KEY"] = _local_session_key(app)
    app.config.update(
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        PERMANENT_SESSION_LIFETIME=timedelta(hours=12),
    )
    # Local HTTP needs Secure=False. Enable SESSION_COOKIE_SECURE for future HTTPS hosting.
    if app.config.get("MAX_CONTENT_LENGTH") is None:
        app.config["MAX_CONTENT_LENGTH"] = 128 * 1024
    app.extensions["account_attempts"] = AttemptLimiter()
    app.extensions["account_dummy_hash"] = generate_password_hash(
        secrets.token_urlsafe(32), method="scrypt:32768:8:1"
    )


def csrf_token():
    if "_csrf_token" not in session:
        session["_csrf_token"] = secrets.token_urlsafe(32)
    return session["_csrf_token"]
