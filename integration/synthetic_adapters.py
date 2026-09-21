"""In-memory adapters backed by synthetic cases. Local mocks, nothing more.

Every public method follows the same order: authenticate the session, validate
the input, authorize for the one case, then act. The evidence adapter has reads
only. State held by the CRM and review adapters is kept in tuples and replaced,
never edited in place.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Tuple

from . import validation as v
from .adjustments import SyntheticAdjustmentAdapter
from .audit_store import AuditLog, SyntheticAuditStore
from .auth import AccessGuard, Clock, Permission, SyntheticIdentityProvider, authorize
from .contracts import (
    PENDING_HUMAN_REVIEW,
    AssignmentReceipt,
    BillingRecord,
    CrmCase,
    CustomerAccount,
    DiagnosticResult,
    MessageReceipt,
    MeterEventHistory,
    MeterReading,
    OutboundMessage,
    ReviewAssignment,
    UsagePeriod,
)
from .errors import AuthorizationError, ValidationError
from .reliability import IdempotencyLedger, fingerprint_of
from .synthetic_store import CaseRecords, SyntheticStore, build_store

__all__ = ["SyntheticEnvironment", "SyntheticEvidenceAdapter", "SyntheticCrmAdapter",
           "SyntheticReviewAdapter", "build_store", "build_synthetic_environment"]

MESSAGE_ID_FORMAT = "MSG-%04d"
ASSIGNMENT_ID_FORMAT = "REV-%04d"


class SyntheticEvidenceAdapter:
    """Read-only evidence for one case at a time. There is no write method to call."""

    __slots__ = ("_guard", "_store")

    def __init__(self, guard: AccessGuard, store: SyntheticStore) -> None:
        self._guard = guard
        self._store = store

    def _case(self, session: object, case_id: object) -> CaseRecords:
        self._guard.enter(session, Permission.READ_EVIDENCE, case_id)
        return self._store.case(str(case_id))

    def get_account(self, session: object, case_id: str) -> CustomerAccount:
        return self._case(session, case_id).account

    def get_account_by_id(self, session: object, case_id: str, account_id: str) -> CustomerAccount:
        """The account, only if it is the one attached to the caller's own case."""
        self._guard.authenticate(session)
        v.require_case_id(case_id)
        v.require_account_id(account_id)
        account = self._case(session, case_id).account
        if account.account_id != account_id:
            raise AuthorizationError()
        return account

    def get_billing_records(self, session: object, case_id: str) -> Tuple[BillingRecord, ...]:
        return self._case(session, case_id).billing_records

    def get_usage_history(self, session: object, case_id: str) -> Tuple[UsagePeriod, ...]:
        return self._case(session, case_id).usage_history

    def get_meter_readings(self, session: object, case_id: str) -> Tuple[MeterReading, ...]:
        return self._case(session, case_id).meter_readings

    def get_meter_event_history(self, session: object, case_id: str) -> MeterEventHistory:
        return self._case(session, case_id).meter_events

    def get_diagnostic_results(self, session: object, case_id: str) -> Tuple[DiagnosticResult, ...]:
        return self._case(session, case_id).diagnostics


