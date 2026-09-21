"""Typed contracts for the systems GridResolve AI would integrate with.

Evidence contracts use the field names of the canonical synthetic case, so an
adapter can serve exactly the records the agents saw. Every contract is a frozen
dataclass, every collection is a tuple, and money is Decimal.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Tuple

from . import validation as v
from .errors import ValidationError

MAX_ADJUSTMENT_USD = Decimal("500.00")
REVIEW_ROLES: Tuple[str, ...] = ("Billing Supervisor", "Compliance Reviewer")
PENDING_HUMAN_REVIEW = "PENDING_HUMAN_REVIEW"


# ---- read-only evidence ---------------------------------------------------

@dataclass(frozen=True)
class RateComponents:
    energy_charge_usd_per_kwh: Decimal
    fixed_charge_usd_per_period: Decimal

    def __post_init__(self) -> None:
        v.require_money("energy_charge_usd_per_kwh", self.energy_charge_usd_per_kwh)
        v.require_money("fixed_charge_usd_per_period", self.fixed_charge_usd_per_period)


@dataclass(frozen=True)
class CustomerAccount:
    account_id: str
    meter_id: str
    service_type: str
    rate_components: RateComponents

    def __post_init__(self) -> None:
        v.require_account_id(self.account_id)
        v.require_pattern("meter_id", self.meter_id, v.METER_ID)
        v.require_text("service_type", self.service_type, 40)


@dataclass(frozen=True)
class BillingRecord:
    record_id: str
    period_start: str
    period_end: str
    billing_days: int
    kwh_billed: int
    amount_usd: Decimal
    read_type_end: str

    def __post_init__(self) -> None:
        v.require_pattern("record_id", self.record_id, v.BILL_ID)
        v.require_pattern("period_start", self.period_start, v.ISO_DATE)
        v.require_pattern("period_end", self.period_end, v.ISO_DATE)
        v.require_int("billing_days", self.billing_days, 1)
        v.require_int("kwh_billed", self.kwh_billed)
        v.require_money("amount_usd", self.amount_usd)
        v.require_text("read_type_end", self.read_type_end, 40)


@dataclass(frozen=True)
class MeterReading:
    record_id: str
    read_date: str
    read_type: str
    register_kwh: int

    def __post_init__(self) -> None:
        v.require_pattern("record_id", self.record_id, v.READ_ID)
        v.require_pattern("read_date", self.read_date, v.ISO_DATE)
        v.require_text("read_type", self.read_type, 40)
        v.require_int("register_kwh", self.register_kwh)


@dataclass(frozen=True)
class MeterEvent:
    record_id: str
    event_date: str
    type: str
    detail: str

    def __post_init__(self) -> None:
        v.require_pattern("record_id", self.record_id, v.EVENT_ID)
        v.require_pattern("event_date", self.event_date, v.ISO_DATE)
        v.require_text("type", self.type, 80)


@dataclass(frozen=True)
class MeterEventHistory:
    """The event log for one meter. An empty log is a fact, and `note` says so."""

    meter_id: str
    events: Tuple[MeterEvent, ...]
    note: str


@dataclass(frozen=True)
class DiagnosticResult:
    record_id: str
    diagnostic_date: str
    type: str
    result: str
    tamper_flag: bool
    register_fault_flag: bool

    def __post_init__(self) -> None:
        v.require_pattern("record_id", self.record_id, v.DIAGNOSTIC_ID)
        v.require_pattern("diagnostic_date", self.diagnostic_date, v.ISO_DATE)
        v.require_text("type", self.type, 80)
        v.require_text("result", self.result, 40)
        v.require_bool("tamper_flag", self.tamper_flag)
        v.require_bool("register_fault_flag", self.register_fault_flag)


@dataclass(frozen=True)
class UsagePeriod:
    period: str
    kwh: int

    def __post_init__(self) -> None:
        v.require_pattern("period", self.period, v.ISO_MONTH)
        v.require_int("kwh", self.kwh)


# ---- CRM and human review -------------------------------------------------

@dataclass(frozen=True)
class CrmCase:
    case_id: str
    account_id: str
    customer_request: str
    status: str

    def __post_init__(self) -> None:
        v.require_case_id(self.case_id)
        v.require_account_id(self.account_id)
        v.require_text("customer_request", self.customer_request)


@dataclass(frozen=True)
class OutboundMessage:
    """A customer message. `compliance_approved` must be true before a CRM sends it."""

    case_id: str
    idempotency_key: str
    body: str
    compliance_approved: bool

    def __post_init__(self) -> None:
        v.require_case_id(self.case_id)
        v.require_idempotency_key(self.idempotency_key)
        v.require_text("body", self.body)
        v.require_bool("compliance_approved", self.compliance_approved)


@dataclass(frozen=True)
class MessageReceipt:
    case_id: str
    idempotency_key: str
    message_id: str
    accepted: bool


@dataclass(frozen=True)
class ReviewAssignment:
    case_id: str
    assignee_role: str
    reason: str
    decision_card_ref: str
    idempotency_key: str

    def __post_init__(self) -> None:
        v.require_case_id(self.case_id)
        if self.assignee_role not in REVIEW_ROLES:
            raise ValidationError("assignee_role is not a known review role.")
        v.require_text("reason", self.reason, v.MAX_DETAIL_LENGTH)
        v.require_text("decision_card_ref", self.decision_card_ref, 120)
        v.require_idempotency_key(self.idempotency_key)


@dataclass(frozen=True)
class AssignmentReceipt:
    case_id: str
    idempotency_key: str
    assignment_id: str
    assignee_role: str
    status: str


# ---- financial adjustment authorization -----------------------------------

class AdjustmentDecision(Enum):
    APPROVED = "APPROVED"
    DENIED = "DENIED"


def require_adjustment_amount(value: object) -> Decimal:
    """A positive Decimal in whole cents, within the per-request ceiling."""
    amount = v.require_money("amount_usd", value)
    exponent = amount.as_tuple().exponent
    if amount <= 0 or amount > MAX_ADJUSTMENT_USD or not isinstance(exponent, int) or exponent < -2:
        raise ValidationError("amount_usd must be positive, in whole cents, and within the ceiling.")
    return amount


@dataclass(frozen=True)
class AdjustmentRequest:
    """A person asking for an adjustment. It moves no money and decides nothing."""

    request_id: str
    case_id: str
    account_id: str
    amount_usd: Decimal
    reason: str
    requested_by: str
    idempotency_key: str

    def __post_init__(self) -> None:
        v.require_pattern("request_id", self.request_id, v.REQUEST_ID)
        v.require_case_id(self.case_id)
        v.require_account_id(self.account_id)
        require_adjustment_amount(self.amount_usd)
        v.require_text("reason", self.reason, v.MAX_DETAIL_LENGTH)
        v.require_pattern("requested_by", self.requested_by, v.PRINCIPAL_ID)
        v.require_idempotency_key(self.idempotency_key)


@dataclass(frozen=True)
class AdjustmentAuthorization:
    """A supervisor's recorded decision. Applying it belongs to the system of record."""

    request_id: str
    case_id: str
    account_id: str
    amount_usd: Decimal
    decision: AdjustmentDecision
    requested_by: str
    approved_by: str
    justification: str


# ---- audit ----------------------------------------------------------------

@dataclass(frozen=True)
class AuditRecord:
    """One link in a per-case hash chain. `record_hash` covers every other field."""

    sequence: int
    case_id: str
    actor: str
    action: str
    detail: str
    recorded_at: str
    previous_hash: str
    record_hash: str
