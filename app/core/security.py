"""Authentication helpers — password hashing, session token management."""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from typing import Optional

import bcrypt

from app.core.config import get_settings


# ─── Password hashing ──────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


# ─── Simple signed session token ──────────────────────────────────────────
# For the hackathon we use a simple HMAC-signed token stored in st.session_state.
# In production, prefer provider-supported sessions (Supabase Auth JWT).

_SEP = "."


def _sign(payload: str, secret: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), digestmod=hashlib.sha256).hexdigest()


def create_session_token(user_id: str, expires_in: int = 86_400 * 7) -> str:
    """Return a signed token: user_id.expiry.signature"""
    settings = get_settings()
    expiry = int(time.time()) + expires_in
    payload = f"{user_id}{_SEP}{expiry}"
    sig = _sign(payload, settings.app_secret_key)
    return f"{payload}{_SEP}{sig}"


def verify_session_token(token: str) -> Optional[str]:
    """Return user_id if token is valid and unexpired, else None."""
    settings = get_settings()
    try:
        parts = token.rsplit(_SEP, 1)
        if len(parts) != 2:
            return None
        payload, sig = parts
        expected = _sign(payload, settings.app_secret_key)
        if not hmac.compare_digest(sig, expected):
            return None
        user_id, expiry_str = payload.rsplit(_SEP, 1)
        if int(time.time()) > int(expiry_str):
            return None
        return user_id
    except Exception:
        return None
