"""Ports: the interfaces a real connector would have to implement.

The four evidence ports declare reads only. There is no method on any of them,
for any role, that writes billing, meter or diagnostic data. Every method takes
the caller's session first, so no port can be used without an identity.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Protocol, Tuple, runtime_checkable

from .auth import SessionToken
from .contracts import (
    AdjustmentAuthorization,
    AdjustmentDecision,
    AdjustmentRequest,
    AssignmentReceipt,
    AuditRecord,
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


@runtime_checkable
class AccountEvidencePort(Protocol):
    def get_account(self, session: SessionToken, case_id: str) -> CustomerAccount: ...

    def get_account_by_id(self, session: SessionToken, case_id: str, account_id: str) -> CustomerAccount: ...


@runtime_checkable
class BillingEvidencePort(Protocol):
    def get_billing_records(self, session: SessionToken, case_id: str) -> Tuple[BillingRecord, ...]: ...

    def get_usage_history(self, session: SessionToken, case_id: str) -> Tuple[UsagePeriod, ...]: ...


@runtime_checkable
class MeterEvidencePort(Protocol):
    def get_meter_readings(self, session: SessionToken, case_id: str) -> Tuple[MeterReading, ...]: ...

    def get_meter_event_history(self, session: SessionToken, case_id: str) -> MeterEventHistory: ...


@runtime_checkable
class DiagnosticEvidencePort(Protocol):
    def get_diagnostic_results(self, session: SessionToken, case_id: str) -> Tuple[DiagnosticResult, ...]: ...


@runtime_checkable
class CrmPort(Protocol):
    def get_case(self, session: SessionToken, case_id: str) -> CrmCase: ...

    def send_message(self, session: SessionToken, message: OutboundMessage) -> MessageReceipt: ...

    def get_sent_messages(self, session: SessionToken, case_id: str) -> Tuple[OutboundMessage, ...]: ...


@runtime_checkable
class ReviewAssignmentPort(Protocol):
    def assign_review(self, session: SessionToken, assignment: ReviewAssignment) -> AssignmentReceipt: ...

    def get_assignments(self, session: SessionToken, case_id: str) -> Tuple[ReviewAssignment, ...]: ...


@runtime_checkable
class AdjustmentAuthorizationPort(Protocol):
    """Records a request and a supervisor's decision. It applies nothing to an account."""

    def request_adjustment(self, session: SessionToken, case_id: str, account_id: str, amount_usd: Decimal,
                           reason: str, idempotency_key: str) -> AdjustmentRequest: ...

    def authorize_adjustment(self, session: SessionToken, request_id: str, decision: AdjustmentDecision,
                             justification: str) -> AdjustmentAuthorization: ...

    def get_pending_requests(self, session: SessionToken, case_id: str) -> Tuple[AdjustmentRequest, ...]: ...

    def get_authorizations(self, session: SessionToken, case_id: str) -> Tuple[AdjustmentAuthorization, ...]: ...


@runtime_checkable
class AuditStorePort(Protocol):
    """Append and read. There is no way to change or drop a record."""

    def append(self, session: SessionToken, case_id: str, action: str, detail: str) -> AuditRecord: ...

    def records(self, session: SessionToken, case_id: str) -> Tuple[AuditRecord, ...]: ...

    def verify(self, session: SessionToken, case_id: str) -> bool: ...
