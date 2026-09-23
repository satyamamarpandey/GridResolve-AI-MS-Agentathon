"""
Supervisor feedback loop, exercised against the local synthetic identity provider
and audit chain. No network, no Azure call, no model call, no cost.

Every record here is built by this harness with a fixed clock. The records marked
ACTUAL_HUMAN_REVIEW are test fixtures standing in for a real decision so that the
metric arithmetic can be checked; no real supervisor has reviewed anything.

Run: python tests/test_supervisor_feedback.py
"""
import dataclasses
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

passes = []
failures = []


def check(name, cond, detail=""):
    (passes if cond else failures).append((name, detail))
    print("  [%s] %-74s %s" % ("PASS" if cond else "FAIL", name, detail))


def raised(exc_type, fn):
    try:
        fn()
    except exc_type as exc:
        return exc
    except Exception as exc:
        print("      unexpected %s: %s" % (type(exc).__name__, exc))
        return None
    return None


try:
    from integration import audit_store, auth, errors
    from integration import supervisor_feedback as sf
except ImportError as exc:
    print("integration package is not importable: %s" % exc)
    print("\nRESULT: 0 passed, 1 failed")
    sys.exit(1)


class FakeClock:
    def __init__(self, start=1_800_000_000.0):
        self.value = start

    def now(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


CASE = "SYN-CASE-4003"
OTHER = "SYN-CASE-4001"
clock = FakeClock()
# Reviews advance the clock by minutes, so sessions here outlive the default TTL.
identity = auth.SyntheticIdentityProvider(clock, ttl_seconds=86_400.0)
guard = auth.AccessGuard(identity)
audit = audit_store.AuditLog(clock)
store = sf.SupervisorFeedbackStore(guard, audit)

supervisor = identity.issue(auth.Principal("human-supervisor-01", auth.Role.HUMAN_BILLING_SUPERVISOR, (CASE, OTHER)))
reviewer = identity.issue(auth.Principal("human-reviewer-02", auth.Role.HUMAN_REVIEWER, (CASE,)))
agent = identity.issue(auth.Principal("agent-planner", auth.Role.AGENT, (CASE,)))
service = identity.issue(auth.Principal("workflow-service", auth.Role.WORKFLOW_SERVICE, (CASE,)))
auditor = identity.issue(auth.Principal("auditor-03", auth.Role.AUDITOR, (CASE,)))

ACTUAL = sf.RecordKind.ACTUAL_HUMAN_REVIEW
SIM = sf.RecordKind.OFFLINE_SIMULATION
ROLE = "Billing Supervisor"


def stamps(seconds):
    """A start stamp now and a completion stamp `seconds` later, on the fixed clock."""
    start = sf.utc_stamp(clock)
    clock.advance(seconds)
    return start, sf.utc_stamp(clock)


def record(session, ref, recommendation, decision, kind, override="", case=CASE, seconds=90.0, **kw):
    start, end = stamps(seconds)
    return store.record(session, case, ref, recommendation, decision, start, end,
                        kw.pop("disposition", "PENDING_HUMAN_REVIEW"), kw.pop("role", ROLE), kind,
                        override_reason=override, reviewer_comments=kw.pop("comments", ""))


# --------------------------------------------------------------------------
print("\n1. AGREEMENT AND DISAGREEMENT")
r1 = record(supervisor, "wfresp_sim_run_2", "ESCALATED_TO_HUMAN", "ESCALATED_TO_HUMAN", SIM,
            comments="simulated fixture")
check("a matching decision is recorded as AGREE", r1.agreement is sf.Agreement.AGREE)
check("the record carries the reviewer principal from the session, not an argument",
      r1.reviewer_principal_id == "human-supervisor-01")
check("the record kind is a field on the record", r1.record_kind is SIM)
check("the duration is measured from the two timestamps", r1.review_duration_seconds == 90.0,
      r1.duration_note)
check("the record is immutable",
      raised(dataclasses.FrozenInstanceError, lambda: setattr(r1, "human_decision", "x")) is not None)

r2 = record(supervisor, "wfresp_sim_run_1", "APPROVED_AND_RELEASED", "REJECT_DRAFT", SIM,
            override="The draft asserted a meter condition without a diagnostic result.")
check("a differing decision is recorded as DISAGREE", r2.agreement is sf.Agreement.DISAGREE)
check("the override reason is kept", "diagnostic" in r2.override_reason)
check("agreement is derived, never supplied: casing and spacing do not matter",
      sf.derive_agreement(" approve ", "APPROVE") is sf.Agreement.AGREE)
check("a disagreement without an override reason is refused",
      raised(sf.MissingOverrideReason,
             lambda: record(supervisor, "wfresp_sim_x1", "APPROVE", "REJECT", SIM)) is not None)
check("a blank override reason counts as missing",
      raised(sf.MissingOverrideReason,
             lambda: record(supervisor, "wfresp_sim_x2", "APPROVE", "REJECT", SIM, override="   ")) is not None)

# --------------------------------------------------------------------------
print("\n2. MISSING DECISION AND TIMESTAMPS")
start, end = stamps(10.0)
check("a missing human decision is refused",
      raised(sf.MissingDecision, lambda: store.record(
          supervisor, CASE, "wfresp_sim_x3", "APPROVE", "", start, end, "PENDING", ROLE, SIM)) is not None)
check("a whitespace decision is refused",
      raised(sf.MissingDecision, lambda: store.record(
          supervisor, CASE, "wfresp_sim_x3", "APPROVE", "  ", start, end, "PENDING", ROLE, SIM)) is not None)
check("a missing agent recommendation is refused",
      raised(sf.MissingDecision, lambda: store.record(
          supervisor, CASE, "wfresp_sim_x3", "", "APPROVE", start, end, "PENDING", ROLE, SIM)) is not None)
check("a missing start timestamp is refused",
      raised(sf.MissingTimestamp, lambda: store.record(
          supervisor, CASE, "wfresp_sim_x3", "APPROVE", "APPROVE", "", end, "PENDING", ROLE, SIM)) is not None)
check("a missing completion timestamp is refused",
      raised(sf.MissingTimestamp, lambda: store.record(
          supervisor, CASE, "wfresp_sim_x3", "APPROVE", "APPROVE", start, None, "PENDING", ROLE, SIM)) is not None)
check("a timestamp that is not ISO 8601 is refused",
      raised(errors.ValidationError, lambda: store.record(
          supervisor, CASE, "wfresp_sim_x3", "APPROVE", "APPROVE", "yesterday", end, "PENDING", ROLE, SIM)) is not None)
check("a naive timestamp without a UTC offset is refused",
      raised(errors.ValidationError, lambda: store.record(
          supervisor, CASE, "wfresp_sim_x3", "APPROVE", "APPROVE", "2026-09-23T10:00:00", end, "PENDING", ROLE, SIM)) is not None)
check("completion before start is refused",
      raised(sf.TimestampOrder, lambda: store.record(
          supervisor, CASE, "wfresp_sim_x3", "APPROVE", "APPROVE", end, start, "PENDING", ROLE, SIM)) is not None)
check("nothing was recorded by any refused call", len(store.records_for(supervisor, CASE)) == 2)
same = sf.utc_stamp(clock)
r0 = store.record(supervisor, CASE, "wfresp_sim_zero", "APPROVE", "APPROVE", same, same, "PENDING", ROLE, SIM)
check("a zero-length review is allowed and measures zero seconds", r0.review_duration_seconds == 0.0)

# --------------------------------------------------------------------------
print("\n3. DUPLICATE FEEDBACK")
check("a second record for the same case and package is refused",
      raised(sf.DuplicateFeedback,
             lambda: record(supervisor, "wfresp_sim_run_2", "ESCALATED_TO_HUMAN", "APPROVE", SIM,
                            override="second opinion")) is not None)
check("a duplicate from a different reviewer is refused too",
      raised(sf.DuplicateFeedback,
             lambda: record(reviewer, "wfresp_sim_run_2", "ESCALATED_TO_HUMAN", "ESCALATED_TO_HUMAN", SIM)) is not None)
check("the first record is unchanged after the duplicate attempt",
      store.records_for(supervisor, CASE)[0] == r1)
r3 = record(reviewer, "wfresp_sim_run_3", "APPROVED_AND_RELEASED", "APPROVED_AND_RELEASED", SIM,
            role="Compliance Reviewer")
check("the same package ref under another case id is a different record",
      record(supervisor, "wfresp_sim_run_3", "APPROVE", "APPROVE", SIM, case=OTHER).case_id == OTHER)

# --------------------------------------------------------------------------
print("\n4. UNAUTHORIZED DECISIONS")
before = len(audit.records_for(CASE))
check("an agent principal cannot record a human decision",
      raised(errors.AuthorizationError,
             lambda: record(agent, "wfresp_sim_a1", "APPROVE", "APPROVE", ACTUAL)) is not None)
check("the workflow service cannot record a human decision",
      raised(errors.AuthorizationError,
             lambda: record(service, "wfresp_sim_s1", "APPROVE", "APPROVE", ACTUAL)) is not None)
check("an auditor cannot record a human decision",
      raised(errors.AuthorizationError,
             lambda: record(auditor, "wfresp_sim_u1", "APPROVE", "APPROVE", ACTUAL)) is not None)
check("a reviewer cannot record on a case outside their scope",
      raised(errors.AuthorizationError,
             lambda: record(reviewer, "wfresp_sim_o1", "APPROVE", "APPROVE", SIM, case=OTHER)) is not None)
check("a missing session is refused",
      raised(errors.AuthenticationError,
             lambda: record(None, "wfresp_sim_n1", "APPROVE", "APPROVE", SIM)) is not None)
check("a made-up token is refused",
      raised(errors.AuthenticationError,
             lambda: record("not-a-token", "wfresp_sim_n2", "APPROVE", "APPROVE", SIM)) is not None)
refusals = [r for r in audit.records_for(CASE)[before:] if r.action == sf.AUDIT_ACTION_REFUSED]
check("each authorised-but-forbidden attempt is written to the audit chain as a refusal",
      len(refusals) == 3, "%d refusals" % len(refusals))
check("the refusal names the principal that tried",
      {r.actor for r in refusals} == {"agent-planner", "workflow-service", "auditor-03"})
check("a role string in the record must be a known review role",
      raised(errors.ValidationError,
             lambda: record(supervisor, "wfresp_sim_r1", "APPROVE", "APPROVE", SIM, role="Chief Executive")) is not None)
check("an agent cannot read the review records either",
      raised(errors.AuthorizationError, lambda: store.records_for(agent, CASE)) is not None)
check("only the RECORD_REVIEW permission holders are human review roles",
      sorted(r.value for r in auth.Role if auth.Permission.RECORD_REVIEW in auth.ROLE_PERMISSIONS[r])
      == ["HUMAN_BILLING_SUPERVISOR", "HUMAN_REVIEWER"])

# --------------------------------------------------------------------------
print("\n5. AUDIT COMPLETENESS")
chain = audit.records_for(CASE)
check("the audit chain verifies after every record and refusal", audit_store.verify_chain(chain))
entries = sf.audit_entries_for(chain, CASE)
accepted = store.records_for(supervisor, CASE)
check("every accepted record has exactly one audit entry", len(entries) == len(accepted),
      "%d entries for %d records" % (len(entries), len(accepted)))
check("the audit actor is the reviewer who recorded",
      sorted(e.actor for e in entries) == sorted(r.reviewer_principal_id for r in accepted))
check("the audit detail names the package, the decision, the agreement and the kind",
      all(any(r.evidence_package_ref in e.detail and r.human_decision in e.detail
              and r.agreement.value in e.detail and r.record_kind.value in e.detail for e in entries)
          for r in accepted))
check("the audit action passes the audit action pattern",
      all(e.action == sf.AUDIT_ACTION_RECORDED for e in entries) and
      __import__("integration.validation", fromlist=["AUDIT_ACTION"]).AUDIT_ACTION.fullmatch(sf.AUDIT_ACTION_RECORDED))
check("an edited audit entry is detected",
      not audit_store.verify_chain(chain[:1] + (dataclasses.replace(chain[1], detail="edited"),) + chain[2:]))
check("the store has no method that changes or drops a record",
      not any(n.startswith(("delete", "remove", "update", "edit", "clear")) for n in dir(store)))
check("records returned to a caller are tuples of frozen records",
      isinstance(accepted, tuple) and all(dataclasses.is_dataclass(r) for r in accepted))

# --------------------------------------------------------------------------
print("\n6. METRICS: SIMULATED ONLY")
all_visible = store.all_records(supervisor)
check("every record so far is an offline simulation",
      all(r.record_kind is SIM for r in all_visible), "%d records" % len(all_visible))
rate = sf.override_rate(all_visible)
check("the override rate is NOT MEASURED with only simulated records", isinstance(rate, sf.NotMeasured))
check("the not-measured result counts the simulated records separately",
      rate.actual_records == 0 and rate.simulated_records == len(all_visible))
check("the not-measured result says why", "No actual human decision" in rate.reason)
reduction = sf.review_time_reduction(all_visible)
check("review-time reduction is NOT MEASURED without a baseline", isinstance(reduction, sf.NotMeasured)
      and "baseline" in reduction.reason)
baseline = sf.ReviewTimeBaseline("synthetic fixture, not a measured baseline", sf.utc_stamp(clock), 5, 600.0)
reduction2 = sf.review_time_reduction(all_visible, baseline)
check("review-time reduction is NOT MEASURED with a baseline but no actual timed review",
      isinstance(reduction2, sf.NotMeasured) and "Simulated durations are never used" in reduction2.reason)
check("a baseline without provenance cannot be built",
      raised(errors.ValidationError, lambda: sf.ReviewTimeBaseline("", sf.utc_stamp(clock), 5, 600.0)) is not None
      and raised(errors.ValidationError, lambda: sf.ReviewTimeBaseline("src", "", 5, 600.0)) is not None
      and raised(errors.ValidationError, lambda: sf.ReviewTimeBaseline("src", sf.utc_stamp(clock), 0, 600.0)) is not None
      and raised(errors.ValidationError, lambda: sf.ReviewTimeBaseline("src", sf.utc_stamp(clock), 5, 0.0)) is not None)
check("a baseline that is not a ReviewTimeBaseline is refused",
      raised(errors.ValidationError, lambda: sf.review_time_reduction(all_visible, {"mean": 600})) is not None)

# --------------------------------------------------------------------------
print("\n7. METRICS: ACTUAL RECORDS (harness fixtures standing in for real decisions)")
a1 = record(supervisor, "fixture_actual_1", "ESCALATED_TO_HUMAN", "ESCALATED_TO_HUMAN", ACTUAL, seconds=120.0)
a2 = record(supervisor, "fixture_actual_2", "APPROVED_AND_RELEASED", "REJECT_DRAFT", ACTUAL, seconds=240.0,
            override="Fixture override: the draft promised a callback the plan did not support.")
a3 = record(reviewer, "fixture_actual_3", "ESCALATED_TO_HUMAN", "ESCALATED_TO_HUMAN", ACTUAL, seconds=60.0,
            role="Compliance Reviewer")
mixed = store.all_records(supervisor)
rate2 = sf.override_rate(mixed)
check("the override rate is measured once actual records exist", isinstance(rate2, sf.OverrideRate))
check("the rate is overrides over actual records only", rate2.actual_records == 3 and rate2.overrides == 1
      and abs(rate2.rate - 1 / 3) < 1e-9, "rate %.3f" % rate2.rate)
check("simulated records are excluded and counted", rate2.simulated_excluded == len(all_visible))
reduction3 = sf.review_time_reduction(mixed, baseline)
check("review-time reduction is measured against the supplied baseline",
      isinstance(reduction3, sf.ReviewTimeReduction))
check("the observed mean uses only actual durations",
      reduction3.actual_records == 3 and abs(reduction3.observed_mean_seconds - 140.0) < 1e-9,
      "observed %.1f s" % reduction3.observed_mean_seconds)
check("the reduction is baseline minus observed and names the baseline source",
      abs(reduction3.reduction_seconds - 460.0) < 1e-9 and reduction3.baseline_source == baseline.source)
check("the audit chain still verifies with actual records appended",
      audit_store.verify_chain(audit.records_for(CASE)))
check("the reviewer sees only their own case's records",
      all(r.case_id == CASE for r in store.all_records(reviewer)))

# --------------------------------------------------------------------------
print("\n8. HYGIENE")
src = open(os.path.join(ROOT, "integration", "supervisor_feedback.py"), encoding="utf-8").read()
check("the module states the simulated versus actual distinction as a field", "record_kind: RecordKind" in src)
check("no em dash or en dash in the module or this test",
      not any(chr(0x2014) in t or chr(0x2013) in t for t in (src, open(__file__, encoding="utf-8").read())))
check("the module is under 400 lines", src.count("\n") < 400)

print("\n" + "=" * 92)
print("RESULT: %d passed, %d failed" % (len(passes), len(failures)))
print("=" * 92)
if failures:
    for name, detail in failures:
        print("  FAILED: %s %s" % (name, detail))
print("Local synthetic fixtures only. No real supervisor decision has been recorded.")
sys.exit(1 if failures else 0)
