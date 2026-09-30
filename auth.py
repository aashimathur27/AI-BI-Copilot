"""
auth.py
-------
Simple username/password authentication for the Streamlit app.

Notes on the approach
----------------------
Streamlit apps run as a single Python process per user session, so a
traditional JWT-in-header flow isn't really necessary for the MVP - we
authenticate once and keep the logged-in user in `st.session_state`.
Passwords are stored as salted SHA-256 hashes (swap in bcrypt/argon2 for
production use). A JWT helper (`create_jwt` / `decode_jwt`) is included
too, ready to use if you expose a separate FastAPI backend later.
"""

import hashlib
import os
import re
import secrets
import time
import base64
import hmac
import json

import database as db

JWT_SECRET = os.environ.get("APP_JWT_SECRET")


# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

def _hash(value: str, salt: str) -> str:
    return hashlib.sha256((salt + value).encode("utf-8")).hexdigest()


def hash_password(password: str, salt: str | None = None):
    salt = salt or secrets.token_hex(16)
    return _hash(password, salt), salt


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    return hmac.compare_digest(_hash(password, salt), expected_hash)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ""))


def is_valid_password(password: str) -> tuple[bool, str]:
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters."
    return True, ""


# ---------------------------------------------------------------------------
# Signup / Login / Forgot password
# ---------------------------------------------------------------------------

def signup(username, email, password, security_question, security_answer):
    if not username or not email or not password:
        return False, "All fields are required."
    if not is_valid_email(email):
        return False, "Please enter a valid email address."
    ok, msg = is_valid_password(password)
    if not ok:
        return False, msg
    if db.get_user_by_username(username):
        return False, "That username is already taken."
    if db.get_user_by_email(email):
        return False, "An account with that email already exists."

    pwd_hash, salt = hash_password(password)
    ans_hash, _ = hash_password(security_answer.strip().lower(), salt)

    db.create_user(username, email, pwd_hash, salt, security_question, ans_hash)
    return True, "Account created! You can now log in."


def login(username, password):
    user = db.get_user_by_username(username)
    if not user:
        return False, "No account found with that username.", None
    if not verify_password(password, user["salt"], user["password_hash"]):
        return False, "Incorrect password.", None
    return True, "Login successful.", user


def reset_password(username, security_answer, new_password):
    user = db.get_user_by_username(username)
    if not user:
        return False, "No account found with that username."
    ans_hash = _hash(security_answer.strip().lower(), user["salt"])
    if not hmac.compare_digest(ans_hash, user["security_answer_hash"]):
        return False, "Security answer is incorrect."
    ok, msg = is_valid_password(new_password)
    if not ok:
        return False, msg
    new_hash, new_salt = hash_password(new_password)
    db.update_password(user["id"], new_hash, new_salt)
    return True, "Password reset successfully. Please log in."


# ---------------------------------------------------------------------------
# Optional JWT helpers (for a future FastAPI backend)
# ---------------------------------------------------------------------------

def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _require_jwt_secret() -> str:
    if not JWT_SECRET:
        raise RuntimeError(
            "APP_JWT_SECRET environment variable is not set. These JWT helpers are "
            "unused by the Streamlit app itself (auth here runs via session state) — "
            "they're provided for a future FastAPI backend. Set APP_JWT_SECRET before "
            "using create_jwt/decode_jwt."
        )
    return JWT_SECRET


def create_jwt(payload: dict, expires_in: int = 3600) -> str:
    secret = _require_jwt_secret()
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {**payload, "exp": int(time.time()) + expires_in}
    segments = [
        _b64url(json.dumps(header).encode()),
        _b64url(json.dumps(payload).encode()),
    ]
    signing_input = ".".join(segments).encode()
    signature = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
    segments.append(_b64url(signature))
    return ".".join(segments)


def decode_jwt(token: str):
    secret = _require_jwt_secret()
    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        signing_input = f"{header_b64}.{payload_b64}".encode()
        expected_sig = hmac.new(secret.encode(), signing_input, hashlib.sha256).digest()
        if not hmac.compare_digest(_b64url(expected_sig), sig_b64):
            return None
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        if payload.get("exp", 0) < time.time():
            return None
        return payload
    except Exception:
        return None
