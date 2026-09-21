"""
Production integration contracts, exercised against local synthetic adapters.

No network, no Azure call, no model call, no cost. Nothing here talks to a real
utility, meter, CRM or identity system. The adapters are in-memory stand-ins
backed by the canonical synthetic case, and these checks prove the properties a
real implementation would have to keep: an authentication boundary, read-only
evidence, case-level authorization, customer-data isolation, input validation,
timeouts, idempotency, safe retry, supervisor-only adjustment authority with a
four-eyes rule, and an append-only hash-chained audit record.

Run: python tests/test_integration_contracts.py
"""
import dataclasses
import json
import os
import re
import sys
from decimal import Decimal

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

passes = []
failures = []


def check(name, cond, detail=""):
    (passes if cond else failures).append((name, detail))
    print("  [%s] %-74s %s" % ("PASS" if cond else "FAIL", name, detail))


def raised(exc_type, fn):
    """The exception `fn` raised if it is an `exc_type`, otherwise None."""
    try:
        fn()
    except exc_type as exc:
        return exc
    except Exception as exc:  # a different failure is reported, never hidden
        print("      unexpected %s: %s" % (type(exc).__name__, exc))
        return None
    return None


try:
    from integration import adjustments, audit_store, auth, contracts, errors, ports, reliability
    from integration import synthetic_adapters as sa
except ImportError as exc:
    print("integration package is not importable: %s" % exc)
    print("\nRESULT: 0 passed, 1 failed")
    sys.exit(1)


