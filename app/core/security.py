import hmac
import secrets
import time
import uuid
from hashlib import sha256
from typing import Any

import jwt

from app.core.config import get_settings


JWT_ISSUER = "grantpilot"
JWT_AUDIENCE = "grantpilot-web"


def generate_opaque_token(length: int = 48) -> str:
    return secrets.token_urlsafe(length)


def hash_token(token: str) -> str:
    key = get_settings().AUTH_JWT_SIGNING_KEY.encode("utf-8")
    digest = hmac.new(key, token.encode("utf-8"), sha256).hexdigest()
    return digest


def create_access_token(user_id: str, email: str, plan: str) -> tuple[str, int]:
    settings = get_settings()
    now = int(time.time())
    ttl_seconds = settings.AUTH_ACCESS_TOKEN_TTL_MIN * 60
    payload: dict[str, Any] = {
        "iss": JWT_ISSUER,
        "aud": JWT_AUDIENCE,
        "sub": user_id,
        "email": email,
        "plan": plan,
        "iat": now,
        "nbf": now,
        "exp": now + ttl_seconds,
        "jti": str(uuid.uuid4()),
    }
    token = jwt.encode(payload, settings.AUTH_JWT_SIGNING_KEY, algorithm="HS256")
    return token, ttl_seconds
