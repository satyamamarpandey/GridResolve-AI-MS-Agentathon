"""Deadlines, bounded retry and idempotency. Time and sleeping are injected.

The deadline is checked after the call returns, against an injected clock. It
does not interrupt a running call. A real connector would also set a transport
timeout. What this module guarantees is that a late answer is never used.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Callable, Generic, Mapping, Optional, Tuple, TypeVar

from .auth import Clock
from .errors import IdempotencyConflict, RetryNotAllowed, TimeoutExceeded, TransientError, ValidationError

T = TypeVar("T")

MAX_ATTEMPTS = 5
BACKOFF_BASE_SECONDS = 0.1
BACKOFF_FACTOR = 2.0


def with_deadline(call: Callable[[], T], clock: Clock, budget_seconds: float) -> T:
    """Run `call`. If it took longer than the budget, discard its result and raise."""
    if isinstance(budget_seconds, bool) or not isinstance(budget_seconds, (int, float)) or budget_seconds <= 0:
        raise ValidationError("budget_seconds must be a positive number.")
    started = clock.now()
    result = call()
    if clock.now() - started > budget_seconds:
        raise TimeoutExceeded(budget_seconds)
    return result


class OperationKind(Enum):
    READ = "READ"
    WRITE = "WRITE"
    AUTHORIZATION = "AUTHORIZATION"


@dataclass(frozen=True)
class Operation(Generic[T]):
    """A named call and what kind it is. Only a READ may be tried more than once."""

    name: str
    kind: OperationKind
    call: Callable[[], T]


def backoff_seconds(attempt: int) -> float:
    return BACKOFF_BASE_SECONDS * (BACKOFF_FACTOR ** (attempt - 1))


def run_with_retry(operation: Operation[T], max_attempts: int, sleeper: Callable[[float], None]) -> T:
    """Try a read up to `max_attempts` times on TransientError only.

    A write or an authorization runs at most once. Asking for more is refused
    before the call is made. Any other error, a refusal included, is not retried.
    """
    if isinstance(max_attempts, bool) or not isinstance(max_attempts, int) or not 1 <= max_attempts <= MAX_ATTEMPTS:
        raise ValidationError("max_attempts must be between 1 and %d." % MAX_ATTEMPTS)
    if operation.kind is not OperationKind.READ and max_attempts > 1:
        raise RetryNotAllowed("%s is not an idempotent read and is never retried." % operation.name)
    for attempt in range(1, max_attempts):
        try:
            return operation.call()
        except TransientError:
            sleeper(backoff_seconds(attempt))
    return operation.call()


def fingerprint_of(payload: object) -> str:
    """A stable digest of a frozen contract or a tuple of plain values."""
    return hashlib.sha256(repr(payload).encode("utf-8")).hexdigest()


def _empty_entries() -> Mapping[str, Tuple[str, object]]:
    return MappingProxyType({})


@dataclass(frozen=True)
class IdempotencyLedger(Generic[T]):
    """Immutable map of key to (payload fingerprint, first result)."""

    entries: Mapping[str, Tuple[str, T]] = field(default_factory=_empty_entries)

    def lookup(self, key: str, fingerprint: str) -> Optional[T]:
        """The first result for `key`, None if unseen, or a conflict if the payload changed."""
        entry = self.entries.get(key)
        if entry is None:
            return None
        if entry[0] != fingerprint:
            raise IdempotencyConflict("This idempotency key was already used with a different payload.")
        return entry[1]

    def remember(self, key: str, fingerprint: str, result: T) -> Tuple["IdempotencyLedger[T]", T]:
        """A new ledger holding `result`, plus the result that now stands for `key`."""
        existing = self.lookup(key, fingerprint)
        if existing is not None:
            return self, existing
        entries = MappingProxyType({**self.entries, key: (fingerprint, result)})
        return IdempotencyLedger(entries), result
