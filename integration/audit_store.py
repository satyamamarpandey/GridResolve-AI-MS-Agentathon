"""Append-only, hash-chained audit records, one chain per case.

Each record's hash covers its content and the hash before it, so an edit, a
deletion or a reordering breaks verification. Neither class here has a method
that changes or drops a record.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from types import MappingProxyType
from typing import Mapping, Sequence, Tuple

from . import validation as v
from .auth import AccessGuard, Clock, Permission
from .contracts import AuditRecord

GENESIS_HASH = "0" * 64


def hash_record(record: AuditRecord) -> str:
    """SHA-256 over every field except `record_hash`, in a fixed order."""
    body = [record.sequence, record.case_id, record.actor, record.action, record.detail,
            record.recorded_at, record.previous_hash]
    return hashlib.sha256(json.dumps(body, ensure_ascii=True).encode("utf-8")).hexdigest()


def verify_chain(records: Sequence[AuditRecord]) -> bool:
    """True only if sequence, back-links and hashes are all intact."""
    previous = GENESIS_HASH
    for index, record in enumerate(records):
        if record.sequence != index + 1 or record.previous_hash != previous:
            return False
        if record.record_hash != hash_record(record):
            return False
        previous = record.record_hash
    return True


class AuditLog:
    """The chains themselves. Adapters write here with the actor the session resolved to."""

    __slots__ = ("_clock", "_chains")

    def __init__(self, clock: Clock) -> None:
        self._clock = clock
        self._chains: Mapping[str, Tuple[AuditRecord, ...]] = MappingProxyType({})

    def append_record(self, actor: str, case_id: str, action: str, detail: str) -> AuditRecord:
        v.require_pattern("actor", actor, v.PRINCIPAL_ID)
        v.require_case_id(case_id)
        v.require_pattern("action", action, v.AUDIT_ACTION)
        v.require_text("detail", detail, v.MAX_DETAIL_LENGTH)
        chain = self._chains.get(case_id, ())
        stamp = datetime.fromtimestamp(self._clock.now(), tz=timezone.utc).isoformat()
        previous = chain[-1].record_hash if chain else GENESIS_HASH
        unsigned = AuditRecord(len(chain) + 1, case_id, actor, action, detail, stamp, previous, "")
        record = AuditRecord(unsigned.sequence, case_id, actor, action, detail, stamp, previous,
                             hash_record(unsigned))
        self._chains = MappingProxyType({**self._chains, case_id: chain + (record,)})
        return record

    def records_for(self, case_id: str) -> Tuple[AuditRecord, ...]:
        return self._chains.get(case_id, ())


class SyntheticAuditStore:
    """The audit port. The actor is taken out of the session, never out of an argument."""

    __slots__ = ("_guard", "_log")

    def __init__(self, guard: AccessGuard, log: AuditLog) -> None:
        self._guard = guard
        self._log = log

    def append(self, session: object, case_id: str, action: str, detail: str) -> AuditRecord:
        principal = self._guard.enter(session, Permission.APPEND_AUDIT, case_id)
        return self._log.append_record(principal.principal_id, case_id, action, detail)

    def records(self, session: object, case_id: str) -> Tuple[AuditRecord, ...]:
        self._guard.enter(session, Permission.READ_AUDIT, case_id)
        return self._log.records_for(case_id)

    def verify(self, session: object, case_id: str) -> bool:
        return verify_chain(self.records(session, case_id))
