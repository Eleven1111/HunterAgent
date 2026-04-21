from __future__ import annotations

import base64
import hashlib
from typing import Iterable


def normalize_identity(full_name: str, email: str | None, phone: str | None) -> str:
    email_domain = email.split("@", 1)[1].lower() if email and "@" in email else ""
    phone_last4 = "".join(ch for ch in (phone or "") if ch.isdigit())[-4:]
    raw = f"{full_name.strip().lower()}|{email_domain}|{phone_last4}"
    return hashlib.sha256(raw.encode()).hexdigest()


def has_strong_identity(email: str | None, phone: str | None) -> bool:
    if email and "@" in email:
        return True
    digits = "".join(ch for ch in (phone or "") if ch.isdigit())
    return len(digits) >= 7


def seal_text(value: str | None) -> str | None:
    if value is None:
        return None
    return base64.urlsafe_b64encode(value.encode()).decode()


def reveal_text(value: str | None) -> str | None:
    if value is None:
        return None
    return base64.urlsafe_b64decode(value.encode()).decode()


def mask_email(value: str | None) -> str | None:
    email = reveal_text(value)
    if not email or "@" not in email:
        return None
    name, domain = email.split("@", 1)
    if len(name) <= 2:
        return f"{name[0]}*@{domain}"
    return f"{name[:2]}***@{domain}"


def mask_phone(value: str | None) -> str | None:
    phone = reveal_text(value)
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    if len(digits) < 4:
        return "***"
    return f"***{digits[-4:]}"


def summarize_resume(text: str, max_words: int = 36) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).strip() + "..."


def lower_join(values: Iterable[str]) -> str:
    return " ".join(value.lower() for value in values if value)
