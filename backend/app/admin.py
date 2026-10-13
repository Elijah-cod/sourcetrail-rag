"""The admin password and sign-in sessions. One administrator, no usernames.

The password is checked against a scrypt hash (ADMIN_PASSWORD_HASH) in constant time. A correct
password starts a session: a random token in an HttpOnly cookie, signed with ADMIN_SESSION_SECRET,
whose SHA-256 is stored with its expiry. Every admin request checks the signature, then the stored
session, so a session ends when it expires, on logout, or for everyone when the secret changes.

    python -m app.admin hash-password    # prints a hash for ADMIN_PASSWORD_HASH (asks for the password)
    python -m app.admin new-secret       # prints a random ADMIN_SESSION_SECRET
"""

import base64
import hashlib
import hmac
import logging
import secrets
import sys
from datetime import datetime, timedelta, timezone
from functools import lru_cache

import psycopg

from app.config import get_settings
from app.monitoring import log_event

log = logging.getLogger("sourcetrail.admin")

COOKIE_NAME = "st_admin"
# scrypt cost: ~50 ms and 16 MB per check, enough to slow guessing without hurting a 1 vCPU server.
_N, _R, _P = 2**14, 8, 1


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return "$".join(["scrypt", str(_N), str(_R), str(_P), _b64(salt), _b64(digest)])


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        actual = hashlib.scrypt(password.encode(), salt=_unb64(salt), n=int(n), r=int(r), p=int(p),
                                dklen=len(_unb64(digest)))
    except (ValueError, TypeError):
        return False                       # a malformed hash never lets anyone in
    return hmac.compare_digest(actual, _unb64(digest))


@lru_cache
def configured_hash() -> str | None:
    """The password hash to check against, or None when the admin area isn't set up (closed)."""
    settings = get_settings()
    if not settings.admin_session_secret:
        log.error("admin area closed: ADMIN_SESSION_SECRET is not set")
        return None
    if settings.admin_password_hash:
        return settings.admin_password_hash
    if settings.admin_password:
        log.warning("ADMIN_PASSWORD is set in plain text; set ADMIN_PASSWORD_HASH instead (see README)")
        return hash_password(settings.admin_password)
    log.error("admin area closed: neither ADMIN_PASSWORD_HASH nor ADMIN_PASSWORD is set")
    return None


# ---------- sessions ----------

def _sign(token: str) -> str:
    key = get_settings().admin_session_secret.encode()
    return _b64(hmac.new(key, token.encode(), hashlib.sha256).digest())


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(conn: psycopg.Connection) -> tuple[str, datetime]:
    """Store a new session; returns (cookie value, expiry)."""
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=get_settings().admin_session_hours)
    conn.execute("INSERT INTO admin_sessions (token_hash, expires_at) VALUES (%s, %s)",
                 (_token_hash(token), expires))
    return f"{token}.{_sign(token)}", expires


def _token(cookie: str | None) -> str | None:
    """The token inside a cookie whose signature is right, else None (tampered or old secret)."""
    if not cookie or "." not in cookie or not get_settings().admin_session_secret:
        return None
    token, signature = cookie.rsplit(".", 1)
    return token if hmac.compare_digest(signature, _sign(token)) else None


def session_status(conn: psycopg.Connection, cookie: str | None) -> tuple[str, datetime | None]:
    """("valid", expiry), ("expired", None) or ("none", None)."""
    token = _token(cookie)
    if token is None:
        return "none", None
    row = conn.execute("SELECT expires_at, revoked_at FROM admin_sessions WHERE token_hash = %s",
                       (_token_hash(token),)).fetchone()
    if row is None or row[1] is not None:
        return "none", None
    if row[0] <= datetime.now(timezone.utc):
        return "expired", None
    return "valid", row[0]


def end_session(conn: psycopg.Connection, cookie: str | None) -> None:
    token = _token(cookie)
    if token:
        conn.execute("UPDATE admin_sessions SET revoked_at = now() WHERE token_hash = %s AND revoked_at IS NULL",
                     (_token_hash(token),))


def record(conn: psycopg.Connection, kind: str, subject: str | None = None) -> None:
    """Sign-in history: login, login_failed, logout, expired. Never a password."""
    conn.execute("INSERT INTO admin_events (kind, subject) VALUES (%s, %s)", (kind, subject))
    log_event("admin", kind=kind)          # Cloud Logging: jsonPayload.event="admin" (see README)


def recent_failures(conn: psycopg.Connection, subject: str, minutes: int = 15) -> int:
    return conn.execute(
        "SELECT count(*) FROM admin_events WHERE kind = 'login_failed' AND subject = %s "
        "AND created_at > now() - make_interval(mins => %s)", (subject, minutes)).fetchone()[0]


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def main(argv: list[str]) -> None:
    command = argv[1] if len(argv) > 1 else ""
    if command == "hash-password":
        from getpass import getpass
        password = getpass("Admin password: ")
        if len(password) < 12:
            sys.exit("Use at least 12 characters.")
        if getpass("Again: ") != password:
            sys.exit("The two passwords differ.")
        print(hash_password(password))
    elif command == "new-secret":
        print(secrets.token_urlsafe(48))
    else:
        sys.exit("usage: python -m app.admin hash-password | new-secret")


if __name__ == "__main__":
    main(sys.argv)
