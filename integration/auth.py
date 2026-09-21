"""Caller identity and authorization rules.

A role is an enum member attached to a principal that the identity provider
resolved out of a session it issued. A role string, a hand-built principal or a
guessed token gets nowhere. The synthetic identity provider stands in for a real
one. It is the trust root, and agents are never handed it.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Dict, FrozenSet, Iterator, Mapping, Protocol, Tuple

from . import validation as v
from .errors import AuthenticationError, AuthorizationError, ValidationError

SessionToken = str
DEFAULT_SESSION_TTL_SECONDS = 900.0
TOKEN_BYTES = 32


class Role(Enum):
    AGENT = "AGENT"
    WORKFLOW_SERVICE = "WORKFLOW_SERVICE"
    HUMAN_REVIEWER = "HUMAN_REVIEWER"
    HUMAN_BILLING_SUPERVISOR = "HUMAN_BILLING_SUPERVISOR"
    AUDITOR = "AUDITOR"


class Permission(Enum):
    READ_EVIDENCE = "READ_EVIDENCE"
    SEND_MESSAGE = "SEND_MESSAGE"
    ASSIGN_REVIEW = "ASSIGN_REVIEW"
    REQUEST_ADJUSTMENT = "REQUEST_ADJUSTMENT"
    AUTHORIZE_ADJUSTMENT = "AUTHORIZE_ADJUSTMENT"
    READ_ADJUSTMENTS = "READ_ADJUSTMENTS"
    APPEND_AUDIT = "APPEND_AUDIT"
    READ_AUDIT = "READ_AUDIT"


class _RoleTable(Mapping[Role, FrozenSet[Permission]]):
    """A read-only mapping. Any attempt to assign, delete or rebind raises TypeError."""

    __slots__ = ("_table",)

    def __init__(self, table: Dict[Role, FrozenSet[Permission]]) -> None:
        object.__setattr__(self, "_table", MappingProxyType(dict(table)))

    def __getitem__(self, role: Role) -> FrozenSet[Permission]:
        return self._table[role]

    def __iter__(self) -> Iterator[Role]:
        return iter(self._table)

    def __len__(self) -> int:
        return len(self._table)

    def __setitem__(self, role: object, permissions: object) -> None:
        raise TypeError("The role table is read-only.")

    def __delitem__(self, role: object) -> None:
        raise TypeError("The role table is read-only.")

    def __setattr__(self, name: str, value: object) -> None:
        raise TypeError("The role table is read-only.")


# No write permission over billing data exists at all. The agent role reads
# evidence and nothing else. Only the supervisor role can authorize.
ROLE_PERMISSIONS: Mapping[Role, FrozenSet[Permission]] = _RoleTable({
    Role.AGENT: frozenset({Permission.READ_EVIDENCE}),
    Role.WORKFLOW_SERVICE: frozenset({
        Permission.READ_EVIDENCE, Permission.SEND_MESSAGE, Permission.ASSIGN_REVIEW,
        Permission.APPEND_AUDIT}),
    Role.HUMAN_REVIEWER: frozenset({
        Permission.READ_EVIDENCE, Permission.REQUEST_ADJUSTMENT, Permission.READ_ADJUSTMENTS}),
    Role.HUMAN_BILLING_SUPERVISOR: frozenset({
        Permission.READ_EVIDENCE, Permission.REQUEST_ADJUSTMENT, Permission.READ_ADJUSTMENTS,
        Permission.AUTHORIZE_ADJUSTMENT}),
    Role.AUDITOR: frozenset({Permission.READ_AUDIT}),
})


@dataclass(frozen=True)
class Principal:
    """Who is calling: an id, a role, and the cases they may touch."""

    principal_id: str
    role: Role
    allowed_case_ids: Tuple[str, ...]

    def __post_init__(self) -> None:
        v.require_pattern("principal_id", self.principal_id, v.PRINCIPAL_ID)
        if not isinstance(self.role, Role):
            raise ValidationError("role must be a member of Role.")
        if not isinstance(self.allowed_case_ids, tuple):
            raise ValidationError("allowed_case_ids must be a tuple.")
        for case_id in self.allowed_case_ids:
            v.require_case_id(case_id)
        if self.role is Role.AGENT and len(self.allowed_case_ids) != 1:
            raise ValidationError("An agent principal is scoped to exactly one case.")


def authorize(principal: Principal, permission: Permission, case_id: str) -> None:
    """Raise AuthorizationError unless the role holds `permission` for `case_id`."""
    if not isinstance(principal, Principal):
        raise AuthorizationError()
    if permission not in ROLE_PERMISSIONS.get(principal.role, frozenset()):
        raise AuthorizationError()
    if case_id not in principal.allowed_case_ids:
        raise AuthorizationError()


class Clock(Protocol):
    def now(self) -> float: ...


@dataclass(frozen=True)
class _Session:
    principal: Principal
    expires_at: float


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class SyntheticIdentityProvider:
    """Issues opaque, expiring sessions. Only token digests are kept."""

    __slots__ = ("_clock", "_sessions", "ttl_seconds")

    def __init__(self, clock: Clock, ttl_seconds: float = DEFAULT_SESSION_TTL_SECONDS) -> None:
        self._clock = clock
        self._sessions: Mapping[str, _Session] = MappingProxyType({})
        self.ttl_seconds = ttl_seconds

    def issue(self, principal: Principal) -> SessionToken:
        if not isinstance(principal, Principal):
            raise ValidationError("principal must be a Principal.")
        token = secrets.token_hex(TOKEN_BYTES)
        session = _Session(principal, self._clock.now() + self.ttl_seconds)
        self._sessions = MappingProxyType({**self._sessions, _digest(token): session})
        return token

    def revoke(self, token: SessionToken) -> bool:
        """End a session. Returns whether there was one to end."""
        key = _digest(token) if isinstance(token, str) else ""
        found = key in self._sessions
        self._sessions = MappingProxyType({k: s for k, s in self._sessions.items() if k != key})
        return found

    def resolve(self, token: object) -> Principal:
        """The principal behind `token`, or AuthenticationError with no reason given."""
        if not isinstance(token, str) or not token:
            raise AuthenticationError()
        session = self._sessions.get(_digest(token))
        if session is None or self._clock.now() >= session.expires_at:
            raise AuthenticationError()
        return session.principal


class AccessGuard:
    """The one entry check every adapter uses: authenticate, validate, authorize."""

    __slots__ = ("_identity",)

    def __init__(self, identity: SyntheticIdentityProvider) -> None:
        self._identity = identity

    def authenticate(self, session: object) -> Principal:
        return self._identity.resolve(session)

    def enter(self, session: object, permission: Permission, case_id: object) -> Principal:
        principal = self.authenticate(session)
        authorize(principal, permission, v.require_case_id(case_id))
        return principal