class SyntheticCrmAdapter:
    """Sends a customer message once per idempotency key, and only if compliance approved it."""

    __slots__ = ("_guard", "_store", "_audit", "_sent", "_ledger")

    def __init__(self, guard: AccessGuard, store: SyntheticStore, audit: AuditLog) -> None:
        self._guard = guard
        self._store = store
        self._audit = audit
        self._sent: Tuple[OutboundMessage, ...] = ()
        self._ledger: IdempotencyLedger[MessageReceipt] = IdempotencyLedger()

    def get_case(self, session: object, case_id: str) -> CrmCase:
        self._guard.enter(session, Permission.READ_EVIDENCE, case_id)
        return self._store.case(case_id).crm_case

    def send_message(self, session: object, message: OutboundMessage) -> MessageReceipt:
        principal = self._guard.authenticate(session)
        if not isinstance(message, OutboundMessage):
            raise ValidationError("message must be an OutboundMessage.")
        if message.compliance_approved is not True:
            raise ValidationError("A message without compliance approval is never sent.")
        authorize(principal, Permission.SEND_MESSAGE, message.case_id)
        self._store.case(message.case_id)
        fingerprint = fingerprint_of(message)
        replay = self._ledger.lookup(message.idempotency_key, fingerprint)
        if replay is not None:
            return replay
        receipt = MessageReceipt(message.case_id, message.idempotency_key,
                                 MESSAGE_ID_FORMAT % (len(self._sent) + 1), True)
        self._ledger, receipt = self._ledger.remember(message.idempotency_key, fingerprint, receipt)
        self._sent = self._sent + (message,)
        self._audit.append_record(principal.principal_id, message.case_id, "CUSTOMER_MESSAGE_SENT",
                                  "message %s, %d characters" % (receipt.message_id, len(message.body)))
        return receipt

    def get_sent_messages(self, session: object, case_id: str) -> Tuple[OutboundMessage, ...]:
        self._guard.enter(session, Permission.SEND_MESSAGE, case_id)
        return tuple(m for m in self._sent if m.case_id == case_id)


class SyntheticReviewAdapter:
    """Creates one human work item per idempotency key. It notifies nobody."""

    __slots__ = ("_guard", "_store", "_audit", "_assigned", "_ledger")

    def __init__(self, guard: AccessGuard, store: SyntheticStore, audit: AuditLog) -> None:
        self._guard = guard
        self._store = store
        self._audit = audit
        self._assigned: Tuple[ReviewAssignment, ...] = ()
        self._ledger: IdempotencyLedger[AssignmentReceipt] = IdempotencyLedger()

    def assign_review(self, session: object, assignment: ReviewAssignment) -> AssignmentReceipt:
        principal = self._guard.authenticate(session)
        if not isinstance(assignment, ReviewAssignment):
            raise ValidationError("assignment must be a ReviewAssignment.")
        authorize(principal, Permission.ASSIGN_REVIEW, assignment.case_id)
        self._store.case(assignment.case_id)
        fingerprint = fingerprint_of(assignment)
        replay = self._ledger.lookup(assignment.idempotency_key, fingerprint)
        if replay is not None:
            return replay
        receipt = AssignmentReceipt(assignment.case_id, assignment.idempotency_key,
                                    ASSIGNMENT_ID_FORMAT % (len(self._assigned) + 1),
                                    assignment.assignee_role, PENDING_HUMAN_REVIEW)
        self._ledger, receipt = self._ledger.remember(assignment.idempotency_key, fingerprint, receipt)
        self._assigned = self._assigned + (assignment,)
        self._audit.append_record(principal.principal_id, assignment.case_id, "HUMAN_REVIEW_ASSIGNED",
                                  "%s to %s" % (receipt.assignment_id, assignment.assignee_role))
        return receipt

    def get_assignments(self, session: object, case_id: str) -> Tuple[ReviewAssignment, ...]:
        self._guard.enter(session, Permission.ASSIGN_REVIEW, case_id)
        return tuple(a for a in self._assigned if a.case_id == case_id)


@dataclass(frozen=True)
class SyntheticEnvironment:
    """Everything wired together for a test or a demonstration."""

    identity: SyntheticIdentityProvider
    evidence: SyntheticEvidenceAdapter
    crm: SyntheticCrmAdapter
    review: SyntheticReviewAdapter
    adjustments: SyntheticAdjustmentAdapter
    audit: SyntheticAuditStore


def build_synthetic_environment(cases: Iterable[Mapping[str, object]], clock: Clock) -> SyntheticEnvironment:
    """Build the adapters over `cases`. `clock` drives session expiry and audit timestamps."""
    store = build_store(cases)
    identity = SyntheticIdentityProvider(clock)
    guard = AccessGuard(identity)
    log = AuditLog(clock)
    return SyntheticEnvironment(
        identity=identity,
        evidence=SyntheticEvidenceAdapter(guard, store),
        crm=SyntheticCrmAdapter(guard, store, log),
        review=SyntheticReviewAdapter(guard, store, log),
        adjustments=SyntheticAdjustmentAdapter(guard, store, log),
        audit=SyntheticAuditStore(guard, log),
    )
