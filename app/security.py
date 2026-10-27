from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from .config import TOKEN_SECRET, TOKEN_TTL_SECONDS


class TokenError(ValueError):
    """Raised when a demo access token is malformed, invalid or expired."""


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
        dklen=32,
    )
    return f"scrypt${_b64encode(salt)}${_b64encode(derived)}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, salt_text, digest_text = encoded.split("$", 2)
        if algorithm != "scrypt":
            return False
        salt = _b64decode(salt_text)
        expected = _b64decode(digest_text)
        actual = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1,
            dklen=32,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


def create_access_token(
    user_id: int,
    username: str,
    role: str,
    ttl_seconds: int | None = None,
) -> tuple[str, int]:
    ttl = ttl_seconds or TOKEN_TTL_SECONDS
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iat": now,
        "exp": now + ttl,
        "iss": "fastapi-test-lab",
    }
    header_part = _b64encode(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )
    payload_part = _b64encode(
        json.dumps(payload, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{header_part}.{payload_part}".encode("ascii")
    signature = hmac.new(
        TOKEN_SECRET.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    return f"{header_part}.{payload_part}.{_b64encode(signature)}", ttl


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        header_part, payload_part, signature_part = token.split(".")
        signing_input = f"{header_part}.{payload_part}".encode("ascii")
        expected = hmac.new(
            TOKEN_SECRET.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        actual = _b64decode(signature_part)
        if not hmac.compare_digest(actual, expected):
            raise TokenError("Token signature is invalid")

        header = json.loads(_b64decode(header_part))
        payload = json.loads(_b64decode(payload_part))
        if header.get("alg") != "HS256":
            raise TokenError("Unsupported token algorithm")
        if int(payload.get("exp", 0)) <= int(time.time()):
            raise TokenError("Token has expired")
        if not payload.get("sub"):
            raise TokenError("Token subject is missing")
        return payload
    except TokenError:
        raise
    except (ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        raise TokenError("Malformed access token") from exc

