"""Supervisor feedback loop: what a human decided about an escalated case.

A HumanReviewRecord says what the agents recommended, what the person decided,
whether the two agree, when the review started and ended, and why the person
overrode the recommendation when they did. Every record states on its face
whether a human really made the decision (ACTUAL_HUMAN_REVIEW) or the record is
an offline demonstration (OFFLINE_SIMULATION). No comment or file name carries
that distinction; the field does.

Rules enforced here and proven in tests/test_supervisor_feedback.py:
  1. Only a session resolved to a human review role with RECORD_REVIEW may record.
     An agent, the workflow service and an auditor are refused, and the refusal
     is written to the audit chain.
  2. One record per (case_id, evidence_package_ref). A second one is refused.
  3. A missing decision, a missing timestamp, or a completion before the start
     is refused with a clear error. Nothing is defaulted.
  4. Agreement is derived from the recommendation and the decision. The caller
     cannot assert it. A disagreement needs an override reason.
  5. Every accepted record is also appended to the per-case audit chain, with
     the reviewer as the actor.
  6. An override rate exists only once at least one ACTUAL_HUMAN_REVIEW record
     exists. Simulated records never enter the rate. A review-time reduction
     exists only against a baseline that carries its own provenance. No baseline
     is ever invented and no simulated duration is ever used.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from types import MappingProxyType
from typing import Mapping, Optional, Sequence, Tuple, Union

from . import validation as v
from .audit_store import AuditLog
from .auth import AccessGuard, Clock, Permission, Principal
from .contracts import REVIEW_ROLES, AuditRecord
from .errors import AuthorizationError, IntegrationError, ValidationError

AUDIT_ACTION_RECORDED = "HUMAN_REVIEW_RECORDED"
AUDIT_ACTION_REFUSED = "HUMAN_REVIEW_REFUSED"
MAX_REF_LENGTH = 120
MAX_DECISION_LENGTH = 80


class Agreement(Enum):
    AGREE = "AGREE"
    DISAGREE = "DISAGREE"


class RecordKind(Enum):
    ACTUAL_HUMAN_REVIEW = "ACTUAL_HUMAN_REVIEW"
    OFFLINE_SIMULATION = "OFFLINE_SIMULATION"


class DuplicateFeedback(IntegrationError):
    """This case and evidence package already have a review record."""


class MissingDecision(ValidationError):
    """The record names no human decision, so it records nothing."""


class MissingTimestamp(ValidationError):
    """A review record must carry both a start and a completion time."""


class TimestampOrder(ValidationError):
    """The review completed before it started."""


class MissingOverrideReason(ValidationError):
    """A disagreement with the recommendation must say why."""


def utc_stamp(clock: Clock) -> str:
    """The injected clock's current instant as an ISO 8601 UTC string."""
    return datetime.fromtimestamp(clock.now(), tz=timezone.utc).isoformat()


def _parse_stamp(field_name: str, value: object) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise MissingTimestamp("%s is required." % field_name)
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValidationError("%s is not an ISO 8601 timestamp." % field_name) from exc
    if parsed.tzinfo is None:
        raise ValidationError("%s must carry a UTC offset." % field_name)
    return parsed


