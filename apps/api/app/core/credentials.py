from __future__ import annotations

import hashlib
import hmac
import secrets


PBKDF2_PREFIX = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 390_000


def hash_password(password: str, *, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return f"{PBKDF2_PREFIX}${iterations}${salt}${digest}"


def needs_password_upgrade(stored_value: str | None) -> bool:
    return not stored_value or not stored_value.startswith(f"{PBKDF2_PREFIX}$")


def verify_password(password: str, stored_value: str | None) -> bool:
    if not stored_value:
        return False
    if needs_password_upgrade(stored_value):
        return hmac.compare_digest(password, stored_value)
    try:
        _, iteration_text, salt, expected = stored_value.split("$", 3)
        iterations = int(iteration_text)
    except (TypeError, ValueError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), iterations).hex()
    return hmac.compare_digest(actual, expected)
