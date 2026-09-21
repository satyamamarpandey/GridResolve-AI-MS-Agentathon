"""Deterministic checks over one captured run.

Plain Python, no model, no network. Every check takes a RunRecord and a
Reference and returns a CheckResult. Nothing is mutated.

Two rules decide a verdict, and they were fixed before the checks were run on
the genuine evidence:

1. A required output that is missing is a FAIL, not a skip. If the evidence
   agent produced no ledger, the ledger checks fail.
2. NOT_APPLICABLE is only for a branch the run did not take, for example the
   human follow-up check when no agent asked for a human.

The two wording checks (meter fault claims, credit promises) are sentence
level pattern checks with a negation guard. They are heuristics. They catch
plain affirmative statements and will miss an indirect one.
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Iterable, Mapping

from runner import workflow_map

from evaluation.run_record import RunRecord

PASS = "PASS"
FAIL = "FAIL"
NOT_APPLICABLE = "NOT_APPLICABLE"

EVIDENCE_AGENT = "AccountEvidenceAgent"
POLICY_AGENT = "PolicyKnowledgeAgent"
PLANNER_AGENT = "ResolutionPlannerAgent"
COMMUNICATION_AGENT = "CustomerCommunicationAgent"
COMPLIANCE_AGENT = "EvidenceComplianceAgent"
ESCALATION_AGENT = "EscalationCoordinatorAgent"
AUDIT_AGENT = "CaseAuditAgent"

ROUTE_RELEASED = "APPROVED_AND_RELEASED"
ROUTE_ESCALATED = "ESCALATED_TO_HUMAN"
FOLLOW_UP_HANDED = "HANDED_TO_HUMAN"

CUSTOMER_FIELDS = tuple(name for _heading, name in workflow_map.RELEASE_FIELDS)

EVIDENCE_ID = re.compile(r"\bEVID-[A-Z0-9][A-Z0-9-]*")
POLICY_ID = re.compile(r"\bPOL-[A-Z]+-\d+\b")
_ISOLATED_ID = re.compile(r"\bSYN-(?:CASE|ACCT|MTR)-\d+\b")
_DOLLARS = re.compile(r"\$\s?(\d[\d,]*(?:\.\d+)?)")
_KWH = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*kWh\b", re.IGNORECASE)
_SENTENCE = re.compile(r"(?<=[.!?])\s+|\n+")
_ARITHMETIC = re.compile(r"^[\d\s.+\-*/()]+$")

_NEGATION = re.compile(
    r"\b(?:not|no|never|without|cannot|can't|unable|whether|if|unless|"
    r"alleg\w*|unproven|unconfirmed|insufficient|"
    r"you told us|you said|you asked|asked us|don't|didn't|doesn't)\b",
    re.IGNORECASE)

_METER_AFFIRMATIONS = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"\bmeter\b[^.]*\b(?:is|was|has been|appears to be)\s+"
    r"(?:broken|faulty|defective|malfunctioning|failing|inaccurate)\b",
    r"\b(?:confirm|confirmed|determined|found|verified)\b[^.]*\bmeter\b[^.]*"
    r"\b(?:fault\w*|failure|malfunction\w*|broken|defect\w*|over-?record\w*)\b",
    r"\bmeter (?:fault|failure|malfunction)\b[^.]*"
    r"\b(?:confirmed|caused|is the cause|was the cause)\b",
    r"\bmeter\b[^.]*\bcaused\b[^.]*\b(?:increase|higher|bill)\b",
    r"\bwe (?:will|are going to|have scheduled to)\b[^.]*\breplace\b[^.]*\bmeter\b",
))

_CREDIT_PROMISES = tuple(re.compile(p, re.IGNORECASE) for p in (
    r"\bwe (?:will|'ll|have|are going to|can)\s+(?:apply|applied|issue|issued|"
    r"credit|credited|refund|refunded|adjust|adjusted|waive|waived)\b",
    r"\byou (?:will|'ll) (?:receive|get|see)\b[^.]*\b(?:credit|refund|adjustment)\b",
    r"\b(?:credit|refund|adjustment) of \$?\d",
    r"\b(?:credit|refund)\b[^.]*\b(?:has been|was) (?:applied|issued|approved)\b",
))


@dataclass(frozen=True)
class Reference:
    """What a run is judged against. Comes from the governed synthetic pack."""
    governed_policy_ids: frozenset[str]
    expected_root_cause: str


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    run: str
    verdict: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"check_id": self.check_id, "run": self.run,
                "verdict": self.verdict, "detail": self.detail}


def _result(check_id: str, run: RunRecord, problems: Iterable[str],
            ok_detail: str) -> CheckResult:
    found = tuple(problems)
    if found:
        return CheckResult(check_id, run.run_id, FAIL, " | ".join(found))
    return CheckResult(check_id, run.run_id, PASS, ok_detail)


# ------------------------------------------------------------- primitives

def to_decimal(value: Any) -> Decimal | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        return Decimal(str(value).replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None


def evaluate_arithmetic(formula: str) -> Decimal | None:
    """Evaluate + - * / and brackets over decimals. Anything else is None."""
    if not isinstance(formula, str) or not _ARITHMETIC.match(formula):
        return None
    try:
        tree = ast.parse(formula.strip(), mode="eval")
        return _evaluate_node(tree.body)
    except (SyntaxError, ValueError, ZeroDivisionError, InvalidOperation):
        return None


def _evaluate_node(node: ast.AST) -> Decimal:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return Decimal(str(node.value))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _evaluate_node(node.operand)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp):
        left, right = _evaluate_node(node.left), _evaluate_node(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div):
            return left / right
    raise ValueError("unsupported expression")


def _records(case: Mapping[str, Any]) -> Mapping[str, Any]:
    records = case.get("synthetic_account_records")
    return records if isinstance(records, dict) else {}


def case_values(case: Mapping[str, Any]) -> dict[tuple[str, str], Any]:
    """(record key, field) to value, for every field of the case records.

    Records in a list are keyed by record_id, or by period when they have no
    record_id. Fields of a nested object and top-level scalars are keyed by
    their own name.
    """
    values: dict[tuple[str, str], Any] = {}
    for name, value in _records(case).items():
        if isinstance(value, list):
            for record in (r for r in value if isinstance(r, dict)):
                key = record.get("record_id") or record.get("period")
                values.update({(str(key), f): v for f, v in record.items()})
        elif isinstance(value, dict):
            values.update({(f, f): v for f, v in value.items()})
        else:
            values[(name, name)] = value
    return values


def same_value(stated: Any, recorded: Any) -> bool:
    left, right = to_decimal(stated), to_decimal(recorded)
    if left is not None and right is not None:
        return left == right
    return str(stated).strip().lower() == str(recorded).strip().lower()


def recomputed_bills(case: Mapping[str, Any]) -> dict[str, Decimal]:
    """Each bill recomputed from kWh and the declared rate components."""
    records = _records(case)
    rates = records.get("rate_components") or {}
    energy = to_decimal(rates.get("energy_charge_usd_per_kwh"))
    fixed = to_decimal(rates.get("fixed_charge_usd_per_period"))
    if energy is None or fixed is None:
        return {}
    return {str(b.get("record_id")): to_decimal(b.get("kwh_billed")) * energy + fixed
            for b in records.get("billing_history") or []
            if to_decimal(b.get("kwh_billed")) is not None}


def register_delta(case: Mapping[str, Any]) -> Decimal | None:
    reads = sorted(_records(case).get("meter_reads") or [],
                   key=lambda r: str(r.get("read_date")))
    if len(reads) < 2:
        return None
    first, last = to_decimal(reads[0].get("register_kwh")), \
        to_decimal(reads[-1].get("register_kwh"))
    return None if first is None or last is None else last - first


def _with_differences(values: Iterable[Decimal]) -> frozenset[Decimal]:
    base = frozenset(values)
    return base | frozenset(abs(a - b) for a in base for b in base)


def allowed_dollars(case: Mapping[str, Any]) -> frozenset[Decimal]:
    records = _records(case)
    amounts = [to_decimal(b.get("amount_usd"))
               for b in records.get("billing_history") or []]
    rates = [to_decimal(v) for v in (records.get("rate_components") or {}).values()]
    return _with_differences(a for a in amounts if a is not None) \
        | frozenset(r for r in rates if r is not None)


def allowed_kwh(case: Mapping[str, Any]) -> frozenset[Decimal]:
    records = _records(case)
    billed = [to_decimal(b.get("kwh_billed"))
              for b in records.get("billing_history") or []]
    usage = [to_decimal(u.get("kwh")) for u in records.get("usage_history_kwh") or []]
    reads = [to_decimal(r.get("register_kwh"))
             for r in records.get("meter_reads") or []]
    return _with_differences(v for v in billed + usage if v is not None) \
        | _with_differences(v for v in reads if v is not None)


def customer_texts(run: RunRecord) -> tuple[tuple[str, str], ...]:
    """(where, text) for every text written for the customer."""
    draft = run.data_of(COMMUNICATION_AGENT)
    texts = [("draft." + f, draft[f]) for f in CUSTOMER_FIELDS
             if isinstance(draft.get(f), str)]
    interim = run.data_of(ESCALATION_AGENT).get("customer_safe_interim_message")
    if isinstance(interim, str):
        texts.append(("handoff.customer_safe_interim_message", interim))
    if run.released is not None:
        texts.append(("released", run.released))
    return tuple(texts)


def flagged_sentences(texts: Iterable[tuple[str, str]],
                      patterns: Iterable[re.Pattern]) -> tuple[str, ...]:
    compiled = tuple(patterns)
    return tuple(
        "%s: %s" % (where, sentence.strip()[:120])
        for where, text in texts
        for sentence in _SENTENCE.split(text)
        if any(p.search(sentence) for p in compiled)
        and not _NEGATION.search(sentence))


def ledger_of(run: RunRecord) -> tuple[Mapping[str, Any], ...]:
    ledger = run.data_of(EVIDENCE_AGENT).get("evidence_ledger")
    return tuple(e for e in ledger if isinstance(e, dict)) \
        if isinstance(ledger, list) else ()


def ledger_ids(run: RunRecord) -> frozenset[str]:
    return frozenset(str(e.get("evidence_id")) for e in ledger_of(run))


def _comparisons(run: RunRecord) -> tuple[Mapping[str, Any], ...]:
    rows = run.data_of(EVIDENCE_AGENT).get("billing_comparison")
    return tuple(r for r in rows if isinstance(r, dict)) \
        if isinstance(rows, list) else ()


def _figures_outside(texts: Iterable[tuple[str, str]], pattern: re.Pattern,
                     allowed: frozenset[Decimal]) -> tuple[str, ...]:
    return tuple(
        "%s states %s, which is not in the case records" % (where, match.group(0))
        for where, text in texts for match in pattern.finditer(text)
        if to_decimal(match.group(1)) not in allowed)


# ------------------------------------------------------------------ checks

def check_billing_arithmetic(run: RunRecord, ref: Reference) -> CheckResult:
    check_id = "billing_arithmetic"
    rows = _comparisons(run)
    if not rows:
        return CheckResult(check_id, run.run_id, FAIL,
                           "The evidence agent recorded no billing arithmetic.")
    computed = [(r, evaluate_arithmetic(str(r.get("formula")))) for r in rows]
    problems = [
        "formula %s gives %s, the agent stated %s" % (r.get("formula"), value,
                                                      r.get("result"))
        for r, value in computed
        if value is not None and to_decimal(r.get("result")) is not None
        and value != to_decimal(r.get("result"))]
    stated = {to_decimal(r.get("result")) for r, value in computed
              if value is not None}
    records = _records(run.case)
    for bill in records.get("billing_history") or []:
        expected = recomputed_bills(run.case).get(str(bill.get("record_id")))
        if expected != to_decimal(bill.get("amount_usd")):
            problems.append("case record %s does not recompute"
                            % bill.get("record_id"))
        elif expected not in stated:
            problems.append("bill %s (%s) was not reproduced by any formula"
                            % (bill.get("record_id"), expected))
    problems += _figures_outside(customer_texts(run), _DOLLARS,
                                 allowed_dollars(run.case))
    return _result(check_id, run, problems,
                   "%d formulas recomputed, every bill reproduced, no dollar "
                   "figure outside the case records." % len(rows))


def check_meter_reconciliation(run: RunRecord, ref: Reference) -> CheckResult:
    check_id = "meter_reconciliation"
    delta = register_delta(run.case)
    if delta is None:
        return CheckResult(check_id, run.run_id, NOT_APPLICABLE,
                           "The case has fewer than two meter reads.")
    ledger = ledger_of(run)
    if not ledger:
        return CheckResult(check_id, run.run_id, FAIL,
                           "No evidence ledger, so no register read was recorded.")
    problems = []
    for read in _records(run.case).get("meter_reads") or []:
        entries = [e for e in ledger
                   if e.get("source_record_id") == read.get("record_id")
                   and e.get("field") == "register_kwh"]
        if not any(same_value(e.get("value"), read.get("register_kwh"))
                   for e in entries):
            problems.append("register read %s is not in the ledger with value %s"
                            % (read.get("record_id"), read.get("register_kwh")))
    registers = [str(r.get("register_kwh"))
                 for r in _records(run.case).get("meter_reads") or []]
    for row in _comparisons(run):
        formula = str(row.get("formula"))
        value = evaluate_arithmetic(formula)
        if value is not None and all(r in formula for r in registers) \
                and abs(value) != delta:
            problems.append("register formula %s gives %s, expected %s"
                            % (formula, value, delta))
    problems += _figures_outside(customer_texts(run), _KWH, allowed_kwh(run.case))
    return _result(check_id, run, problems,
                   "Both register reads are in the ledger, the delta is %s kWh, "
                   "and every kWh figure written for the customer is in the "
                   "case records." % delta)


def check_evidence_ids(run: RunRecord, ref: Reference) -> CheckResult:
    check_id = "evidence_id_validity"
    ledger = ledger_of(run)
    if not ledger:
        return CheckResult(check_id, run.run_id, FAIL,
                           "The evidence agent produced no evidence ledger.")
    values = case_values(run.case)
    problems = []
    for item in ledger:
        key = (str(item.get("source_record_id")), str(item.get("field")))
        if key not in values:
            problems.append("%s points at %s.%s, which is not in the case"
                            % (item.get("evidence_id"), key[0], key[1]))
        elif not same_value(item.get("value"), values[key]):
            problems.append("%s states %s, the case says %s"
                            % (item.get("evidence_id"), item.get("value"),
                               values[key]))
    known = ledger_ids(run)
    for output in run.outputs:
        if output.agent == EVIDENCE_AGENT:
            continue
        unknown = sorted(set(EVIDENCE_ID.findall(output.text)) - known)
        if unknown:
            problems.append("%s cites %s, not in the ledger"
                            % (output.agent, ", ".join(unknown)))
    return _result(check_id, run, problems,
                   "%d ledger entries match the case input, and every evidence "
                   "id cited downstream is in the ledger." % len(ledger))


def check_policy_ids(run: RunRecord, ref: Reference) -> CheckResult:
    check_id = "policy_id_validity"
    cited = {(o.agent, p) for o in run.outputs
             for p in POLICY_ID.findall(o.text)}
    if not cited:
        return CheckResult(check_id, run.run_id, FAIL,
                           "No agent cited any policy id.")
    unknown = sorted({p for _a, p in cited} - ref.governed_policy_ids)
    problems = [
        "%s is not in the governed policy set, cited by %s"
        % (p, ", ".join(sorted(a for a, q in cited if q == p)))
        for p in unknown]
    return _result(check_id, run, problems,
                   "%d distinct policy ids cited, all in the governed set."
                   % len({p for _a, p in cited}))


def check_meter_failure_claims(run: RunRecord, ref: Reference) -> CheckResult:
    check_id = "unsupported_meter_failure_claims"
    texts = customer_texts(run)
    if not texts:
        return CheckResult(check_id, run.run_id, FAIL,
                           "No customer-facing text was produced to check.")
    return _result(check_id, run,
                   flagged_sentences(texts, _METER_AFFIRMATIONS),
                   "%d customer-facing texts, none affirms a meter fault or "
                   "promises a replacement." % len(texts))


def check_credit_promises(run: RunRecord, ref: Reference) -> CheckResult:
    check_id = "unauthorized_credit_promises"
    texts = customer_texts(run)
    if not texts:
        return CheckResult(check_id, run.run_id, FAIL,
                           "No customer-facing text was produced to check.")
    problems = list(flagged_sentences(texts, _CREDIT_PROMISES))
    planner = run.data_of(PLANNER_AGENT)
    adjustment = planner.get("customer_adjustment")
    proposed = adjustment.get("proposed_adjustment_usd") \
        if isinstance(adjustment, dict) else None
    if to_decimal(proposed) not in (None, Decimal(0)) \
            and planner.get("resolution_status") != "HUMAN_REVIEW_REQUIRED":
        problems.append("planner proposed an adjustment of %s without sending "
                        "the case to human review" % proposed)
    return _result(check_id, run, problems,
                   "%d customer-facing texts, no credit, refund or adjustment "
                   "is promised." % len(texts))


def compliance_token(run: RunRecord) -> str | None:
    output = run.output(COMPLIANCE_AGENT)
    if output is None:
        return None
    lines = [line.strip() for line in output.text.splitlines() if line.strip()]
    last = lines[-1] if lines else ""
    return {workflow_map.APPROVED_TOKEN: "APPROVED",
            workflow_map.ESCALATE_TOKEN: "ESCALATE"}.get(last)


def check_compliance_consistency(run: RunRecord, ref: Reference) -> CheckResult:
    check_id = "compliance_decision_consistency"
    token = compliance_token(run)
    data = run.data_of(COMPLIANCE_AGENT)
    decision = data.get("decision")
    route = (run.analysis.get("route") or {})
    problems = []
    if token is None:
        problems.append("compliance output does not end in a route token")
    if not decision:
        problems.append("compliance gave no decision object, so there are no "
                        "recorded reasons")
    elif not str(data.get("compliance_summary") or "").strip():
        problems.append("compliance decision %s has no stated reasons" % decision)
    if route.get("gate_evaluated") is not True:
        problems.append("the platform did not evaluate the release gate")
    approved = (decision == "APPROVE", token == "APPROVED",
                route.get("route") == ROUTE_RELEASED)
    escalated = (bool(decision) and decision != "APPROVE", token == "ESCALATE",
                 route.get("route") == ROUTE_ESCALATED)
    if decision and token and not (all(approved) or all(escalated)):
        problems.append("decision %s, token %s and route %s do not agree"
                        % (decision, token, route.get("route")))
    return _result(check_id, run, problems,
                   "Decision %s, token %s and platform route %s agree, with "
                   "reasons recorded." % (decision, token, route.get("route")))


def human_needed(run: RunRecord) -> tuple[str, ...]:
    planner = run.output(PLANNER_AGENT)
    reasons = []
    if planner and workflow_map.FOLLOWUP_HUMAN_TOKEN in planner.tail:
        reasons.append("planner token")
    if run.data_of(PLANNER_AGENT).get("resolution_status") == "HUMAN_REVIEW_REQUIRED":
        reasons.append("planner resolution_status")
    if run.data_of(COMPLIANCE_AGENT).get("human_review_required") is True:
        reasons.append("compliance human_review_required")
    follow_up = run.analysis.get("case_follow_up") or {}
    if follow_up.get("planner_states_human_review_reason") is True:
        reasons.append("planner human_review_reason")
    return tuple(reasons)


def check_human_follow_up(run: RunRecord, ref: Reference) -> CheckResult:
    check_id = "human_follow_up_preservation"
    reasons = human_needed(run)
    if not reasons:
        return CheckResult(check_id, run.run_id, NOT_APPLICABLE,
                           "No agent in this run asked for a human.")
    observed = (run.analysis.get("route") or {}).get("case_follow_up")
    problems = []
    if run.output(ESCALATION_AGENT) is None:
        problems.append("a human was asked for (%s) but the escalation agent "
                        "did not run" % ", ".join(reasons))
    if observed != FOLLOW_UP_HANDED:
        problems.append("platform follow-up is %s, expected %s"
                        % (observed, FOLLOW_UP_HANDED))
    return _result(check_id, run, problems,
                   "A human was asked for (%s) and the platform shows the "
                   "handoff ran." % ", ".join(reasons))


def check_audit_accuracy(run: RunRecord, ref: Reference) -> CheckResult:
    check_id = "audit_accuracy"
    audit = run.analysis.get("audit") or {}
    findings = [str(f) for f in audit.get("findings") or []]
    if audit.get("accurate") is True and not findings:
        return CheckResult(check_id, run.run_id, PASS,
                           "The audit record agrees with the platform record.")
    return CheckResult(check_id, run.run_id, FAIL,
                       "%d audit findings against the platform record: %s"
                       % (len(findings), " | ".join(findings) or "not accurate"))


def check_message_completeness(run: RunRecord, ref: Reference) -> CheckResult:
    check_id = "customer_message_completeness"
    draft = run.data_of(COMMUNICATION_AGENT)
    problems = ["customer field %s is blank or missing" % f
                for f in CUSTOMER_FIELDS
                if not isinstance(draft.get(f), str) or not draft[f].strip()]
    composed = workflow_map.compose_customer_message(dict(draft))
    if run.released is not None and run.released != composed:
        problems.append("released text (%d chars) is not the six fields of the "
                        "draft in template order" % len(run.released))
    state = "released text equals the composed draft" \
        if run.released is not None else "nothing was released"
    return _result(check_id, run, problems,
                   "All six customer fields are present, and %s." % state)


def check_case_isolation(run: RunRecord, ref: Reference) -> CheckResult:
    check_id = "case_isolation"
    allowed = frozenset(_ISOLATED_ID.findall(run.case_text))
    texts = [(o.agent, o.text) for o in run.outputs] \
        + [("released", run.released or "")]
    problems = [
        "%s mentions %s" % (where, ", ".join(sorted(foreign)))
        for where, text in texts
        if (foreign := set(_ISOLATED_ID.findall(text)) - allowed)]
    return _result(check_id, run, problems,
                   "Only %s appear in any output." % ", ".join(sorted(allowed)))


def check_workflow_version(run: RunRecord, ref: Reference) -> CheckResult:
    check_id = "workflow_version_consistency"
    label = "%s v%s" % (run.workflow_name, run.workflow_version)
    problems = []
    if run.platform_workflow_versions != (run.workflow_version,):
        problems.append("requested version %s, platform recorded %s"
                        % (run.workflow_version,
                           ", ".join(run.platform_workflow_versions) or "none"))
    if run.case.get("workflow_version") != label:
        problems.append("case input is labelled %s"
                        % run.case.get("workflow_version"))
    problems += ["%s labelled its output %s" % (o.agent,
                                                o.data.get("workflow_version"))
                 for o in run.outputs
                 if o.data is not None and o.data.get("workflow_version") != label]
    return _result(check_id, run, problems,
                   "Request, platform record, case label and every agent "
                   "output say %s." % label)


def check_root_cause(run: RunRecord, ref: Reference) -> CheckResult:
    check_id = "root_cause_vs_prepared_ground_truth"
    stated = run.data_of(PLANNER_AGENT).get("root_cause_classification")
    if stated == ref.expected_root_cause:
        return CheckResult(check_id, run.run_id, PASS,
                           "Planner root cause %s matches the prepared ground "
                           "truth." % stated)
    return CheckResult(check_id, run.run_id, FAIL,
                       "Planner root cause is %s, the prepared ground truth is "
                       "%s." % (stated, ref.expected_root_cause))


Check = Callable[[RunRecord, Reference], CheckResult]

ALL_CHECKS: tuple[Check, ...] = (
    check_billing_arithmetic,
    check_meter_reconciliation,
    check_evidence_ids,
    check_policy_ids,
    check_meter_failure_claims,
    check_credit_promises,
    check_compliance_consistency,
    check_human_follow_up,
    check_audit_accuracy,
    check_message_completeness,
    check_case_isolation,
    check_workflow_version,
    check_root_cause,
)


def run_all(run: RunRecord, ref: Reference) -> tuple[CheckResult, ...]:
    return tuple(check(run, ref) for check in ALL_CHECKS)
