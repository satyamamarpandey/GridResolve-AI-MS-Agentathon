"""Financial adjustment authorization. It records decisions and moves no money.

Rules, all enforced here and all tested:
  1. Only a session resolved to HUMAN_BILLING_SUPERVISOR can authorize.
  2. The approver can never be the requester (four eyes).
  3. An agent or the workflow service can neither request nor authorize.
  4. A decision is final. The identical decision replays, a different one is refused.
  5. Every request, decision and refusal is written to the audit chain.
There is no method that applies an amount to an account. That belongs to the
billing system of record, outside this package.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, Tuple

from . import validation as v
from .audit_store import AuditLog
from .auth import AccessGuard, Permission, Principal, Role, authorize
from .contracts import AdjustmentAuthorization, AdjustmentDecision, AdjustmentRequest
from .errors import AlreadyDecided, AuthorizationError, FourEyesViolation, ValidationError
from .reliability import IdempotencyLedger, fingerprint_of
from .synthetic_store import SyntheticStore

REQUEST_ID_FORMAT = "ADJ-%04d"


class SyntheticAdjustmentAdapter:
    __slots__ = ("_guard", "_store", "_audit", "_requests", "_authorizations", "_ledger")

    def __init__(self, guard: AccessGuard, store: SyntheticStore, audit: AuditLog) -> None:
        self._guard = guard
        self._store = store
        self._audit = audit
        self._requests: Tuple[AdjustmentRequest, ...] = ()
        self._authorizations: Tuple[AdjustmentAuthorization, ...] = ()
        self._ledger: IdempotencyLedger[AdjustmentRequest] = IdempotencyLedger()

    # ---- public port ------------------------------------------------------

    def request_adjustment(self, session: object, case_id: str, account_id: str, amount_usd: Decimal,
                           reason: str, idempotency_key: str) -> AdjustmentRequest:
        principal = self._guard.authenticate(session)
        candidate = AdjustmentRequest(REQUEST_ID_FORMAT % (len(self._requests) + 1), case_id, account_id,
                                      amount_usd, reason, principal.principal_id, idempotency_key)
        self._require_may_request(principal, candidate)
        fingerprint = fingerprint_of((case_id, account_id, str(amount_usd), reason, principal.principal_id))
        replay = self._ledger.lookup(idempotency_key, fingerprint)
        if replay is not None:
            return replay
        self._ledger, request = self._ledger.remember(idempotency_key, fingerprint, candidate)
        self._requests = self._requests + (request,)
        self._audit.append_record(principal.principal_id, case_id, "ADJUSTMENT_REQUESTED",
                                  "request %s for %s USD" % (request.request_id, request.amount_usd))
        return request

    def authorize_adjustment(self, session: object, request_id: str, decision: AdjustmentDecision,
                             justification: str) -> AdjustmentAuthorization:
        principal = self._guard.authenticate(session)
        v.require_pattern("request_id", request_id, v.REQUEST_ID)
        if not isinstance(decision, AdjustmentDecision):
            raise ValidationError("decision must be a member of AdjustmentDecision.")
        v.require_text("justification", justification, v.MAX_DETAIL_LENGTH)
        request = self._require_may_decide(principal, self._find_request(request_id))
        existing = self._find_authorization(request_id)
        if existing is not None:
            return _replay_or_refuse(existing, principal, decision, justification)
        return self._record_decision(principal, request, decision, justification)

    def get_pending_requests(self, session: object, case_id: str) -> Tuple[AdjustmentRequest, ...]:
        self._guard.enter(session, Permission.READ_ADJUSTMENTS, case_id)
        decided = {a.request_id for a in self._authorizations}
        return tuple(r for r in self._requests if r.case_id == case_id and r.request_id not in decided)

    def get_authorizations(self, session: object, case_id: str) -> Tuple[AdjustmentAuthorization, ...]:
        self._guard.enter(session, Permission.READ_ADJUSTMENTS, case_id)
        return tuple(a for a in self._authorizations if a.case_id == case_id)

    # ---- rules ------------------------------------------------------------

    def _require_may_request(self, principal: Principal, candidate: AdjustmentRequest) -> None:
        try:
            authorize(principal, Permission.REQUEST_ADJUSTMENT, candidate.case_id)
            if self._store.case(candidate.case_id).account.account_id != candidate.account_id:
                raise AuthorizationError()
        except AuthorizationError:
            self._audit.append_record(principal.principal_id, candidate.case_id, "ADJUSTMENT_REFUSED",
                                      "request attempt refused")
            raise

    def _require_may_decide(self, principal: Principal,
                            request: Optional[AdjustmentRequest]) -> AdjustmentRequest:
        """Supervisor role, case scope, a real request, and a different person than the requester."""
        if request is None:
            raise AuthorizationError()
        try:
            if principal.role is not Role.HUMAN_BILLING_SUPERVISOR:
                raise AuthorizationError()
            authorize(principal, Permission.AUTHORIZE_ADJUSTMENT, request.case_id)
        except AuthorizationError:
            self._audit.append_record(principal.principal_id, request.case_id, "ADJUSTMENT_REFUSED",
                                      "authorization attempt refused for %s" % request.request_id)
            raise
        if request.requested_by == principal.principal_id:
            self._audit.append_record(principal.principal_id, request.case_id, "ADJUSTMENT_REFUSED_FOUR_EYES",
                                      "requester tried to decide %s" % request.request_id)
            raise FourEyesViolation("The requester cannot decide their own request.")
        return request

    def _record_decision(self, principal: Principal, request: AdjustmentRequest,
                         decision: AdjustmentDecision, justification: str) -> AdjustmentAuthorization:
        authorization = AdjustmentAuthorization(
            request.request_id, request.case_id, request.account_id, request.amount_usd, decision,
            request.requested_by, principal.principal_id, justification)
        self._authorizations = self._authorizations + (authorization,)
        action = "ADJUSTMENT_AUTHORIZED" if decision is AdjustmentDecision.APPROVED else "ADJUSTMENT_DENIED"
        self._audit.append_record(principal.principal_id, request.case_id, action,
                                  "decision on %s requested by %s" % (request.request_id, request.requested_by))
        return authorization

    def _find_request(self, request_id: str) -> Optional[AdjustmentRequest]:
        return next((r for r in self._requests if r.request_id == request_id), None)

    def _find_authorization(self, request_id: str) -> Optional[AdjustmentAuthorization]:
        return next((a for a in self._authorizations if a.request_id == request_id), None)


def _replay_or_refuse(existing: AdjustmentAuthorization, principal: Principal, decision: AdjustmentDecision,
                      justification: str) -> AdjustmentAuthorization:
    same = (existing.approved_by, existing.decision, existing.justification) == (
        principal.principal_id, decision, justification)
    if not same:
        raise AlreadyDecided("This request already has a decision.")
    return existing