class FakeClock:
    """Test clock. Advancing it is how a slow dependency is simulated."""

    def __init__(self, start=1_800_000_000.0):
        self.value = start

    def now(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


CANONICAL_PATH = os.path.join(ROOT, "submission", "SYN-CASE-4003_input.json")
CANONICAL = json.load(open(CANONICAL_PATH, encoding="utf-8"))
RECORDS = CANONICAL["synthetic_account_records"]

# A second synthetic customer, so that isolation has something to isolate from.
OTHER_CASE = {
    "case_id": "SYN-CASE-4099",
    "data_classification": "SYNTHETIC_ONLY",
    "customer_request": "Synthetic second customer used only to test isolation.",
    "synthetic_account_records": {
        "account_id": "SYN-ACCT-0099",
        "meter_id": "SYN-MTR-0099",
        "service_type": "electric",
        "rate_components": {"energy_charge_usd_per_kwh": 0.31, "fixed_charge_usd_per_period": 9.00},
        "billing_history": [
            {"record_id": "SYN-BILL-0099-07", "period_start": "2026-07-01", "period_end": "2026-07-31",
             "billing_days": 31, "kwh_billed": 111, "amount_usd": 43.41, "read_type_end": "estimated"}
        ],
        "meter_reads": [
            {"record_id": "SYN-READ-0099-A", "read_date": "2026-07-31", "read_type": "estimated",
             "register_kwh": 7777}
        ],
        "meter_events": [],
        "meter_event_note": "No meter events recorded.",
        "diagnostic_records": [],
    },
}
OTHER_MARKERS = ("0099", "43.41", "7777", "0.31")

CASE = "SYN-CASE-4003"
ACCOUNT = "SYN-ACCT-0003"


def environment(clock=None):
    return sa.build_synthetic_environment([CANONICAL, OTHER_CASE], clock or FakeClock())


def sessions(env):
    """One session per role, all scoped to the canonical case unless stated."""
    idp = env.identity
    P, R = auth.Principal, auth.Role
    return {
        "agent": idp.issue(P("agent-account-evidence", R.AGENT, (CASE,))),
        "workflow": idp.issue(P("workflow-gridresolve", R.WORKFLOW_SERVICE, (CASE,))),
        "reviewer": idp.issue(P("human-reviewer-01", R.HUMAN_REVIEWER, (CASE,))),
        "supervisor": idp.issue(P("human-supervisor-01", R.HUMAN_BILLING_SUPERVISOR, (CASE,))),
        "supervisor2": idp.issue(P("human-supervisor-02", R.HUMAN_BILLING_SUPERVISOR, (CASE,))),
        "auditor": idp.issue(P("human-auditor-01", R.AUDITOR, (CASE,))),
        "other_agent": idp.issue(P("agent-other-case", R.AGENT, ("SYN-CASE-4099",))),
    }


# --------------------------------------------------------------------------
print("\n1. CONTRACTS LINE UP WITH THE CANONICAL CASE")
env = environment()
s = sessions(env)
account = env.evidence.get_account(s["agent"], CASE)
bills = env.evidence.get_billing_records(s["agent"], CASE)
reads = env.evidence.get_meter_readings(s["agent"], CASE)
events = env.evidence.get_meter_event_history(s["agent"], CASE)
diags = env.evidence.get_diagnostic_results(s["agent"], CASE)


def field_names(cls):
    return {f.name for f in dataclasses.fields(cls)}


check("billing contract has exactly the case's billing fields",
      field_names(contracts.BillingRecord) == set(RECORDS["billing_history"][0]))
check("meter reading contract has exactly the case's read fields",
      field_names(contracts.MeterReading) == set(RECORDS["meter_reads"][0]))
check("diagnostic contract has exactly the case's diagnostic fields",
      field_names(contracts.DiagnosticResult) == set(RECORDS["diagnostic_records"][0]))
check("rate components contract has exactly the case's rate fields",
      field_names(contracts.RateComponents) == set(RECORDS["rate_components"]))
check("account contract carries account, meter, service type and rate",
      {"account_id", "meter_id", "service_type", "rate_components"} <= field_names(contracts.CustomerAccount))
check("the adapter serves the account the agents saw",
      (account.account_id, account.meter_id, account.service_type)
      == (RECORDS["account_id"], RECORDS["meter_id"], RECORDS["service_type"]))
check("the adapter serves both bills, in order, with the same record ids",
      [b.record_id for b in bills] == [b["record_id"] for b in RECORDS["billing_history"]])
check("the adapter serves both reads with the same registers",
      [r.register_kwh for r in reads] == [r["register_kwh"] for r in RECORDS["meter_reads"]])
check("money is exact decimal, never binary float",
      all(isinstance(b.amount_usd, Decimal) for b in bills)
      and isinstance(account.rate_components.energy_charge_usd_per_kwh, Decimal))
rate = account.rate_components
check("both bills reconstruct exactly from the served rate",
      all(b.kwh_billed * rate.energy_charge_usd_per_kwh + rate.fixed_charge_usd_per_period == b.amount_usd
          for b in bills), str([str(b.amount_usd) for b in bills]))
check("register movement equals billed consumption, from served records",
      reads[1].register_kwh - reads[0].register_kwh == bills[1].kwh_billed == 870)
check("an empty event log is served as empty, with its note, not invented",
      events.events == () and events.note == RECORDS["meter_event_note"])
check("the diagnostic is served as recorded",
      len(diags) == 1 and diags[0].result == "PASS" and diags[0].tamper_flag is False
      and diags[0].register_fault_flag is False)
check("every contract is a frozen dataclass",
      all(dataclasses.is_dataclass(c) and c.__dataclass_params__.frozen for c in (
          contracts.CustomerAccount, contracts.RateComponents, contracts.BillingRecord,
          contracts.MeterReading, contracts.MeterEvent, contracts.MeterEventHistory,
          contracts.DiagnosticResult, contracts.CrmCase, contracts.OutboundMessage,
          contracts.MessageReceipt, contracts.ReviewAssignment, contracts.AssignmentReceipt,
          contracts.AdjustmentRequest, contracts.AdjustmentAuthorization, contracts.AuditRecord)))
check("the canonical case file was only read", json.load(open(CANONICAL_PATH, encoding="utf-8")) == CANONICAL)

# --------------------------------------------------------------------------
print("\n2. AUTHENTICATION BOUNDARY")
for label, token in (("no token", None), ("empty token", ""), ("made-up token", "not-a-session"),
                     ("a principal object instead of a token",
                      auth.Principal("human-supervisor-09", auth.Role.HUMAN_BILLING_SUPERVISOR, (CASE,)))):
    check("evidence refused with %s" % label,
          raised(errors.AuthenticationError, lambda t=token: env.evidence.get_billing_records(t, CASE)) is not None)
check("audit read refused without a session",
      raised(errors.AuthenticationError, lambda: env.audit.records(None, CASE)) is not None)
check("adjustment authorization refused without a session",
      raised(errors.AuthenticationError,
             lambda: env.adjustments.authorize_adjustment(None, "ADJ-0001", contracts.AdjustmentDecision.APPROVED,
                                                          "x")) is not None)
revoked = env.identity.issue(auth.Principal("agent-revoked", auth.Role.AGENT, (CASE,)))
env.identity.revoke(revoked)
check("a revoked session is refused",
      raised(errors.AuthenticationError, lambda: env.evidence.get_account(revoked, CASE)) is not None)
clock = FakeClock()
env_ttl = environment(clock)
short = env_ttl.identity.issue(auth.Principal("agent-expiring", auth.Role.AGENT, (CASE,)))
check("a fresh session works", env_ttl.evidence.get_account(short, CASE).account_id == ACCOUNT)
clock.advance(env_ttl.identity.ttl_seconds + 1)
check("an expired session is refused",
      raised(errors.AuthenticationError, lambda: env_ttl.evidence.get_account(short, CASE)) is not None)
check("sessions are opaque and unguessable",
      len(s["agent"]) >= 32 and "agent" not in s["agent"] and "AGENT" not in s["agent"]
      and len({env.identity.issue(auth.Principal("agent-repeat", auth.Role.AGENT, (CASE,))) for _ in range(5)}) == 5)
check("an authentication failure does not say why",
      str(raised(errors.AuthenticationError, lambda: env.evidence.get_account("nope", CASE)))
      == str(raised(errors.AuthenticationError, lambda: env.evidence.get_account(revoked, CASE))))

# --------------------------------------------------------------------------
print("\n3. EVIDENCE IS READ-ONLY")
WRITE_WORDS = ("set", "put", "post", "write", "update", "delete", "remove", "create", "add", "insert",
               "patch", "save", "adjust", "apply", "correct")
public_evidence = [n for n in dir(env.evidence) if not n.startswith("_")]
check("every public evidence method is a read", all(n.startswith("get_") for n in public_evidence),
      str(public_evidence))
check("no evidence method name suggests a write",
      not any(n.split("_")[0] in WRITE_WORDS for n in public_evidence))
port_methods = [n for n in dir(ports.BillingEvidencePort) if not n.startswith("_")]
check("the evidence port protocols declare reads only",
      all(n.startswith("get_") for p in (ports.AccountEvidencePort, ports.BillingEvidencePort,
                                         ports.MeterEvidencePort, ports.DiagnosticEvidencePort)
          for n in dir(p) if not n.startswith("_")), str(port_methods))
check("the synthetic adapter satisfies every evidence port",
      all(isinstance(env.evidence, p) for p in (ports.AccountEvidencePort, ports.BillingEvidencePort,
                                                ports.MeterEvidencePort, ports.DiagnosticEvidencePort)))
check("a served bill cannot be modified",
      raised(dataclasses.FrozenInstanceError, lambda: setattr(bills[1], "amount_usd", Decimal("1.00"))) is not None)
check("a served rate cannot be modified",
      raised(dataclasses.FrozenInstanceError,
             lambda: setattr(account.rate_components, "energy_charge_usd_per_kwh", Decimal("0"))) is not None)
check("collections are tuples, so nothing can be appended", isinstance(bills, tuple) and isinstance(reads, tuple)
      and isinstance(diags, tuple) and isinstance(events.events, tuple))
check("a second read returns the same facts", env.evidence.get_billing_records(s["agent"], CASE) == bills)
check("even a supervisor has no way to write billing data through an evidence port",
      not any(n.split("_")[0] in WRITE_WORDS for n in dir(env.evidence) if not n.startswith("__")))

# --------------------------------------------------------------------------
print("\n4. CASE AUTHORIZATION AND CUSTOMER-DATA ISOLATION")
denied_other = raised(errors.AuthorizationError, lambda: env.evidence.get_billing_records(s["agent"], "SYN-CASE-4099"))
denied_missing = raised(errors.AuthorizationError, lambda: env.evidence.get_billing_records(s["agent"], "SYN-CASE-0001"))
check("an agent scoped to one case cannot read another case", denied_other is not None)
check("a case that does not exist is refused the same way", denied_missing is not None)
check("the two refusals are indistinguishable, so cases cannot be enumerated",
      denied_other is not None and denied_missing is not None and str(denied_other) == str(denied_missing)
      and type(denied_other) is type(denied_missing))
check("the refusal text names no case, account, amount or reading",
      denied_other is not None and not any(m in str(denied_other) for m in OTHER_MARKERS + ("SYN-", "4003")),
      str(denied_other))
check("the refusal carries no hidden detail", denied_other is not None
      and not any(m in repr(denied_other.args) + repr(getattr(denied_other, "__dict__", {})) for m in OTHER_MARKERS))
cross = raised(errors.AuthorizationError,
               lambda: env.evidence.get_account_by_id(s["agent"], CASE, "SYN-ACCT-0099"))
check("own case plus another customer's account id is refused", cross is not None)
check("and that refusal is the same generic text", cross is not None and str(cross) == str(denied_other))
check("own case plus own account id works",
      env.evidence.get_account_by_id(s["agent"], CASE, ACCOUNT).account_id == ACCOUNT)
check("the other agent reads its own case", env.evidence.get_account(s["other_agent"], "SYN-CASE-4099").account_id
      == "SYN-ACCT-0099")
check("and cannot read the canonical case",
      raised(errors.AuthorizationError, lambda: env.evidence.get_account(s["other_agent"], CASE)) is not None)
check("nothing served for one case mentions the other",
      not any(m in repr((account, bills, reads, events, diags)) for m in OTHER_MARKERS))
check("an agent principal must be scoped to exactly one case",
      raised(errors.ValidationError, lambda: auth.Principal("agent-wide", auth.Role.AGENT, (CASE, "SYN-CASE-4099")))
      is not None
      and raised(errors.ValidationError, lambda: auth.Principal("agent-none", auth.Role.AGENT, ())) is not None)
check("an auditor cannot read evidence",
      raised(errors.AuthorizationError, lambda: env.evidence.get_billing_records(s["auditor"], CASE)) is not None)
check("an agent cannot read the audit record",
      raised(errors.AuthorizationError, lambda: env.audit.records(s["agent"], CASE)) is not None)
check("an agent cannot send a customer message",
      raised(errors.AuthorizationError, lambda: env.crm.send_message(s["agent"], contracts.OutboundMessage(
          CASE, "msg-agent-0001", "hello", True))) is not None)
check("an agent cannot assign a human review",
      raised(errors.AuthorizationError, lambda: env.review.assign_review(s["agent"], contracts.ReviewAssignment(
          CASE, "Billing Supervisor", "open meter allegation", "decision-card-4003", "rev-agent-0001"))) is not None)

# --------------------------------------------------------------------------
print("\n5. INPUT VALIDATION AT THE BOUNDARY")
BAD_CASE_IDS = ("", " ", "SYN-CASE-403", "SYN-CASE-40033", "syn-case-4003", "SYN-CASE-4003 ", "CASE-4003",
                "SYN-CASE-4003; DROP TABLE", "../SYN-CASE-4003", "SYN-CASE-4003\n", "SYN-CASE-40O3", None, 4003,
                "REAL-CUSTOMER-1")
check("every malformed case id is rejected before any lookup",
      all(raised(errors.ValidationError, lambda c=c: env.evidence.get_billing_records(s["agent"], c)) is not None
          for c in BAD_CASE_IDS))
check("a malformed account id is rejected",
      all(raised(errors.ValidationError, lambda a=a: env.evidence.get_account_by_id(s["agent"], CASE, a)) is not None
          for a in ("", "ACCT-0003", "SYN-ACCT-3", "SYN-ACCT-0003x", None, "12345678")))
check("validation does not echo the rejected value",
      "DROP" not in str(raised(errors.ValidationError,
                               lambda: env.evidence.get_billing_records(s["agent"], "SYN-CASE-4003; DROP TABLE"))))
check("authentication is checked before validation",
      raised(errors.AuthenticationError, lambda: env.evidence.get_billing_records("nope", "garbage")) is not None)
check("a principal id must be well formed",
      all(raised(errors.ValidationError, lambda p=p: auth.Principal(p, auth.Role.AGENT, (CASE,))) is not None
          for p in ("", "A", "has space", "x" * 80, None)))
check("an idempotency key must be well formed",
      all(raised(errors.ValidationError, lambda k=k: contracts.OutboundMessage(CASE, k, "body", True)) is not None
          for k in ("", "short", "has space in it", None, "k" * 200)))
check("an empty customer message is rejected",
      raised(errors.ValidationError, lambda: contracts.OutboundMessage(CASE, "msg-empty-0001", "   ", True))
      is not None)
check("a store refuses data that is not labelled synthetic",
      raised(errors.ValidationError,
             lambda: sa.build_store([dict(CANONICAL, data_classification="PRODUCTION")])) is not None)
check("a store refuses a case id outside the synthetic pattern",
      raised(errors.ValidationError, lambda: sa.build_store([dict(CANONICAL, case_id="CASE-1")])) is not None)
check("a store refuses two cases with the same id",
      raised(errors.ValidationError, lambda: sa.build_store([CANONICAL, CANONICAL])) is not None)

# --------------------------------------------------------------------------
print("\n6. TIMEOUT HANDLING, INJECTED CLOCK, NO SLEEPING")
tclock = FakeClock()


def slow_read(seconds, value="late"):
    def _op():
        tclock.advance(seconds)
        return value
    return _op


check("a call inside its deadline returns its value",
      reliability.with_deadline(slow_read(0.2, "ok"), tclock, 2.0) == "ok")
late = raised(errors.TimeoutExceeded, lambda: reliability.with_deadline(slow_read(5.0), tclock, 2.0))
check("a call past its deadline raises, and its late result is discarded", late is not None)
check("the timeout names the budget, not the data", late is not None and "2" in str(late) and "late" not in str(late))
check("a zero or negative budget is refused up front",
      all(raised(errors.ValidationError, lambda b=b: reliability.with_deadline(slow_read(0), tclock, b)) is not None
          for b in (0, -1, None)))
check("an error inside the call is not turned into a timeout",
      raised(errors.AuthorizationError,
             lambda: reliability.with_deadline(lambda: env.evidence.get_account(s["auditor"], CASE), tclock, 2.0))
      is not None)

# --------------------------------------------------------------------------
print("\n7. IDEMPOTENCY")
env = environment()
s = sessions(env)
message = contracts.OutboundMessage(CASE, "msg-4003-final-0001", "Your register moved 870 kWh.", True)
first = env.crm.send_message(s["workflow"], message)
second = env.crm.send_message(s["workflow"], message)
check("the same key and payload returns the first receipt", first == second and first.accepted is True)
check("and the customer got one message, not two", len(env.crm.get_sent_messages(s["workflow"], CASE)) == 1)
check("the same key with a different payload is refused",
      raised(errors.IdempotencyConflict, lambda: env.crm.send_message(
          s["workflow"], contracts.OutboundMessage(CASE, "msg-4003-final-0001", "A different message.", True)))
      is not None)
check("still exactly one message after the conflict", len(env.crm.get_sent_messages(s["workflow"], CASE)) == 1)
check("a message compliance did not approve is never sent",
      raised(errors.ValidationError, lambda: env.crm.send_message(
          s["workflow"], contracts.OutboundMessage(CASE, "msg-4003-unapproved", "Your meter is broken.", False)))
      is not None and len(env.crm.get_sent_messages(s["workflow"], CASE)) == 1)
assignment = contracts.ReviewAssignment(CASE, "Billing Supervisor", "open meter allegation",
                                        "decision-card-4003", "rev-4003-0001")
a1 = env.review.assign_review(s["workflow"], assignment)
a2 = env.review.assign_review(s["workflow"], assignment)
check("a repeated review assignment creates one work item", a1 == a2
      and len(env.review.get_assignments(s["workflow"], CASE)) == 1 and a1.status == "PENDING_HUMAN_REVIEW")
check("the CRM adapter satisfies the CRM port and the review adapter the review port",
      isinstance(env.crm, ports.CrmPort) and isinstance(env.review, ports.ReviewAssignmentPort))
ledger = reliability.IdempotencyLedger()
l1, r1 = ledger.remember("key-0000-0001", "fingerprint-a", "result-a")
check("the ledger returns a new ledger and leaves the old one unchanged",
      l1 is not ledger and ledger.lookup("key-0000-0001", "fingerprint-a") is None and r1 == "result-a")
check("the ledger replays the first result", l1.lookup("key-0000-0001", "fingerprint-a") == "result-a")
check("the ledger refuses a changed payload under a used key",
      raised(errors.IdempotencyConflict, lambda: l1.lookup("key-0000-0001", "fingerprint-b")) is not None)

# --------------------------------------------------------------------------
print("\n8. SAFE RETRY")
naps = []
attempts = {"n": 0}


def flaky_read():
    attempts["n"] += 1
    if attempts["n"] < 3:
        raise errors.TransientError("dependency unavailable")
    return "evidence"


read_op = reliability.Operation("get_billing_records", reliability.OperationKind.READ, flaky_read)
check("a transient read failure is retried until it succeeds",
      reliability.run_with_retry(read_op, 3, naps.append) == "evidence" and attempts["n"] == 3)
check("it backs off between attempts, through the injected sleeper only", len(naps) == 2 and naps[1] > naps[0] > 0)
attempts["n"] = -10
check("attempts are bounded, then the last error surfaces",
      raised(errors.TransientError, lambda: reliability.run_with_retry(read_op, 3, naps.append)) is not None
      and attempts["n"] == -7)
check("the attempt count itself is capped",
      raised(errors.ValidationError, lambda: reliability.run_with_retry(read_op, 50, naps.append)) is not None
      and raised(errors.ValidationError, lambda: reliability.run_with_retry(read_op, 0, naps.append)) is not None)
calls = {"write": 0, "authz": 0, "denied": 0}


def counting(key, exc=None):
    def _op():
        calls[key] += 1
        if exc:
            raise exc
        return key
    return _op


check("a write is never retried",
      raised(errors.RetryNotAllowed, lambda: reliability.run_with_retry(
          reliability.Operation("send_message", reliability.OperationKind.WRITE, counting("write")), 3, naps.append))
      is not None and calls["write"] == 0)
check("an authorization is never retried",
      raised(errors.RetryNotAllowed, lambda: reliability.run_with_retry(
          reliability.Operation("authorize_adjustment", reliability.OperationKind.AUTHORIZATION, counting("authz")),
          2, naps.append)) is not None and calls["authz"] == 0)
check("a write may run once through the same wrapper",
      reliability.run_with_retry(reliability.Operation("send_message", reliability.OperationKind.WRITE,
                                                       counting("write")), 1, naps.append) == "write"
      and calls["write"] == 1)
check("a refusal is not retried, because trying again will not make it allowed",
      raised(errors.AuthorizationError, lambda: reliability.run_with_retry(
          reliability.Operation("get_account", reliability.OperationKind.READ,
                                counting("denied", errors.AuthorizationError())), 3, naps.append)) is not None
      and calls["denied"] == 1)

# --------------------------------------------------------------------------
print("\n9. ONLY A HUMAN BILLING SUPERVISOR CAN AUTHORIZE MONEY")
env = environment()
s = sessions(env)
adj = env.adjustments
APPROVED, DENIED = contracts.AdjustmentDecision.APPROVED, contracts.AdjustmentDecision.DENIED
expected_public = {"request_adjustment", "authorize_adjustment", "get_pending_requests", "get_authorizations"}
check("the adjustment adapter exposes exactly the reviewed methods",
      {n for n in dir(adj) if not n.startswith("_")} == expected_public,
      str(sorted(n for n in dir(adj) if not n.startswith("_"))))
check("it satisfies the adjustment port", isinstance(adj, ports.AdjustmentAuthorizationPort))
request = adj.request_adjustment(s["reviewer"], CASE, ACCOUNT, Decimal("25.00"),
                                 "on-site inspection confirmed a register fault", "adj-4003-req-0001")
check("a human reviewer can request an adjustment, and it is only a request",
      request.requested_by == "human-reviewer-01" and len(adj.get_authorizations(s["supervisor"], CASE)) == 0)

agent_attempts = {
    "request": lambda: adj.request_adjustment(s["agent"], CASE, ACCOUNT, Decimal("25.00"), "agent says so",
                                              "adj-4003-agent-0001"),
    "authorize": lambda: adj.authorize_adjustment(s["agent"], request.request_id, APPROVED, "agent approves"),
    "list pending": lambda: adj.get_pending_requests(s["agent"], CASE),
    "list authorizations": lambda: adj.get_authorizations(s["agent"], CASE),
}
for label, attempt in agent_attempts.items():
    check("agent refused: %s" % label, raised(errors.AuthorizationError, attempt) is not None)
check("the workflow service cannot request or authorize either",
      raised(errors.AuthorizationError, lambda: adj.authorize_adjustment(s["workflow"], request.request_id,
                                                                         APPROVED, "x")) is not None
      and raised(errors.AuthorizationError, lambda: adj.request_adjustment(
          s["workflow"], CASE, ACCOUNT, Decimal("1.00"), "x", "adj-4003-wf-0001")) is not None)
check("a human reviewer cannot authorize",
      raised(errors.AuthorizationError, lambda: adj.authorize_adjustment(s["reviewer"], request.request_id,
                                                                         APPROVED, "x")) is not None)
check("an auditor cannot authorize",
      raised(errors.AuthorizationError, lambda: adj.authorize_adjustment(s["auditor"], request.request_id,
                                                                         APPROVED, "x")) is not None)

# Forgery. A role is an enum member resolved from a session the identity
# provider issued. A string, a made-up enum value or a hand-built principal
# gets nowhere.
check("a role given as a string is rejected when the principal is built",
      raised(errors.ValidationError, lambda: auth.Principal("agent-forger", "HUMAN_BILLING_SUPERVISOR", (CASE,)))
      is not None)
check("a role that is not a member of Role is rejected",
      raised(errors.ValidationError, lambda: auth.Principal("agent-forger", object(), (CASE,))) is not None)
forged = auth.Principal("agent-forger", auth.Role.HUMAN_BILLING_SUPERVISOR, (CASE,))
check("a hand-built supervisor principal that was never issued a session is refused",
      raised(errors.AuthenticationError, lambda: adj.authorize_adjustment(forged, request.request_id, APPROVED, "x"))
      is not None)
agent_principal = env.identity.resolve(s["agent"])
check("a resolved principal is frozen, so its role cannot be changed afterwards",
      raised(dataclasses.FrozenInstanceError,
             lambda: setattr(agent_principal, "role", auth.Role.HUMAN_BILLING_SUPERVISOR)) is not None)
check("the role to permission table cannot be edited at run time",
      raised(TypeError, lambda: auth.ROLE_PERMISSIONS.__setitem__(
          auth.Role.AGENT, frozenset({auth.Permission.AUTHORIZE_ADJUSTMENT}))) is not None)
check("the agent role holds exactly one permission, reading evidence",
      auth.ROLE_PERMISSIONS[auth.Role.AGENT] == frozenset({auth.Permission.READ_EVIDENCE}))
check("only the supervisor role holds the authorize permission",
      [r for r in auth.Role if auth.Permission.AUTHORIZE_ADJUSTMENT in auth.ROLE_PERMISSIONS[r]]
      == [auth.Role.HUMAN_BILLING_SUPERVISOR])
check("a token string that merely looks privileged is refused",
      raised(errors.AuthenticationError, lambda: adj.authorize_adjustment("HUMAN_BILLING_SUPERVISOR",
                                                                          request.request_id, APPROVED, "x"))
      is not None)
check("after every attempt above, nothing has been authorized",
      adj.get_authorizations(s["supervisor"], CASE) == ()
      and [r.request_id for r in adj.get_pending_requests(s["supervisor"], CASE)] == [request.request_id])

# Four eyes.
own = adj.request_adjustment(s["supervisor"], CASE, ACCOUNT, Decimal("10.00"), "supervisor's own request",
                             "adj-4003-sup-0001")
check("a supervisor cannot approve their own request",
      raised(errors.FourEyesViolation, lambda: adj.authorize_adjustment(s["supervisor"], own.request_id,
                                                                        APPROVED, "self")) is not None)
check("a second supervisor can", adj.authorize_adjustment(s["supervisor2"], own.request_id, APPROVED,
                                                         "reviewed the inspection report").approved_by
      == "human-supervisor-02")
authorization = adj.authorize_adjustment(s["supervisor"], request.request_id, APPROVED, "inspection report attached")
check("a supervisor authorizes another person's request",
      (authorization.approved_by, authorization.requested_by, authorization.decision, authorization.amount_usd)
      == ("human-supervisor-01", "human-reviewer-01", APPROVED, Decimal("25.00")))
check("repeating the identical decision returns the first authorization",
      adj.authorize_adjustment(s["supervisor"], request.request_id, APPROVED, "inspection report attached")
      == authorization and len(adj.get_authorizations(s["supervisor"], CASE)) == 2)
check("a decided request cannot be decided again differently",
      raised(errors.AlreadyDecided, lambda: adj.authorize_adjustment(s["supervisor2"], request.request_id,
                                                                     DENIED, "changed my mind")) is not None)
check("an unknown request id is refused without detail",
      raised(errors.AuthorizationError, lambda: adj.authorize_adjustment(s["supervisor"], "ADJ-9999", APPROVED, "x"))
      is not None)
check("amounts are validated: positive, decimal, within the per-request ceiling",
      all(raised(errors.ValidationError, lambda a=a: adj.request_adjustment(
          s["reviewer"], CASE, ACCOUNT, a, "reason", "adj-4003-bad-%04d" % i)) is not None
          for i, a in enumerate((Decimal("0"), Decimal("-5"), 25.0, "25.00", None, Decimal("1000000"),
                                 Decimal("1.234")))))
check("a request must name the case's own account",
      raised(errors.AuthorizationError, lambda: adj.request_adjustment(
          s["reviewer"], CASE, "SYN-ACCT-0099", Decimal("5.00"), "wrong customer", "adj-4003-cross-0001"))
      is not None)
check("a repeated request under the same key is one request",
      adj.request_adjustment(s["reviewer"], CASE, ACCOUNT, Decimal("25.00"),
                             "on-site inspection confirmed a register fault", "adj-4003-req-0001") == request)
check("an authorization records a decision and changes no billing record",
      env.evidence.get_billing_records(s["supervisor"], CASE) == bills)
check("no adapter has a method that applies money to an account",
      not any(n.split("_")[0] in ("apply", "post", "credit", "refund", "pay")
              for a in (env.evidence, env.crm, env.review, env.adjustments, env.audit)
              for n in dir(a) if not n.startswith("_")))

# --------------------------------------------------------------------------
print("\n10. AUDIT INTEGRITY")
chain = env.audit.records(s["auditor"], CASE)
actions = [r.action for r in chain]
check("requests, the refused self-approval and the authorizations were all recorded",
      actions.count("ADJUSTMENT_REQUESTED") == 2 and actions.count("ADJUSTMENT_AUTHORIZED") == 2
      and "ADJUSTMENT_REFUSED_FOUR_EYES" in actions, str(actions))
check("refused attempts by the agent were recorded too",
      any(r.action == "ADJUSTMENT_REFUSED" and r.actor == "agent-account-evidence" for r in chain))
check("the actor comes from the session, never from the caller",
      {r.actor for r in chain} <= {"agent-account-evidence", "workflow-gridresolve", "human-reviewer-01",
                                   "human-supervisor-01", "human-supervisor-02", "human-auditor-01"})
check("the chain verifies", audit_store.verify_chain(chain) is True and env.audit.verify(s["auditor"], CASE) is True)
check("sequence numbers are contiguous from one", [r.sequence for r in chain] == list(range(1, len(chain) + 1)))
check("each record points at the hash before it",
      all(chain[i].previous_hash == chain[i - 1].record_hash for i in range(1, len(chain)))
      and chain[0].previous_hash == audit_store.GENESIS_HASH)
edited = chain[:1] + (dataclasses.replace(chain[1], detail="nothing happened"),) + chain[2:]
check("editing a record is detected", audit_store.verify_chain(edited) is False)
check("deleting a record is detected", audit_store.verify_chain(chain[:1] + chain[2:]) is False)
check("reordering records is detected", audit_store.verify_chain((chain[1], chain[0]) + chain[2:]) is False)
rehashed = dataclasses.replace(chain[1], detail="nothing happened")
rehashed = dataclasses.replace(rehashed, record_hash=audit_store.hash_record(rehashed))
check("editing a record and recomputing its own hash is still detected by the next link",
      audit_store.verify_chain(chain[:1] + (rehashed,) + chain[2:]) is False)
check("the store has no way to delete, update or replace a record",
      not any(w in n for n in dir(env.audit) if not n.startswith("_")
              for w in ("delete", "update", "remove", "replace", "clear", "truncate", "edit")),
      str([n for n in dir(env.audit) if not n.startswith("_")]))
check("a served audit record is frozen",
      raised(dataclasses.FrozenInstanceError, lambda: setattr(chain[0], "detail", "x")) is not None)
before = len(chain)
env.audit.append(s["workflow"], CASE, "CASE_AUDIT_WRITTEN", "terminal audit persisted")
after = env.audit.records(s["auditor"], CASE)
check("appending adds one record and leaves earlier ones identical",
      len(after) == before + 1 and after[:before] == chain and audit_store.verify_chain(after))
check("an agent cannot append to the audit record",
      raised(errors.AuthorizationError, lambda: env.audit.append(s["agent"], CASE, "X", "y")) is not None)
check("audit records are scoped by case",
      raised(errors.AuthorizationError, lambda: env.audit.records(s["auditor"], "SYN-CASE-4099")) is not None)
check("audit detail never holds a session token", not any(tok in repr(after) for tok in s.values()))
check("the audit store satisfies the audit port", isinstance(env.audit, ports.AuditStorePort))

# --------------------------------------------------------------------------
print("\n11. PACKAGE HYGIENE")
package_dir = os.path.join(ROOT, "integration")
sources = {n: open(os.path.join(package_dir, n), encoding="utf-8").read()
           for n in sorted(os.listdir(package_dir)) if n.endswith((".py", ".md"))}
check("the package has its contracts, ports, auth, adapters and README",
      {"contracts.py", "ports.py", "auth.py", "synthetic_adapters.py", "README.md"} <= set(sources))
check("no em dash or en dash anywhere in the package or this test",
      not any(chr(0x2014) in t or chr(0x2013) in t for t in list(sources.values()) + [open(__file__, encoding="utf-8").read()]))
check("no network or subprocess module is imported",
      not any(re.search(r"^\s*(import|from)\s+(urllib|http|socket|requests|subprocess|ssl|smtplib|ftplib|asyncio)\b",
                        t, re.M) for n, t in sources.items() if n.endswith(".py")))
check("standard library only",
      all(re.match(r"(from\s+\.|from\s+(integration|__future__|dataclasses|decimal|enum|typing|types|hashlib|json|os|re|"
                   r"secrets|time|datetime)\b|import\s+(dataclasses|hashlib|json|os|re|secrets|time|datetime)\b)", ln)
          for n, t in sources.items() if n.endswith(".py")
          for ln in t.splitlines() if re.match(r"(import|from)\s", ln)))
check("every file is under 400 lines", all(t.count("\n") < 400 for t in sources.values()),
      str({n: t.count("\n") for n, t in sources.items()}))
check("no tenant identifier, key or token is present",
      not any(re.search(r"(services\.ai\.azure\.com/api/projects/[a-z]|Bearer\s+ey|api[_-]?key\s*=\s*['\"])", t)
              for t in sources.values()))
readme = sources.get("README.md", "")
check("the README says plainly that nothing real is connected or deployed",
      all(p in readme for p in ("synthetic", "not connected", "not deployed", "Entra ID", "system of record")),
      "checked five phrases")

print("\n" + "=" * 92)
print("RESULT: %d passed, %d failed" % (len(passes), len(failures)))
print("=" * 92)
if failures:
    for name, detail in failures:
        print("  FAILED: %s %s" % (name, detail))
print("Local synthetic adapters only. No real utility, meter, CRM or identity system is connected.")
sys.exit(1 if failures else 0)
