"""Boundary validation. Identifier patterns follow the canonical synthetic case.

Every check raises ValidationError with the field name only. A rejected value is
never echoed back, because it may be hostile or may belong to someone else.
"""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Pattern

from .errors import ValidationError

CASE_ID: Pattern[str] = re.compile(r"SYN-CASE-[0-9]{4}")
ACCOUNT_ID: Pattern[str] = re.compile(r"SYN-ACCT-[0-9]{4}")
METER_ID: Pattern[str] = re.compile(r"SYN-MTR-[0-9]{4}")
BILL_ID: Pattern[str] = re.compile(r"SYN-BILL-[0-9]{4}-[0-9]{2}")
READ_ID: Pattern[str] = re.compile(r"SYN-READ-[0-9]{4}-[A-Z]")
DIAGNOSTIC_ID: Pattern[str] = re.compile(r"SYN-DIAG-[0-9]{4}-[0-9]{2}")
EVENT_ID: Pattern[str] = re.compile(r"SYN-EVT-[0-9]{4}-[0-9]{2}")
REQUEST_ID: Pattern[str] = re.compile(r"ADJ-[0-9]{4}")
ISO_DATE: Pattern[str] = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
ISO_MONTH: Pattern[str] = re.compile(r"[0-9]{4}-[0-9]{2}")
PRINCIPAL_ID: Pattern[str] = re.compile(r"[a-z][a-z0-9-]{2,63}")
IDEMPOTENCY_KEY: Pattern[str] = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{7,63}")
AUDIT_ACTION: Pattern[str] = re.compile(r"[A-Z][A-Z0-9_]{0,63}")

MAX_TEXT_LENGTH = 4000
MAX_DETAIL_LENGTH = 500
SYNTHETIC_CLASSIFICATION = "SYNTHETIC_ONLY"


def require_pattern(field_name: str, value: object, pattern: Pattern[str]) -> str:
    """Return `value` if it is a string that fully matches `pattern`."""
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValidationError("%s does not match the required pattern." % field_name)
    return value


def require_case_id(value: object) -> str:
    return require_pattern("case_id", value, CASE_ID)


def require_account_id(value: object) -> str:
    return require_pattern("account_id", value, ACCOUNT_ID)


def require_idempotency_key(value: object) -> str:
    return require_pattern("idempotency_key", value, IDEMPOTENCY_KEY)


def require_text(field_name: str, value: object, max_length: int = MAX_TEXT_LENGTH) -> str:
    """Return `value` if it is a non-blank string within `max_length`."""
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise ValidationError("%s must be non-empty text within the length limit." % field_name)
    return value


def require_int(field_name: str, value: object, minimum: int = 0) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValidationError("%s must be a whole number of at least %d." % (field_name, minimum))
    return value


def require_bool(field_name: str, value: object) -> bool:
    if not isinstance(value, bool):
        raise ValidationError("%s must be true or false." % field_name)
    return value


def require_money(field_name: str, value: object) -> Decimal:
    """Return `value` if it is a finite, non-negative Decimal."""
    if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
        raise ValidationError("%s must be a non-negative decimal amount." % field_name)
    return value


def to_money(field_name: str, value: object) -> Decimal:
    """Convert a JSON number to an exact Decimal through its shortest text form."""
    if isinstance(value, bool) or not isinstance(value, (int, float, str, Decimal)):
        raise ValidationError("%s must be a number." % field_name)
    try:
        return require_money(field_name, Decimal(str(value)))
    except InvalidOperation as exc:
        raise ValidationError("%s must be a number." % field_name) from exc