def _decision_text(field_name: str, value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MissingDecision("%s is required." % field_name)
    return v.require_text(field_name, value, MAX_DECISION_LENGTH)


@dataclass(frozen=True)
class HumanReviewRecord:
    """One human review of one evidence package. Immutable once built."""

    case_id: str
    evidence_package_ref: str
    agent_recommendation: str
    human_decision: str
    agreement: Agreement
    review_started_at: str
    review_completed_at: str
    review_duration_seconds: Optional[float]
    duration_note: str
    override_reason: str
    reviewer_comments: str
    final_disposition: str
    reviewer_principal_id: str
    reviewer_role: str
    record_kind: RecordKind

    def __post_init__(self) -> None:
        v.require_case_id(self.case_id)
        v.require_text("evidence_package_ref", self.evidence_package_ref, MAX_REF_LENGTH)
        _decision_text("agent_recommendation", self.agent_recommendation)
        _decision_text("human_decision", self.human_decision)
        if not isinstance(self.agreement, Agreement):
            raise ValidationError("agreement must be a member of Agreement.")
        if not isinstance(self.record_kind, RecordKind):
            raise ValidationError("record_kind must be a member of RecordKind.")
        v.require_text("final_disposition", self.final_disposition, MAX_DECISION_LENGTH)
        v.require_pattern("reviewer_principal_id", self.reviewer_principal_id, v.PRINCIPAL_ID)
        if self.reviewer_role not in REVIEW_ROLES:
            raise ValidationError("reviewer_role is not a known review role.")
        if self.agreement is Agreement.DISAGREE and not self.override_reason.strip():
            raise MissingOverrideReason("override_reason is required when the decision disagrees.")
        if self.override_reason:
            v.require_text("override_reason", self.override_reason, v.MAX_DETAIL_LENGTH)
        if self.reviewer_comments:
            v.require_text("reviewer_comments", self.reviewer_comments, v.MAX_TEXT_LENGTH)


def derive_agreement(agent_recommendation: str, human_decision: str) -> Agreement:
    """AGREE only when the two texts match after trimming and case folding."""
    same = agent_recommendation.strip().casefold() == human_decision.strip().casefold()
    return Agreement.AGREE if same else Agreement.DISAGREE


def build_record(case_id: str, evidence_package_ref: str, agent_recommendation: str,
                 human_decision: str, review_started_at: str, review_completed_at: str,
                 final_disposition: str, reviewer_principal_id: str, reviewer_role: str,
                 record_kind: RecordKind, override_reason: str = "",
                 reviewer_comments: str = "") -> HumanReviewRecord:
    """Validate the inputs and derive agreement and duration. Raises, never defaults."""
    _decision_text("agent_recommendation", agent_recommendation)
    _decision_text("human_decision", human_decision)
    started = _parse_stamp("review_started_at", review_started_at)
    completed = _parse_stamp("review_completed_at", review_completed_at)
    if completed < started:
        raise TimestampOrder("review_completed_at is earlier than review_started_at.")
    duration = (completed - started).total_seconds()
    return HumanReviewRecord(
        case_id, evidence_package_ref, agent_recommendation, human_decision,
        derive_agreement(agent_recommendation, human_decision),
        started.isoformat(), completed.isoformat(), duration,
        "measured from the two recorded timestamps", override_reason, reviewer_comments,
        final_disposition, reviewer_principal_id, reviewer_role, record_kind)


class SupervisorFeedbackStore:
    """Append-only store of human review records, one per case and package."""

    __slots__ = ("_guard", "_audit", "_records")

    def __init__(self, guard: AccessGuard, audit: AuditLog) -> None:
        self._guard = guard
        self._audit = audit
        self._records: Mapping[Tuple[str, str], HumanReviewRecord] = MappingProxyType({})

    def record(self, session: object, case_id: str, evidence_package_ref: str,
               agent_recommendation: str, human_decision: str, review_started_at: str,
               review_completed_at: str, final_disposition: str, reviewer_role: str,
               record_kind: RecordKind, override_reason: str = "",
               reviewer_comments: str = "") -> HumanReviewRecord:
        principal = self._require_reviewer(session, case_id)
        key = (case_id, v.require_text("evidence_package_ref", evidence_package_ref, MAX_REF_LENGTH))
        if key in self._records:
            raise DuplicateFeedback("This case and evidence package already have a review record.")
        entry = build_record(case_id, evidence_package_ref, agent_recommendation, human_decision,
                             review_started_at, review_completed_at, final_disposition,
                             principal.principal_id, reviewer_role, record_kind,
                             override_reason, reviewer_comments)
        self._records = MappingProxyType({**self._records, key: entry})
        self._audit.append_record(principal.principal_id, case_id, AUDIT_ACTION_RECORDED,
                                  "%s review of %s: %s, %s" % (
                                      entry.record_kind.value, entry.evidence_package_ref,
                                      entry.human_decision, entry.agreement.value))
        return entry

    def records_for(self, session: object, case_id: str) -> Tuple[HumanReviewRecord, ...]:
        self._require_reviewer(session, case_id)
        return tuple(r for (c, _), r in self._records.items() if c == case_id)

    def all_records(self, session: object) -> Tuple[HumanReviewRecord, ...]:
        """Every record the caller may see, for the metrics functions."""
        principal = self._guard.authenticate(session)
        return tuple(r for (c, _), r in self._records.items() if c in principal.allowed_case_ids)

    def _require_reviewer(self, session: object, case_id: object) -> Principal:
        principal = self._guard.authenticate(session)
        valid_case = v.require_case_id(case_id)
        try:
            return self._guard.enter(session, Permission.RECORD_REVIEW, valid_case)
        except AuthorizationError:
            self._audit.append_record(principal.principal_id, valid_case, AUDIT_ACTION_REFUSED,
                                      "review record attempt refused")
            raise


# ---- metrics --------------------------------------------------------------

@dataclass(frozen=True)
class NotMeasured:
    """A metric that cannot be reported yet, and the reason it cannot."""

    metric: str
    reason: str
    actual_records: int
    simulated_records: int


@dataclass(frozen=True)
class OverrideRate:
    rate: float
    actual_records: int
    overrides: int
    simulated_excluded: int


@dataclass(frozen=True)
class ReviewTimeBaseline:
    """A measured baseline with its provenance. Never constructed from a guess."""

    source: str
    measured_at: str
    sample_size: int
    mean_seconds: float

    def __post_init__(self) -> None:
        v.require_text("source", self.source, v.MAX_DETAIL_LENGTH)
        _parse_stamp("measured_at", self.measured_at)
        v.require_int("sample_size", self.sample_size, 1)
        if isinstance(self.mean_seconds, bool) or not isinstance(self.mean_seconds, (int, float)) \
                or self.mean_seconds <= 0:
            raise ValidationError("mean_seconds must be a positive number.")


@dataclass(frozen=True)
class ReviewTimeReduction:
    baseline_mean_seconds: float
    observed_mean_seconds: float
    reduction_seconds: float
    actual_records: int
    baseline_source: str


def _split(records: Sequence[HumanReviewRecord]) -> Tuple[Tuple[HumanReviewRecord, ...], int]:
    actual = tuple(r for r in records if r.record_kind is RecordKind.ACTUAL_HUMAN_REVIEW)
    return actual, len(records) - len(actual)


def override_rate(records: Sequence[HumanReviewRecord]) -> Union[OverrideRate, NotMeasured]:
    actual, simulated = _split(records)
    if not actual:
        return NotMeasured("supervisor_override_rate",
                           "No actual human decision has been recorded. Simulated records "
                           "are excluded from the rate.", 0, simulated)
    overrides = sum(1 for r in actual if r.agreement is Agreement.DISAGREE)
    return OverrideRate(overrides / len(actual), len(actual), overrides, simulated)


def review_time_reduction(records: Sequence[HumanReviewRecord],
                          baseline: Optional[ReviewTimeBaseline] = None
                          ) -> Union[ReviewTimeReduction, NotMeasured]:
    actual, simulated = _split(records)
    timed = tuple(r for r in actual if r.review_duration_seconds is not None)
    if baseline is None:
        return NotMeasured("review_time_reduction",
                           "No comparable baseline with provenance was supplied. A baseline is "
                           "never invented.", len(timed), simulated)
    if not isinstance(baseline, ReviewTimeBaseline):
        raise ValidationError("baseline must be a ReviewTimeBaseline.")
    if not timed:
        return NotMeasured("review_time_reduction",
                           "No actual human review carries a measured duration. Simulated "
                           "durations are never used.", 0, simulated)
    observed = sum(r.review_duration_seconds or 0.0 for r in timed) / len(timed)
    return ReviewTimeReduction(baseline.mean_seconds, observed, baseline.mean_seconds - observed,
                               len(timed), baseline.source)


def audit_entries_for(records: Sequence[AuditRecord], case_id: str) -> Tuple[AuditRecord, ...]:
    """The review entries in one case's audit chain."""
    return tuple(r for r in records if r.case_id == case_id and r.action == AUDIT_ACTION_RECORDED)
