"""Provenance validator: can one run be followed from the customer's words to
the audit record, identifier by identifier?

The chain has eight links:

  customer_assertion -> evidence -> policy -> claim_ledger -> compliance
  -> customer_response -> human_review_package -> audit

Each link is RESOLVED or BROKEN, with the identifiers involved. NOT_TAKEN is
used only when the run did not take that branch (a withheld message, or a case
that needed no human). It is never counted as resolved.

Local and read-only. No model, no network.

Run: python -m evaluation.provenance
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from runner import workflow_map

from evaluation import deterministic_checks as dc
from evaluation.run_record import RunRecord, load_all

RESOLVED = "RESOLVED"
BROKEN = "BROKEN"
NOT_TAKEN = "NOT_TAKEN"


@dataclass(frozen=True)
class Link:
    link: str
    run: str
    status: str
    identifiers: tuple[str, ...]
    detail: str

    def as_dict(self) -> dict[str, Any]:
        return {"link": self.link, "run": self.run, "status": self.status,
                "identifiers": list(self.identifiers), "detail": self.detail}


def _link(name: str, run: RunRecord, problems: Iterable[tuple[str, str]],
          identifiers: Iterable[str], detail: str) -> Link:
    found = tuple(problems)
    if found:
        return Link(name, run.run_id, BROKEN, tuple(sorted({i for i, _ in found})),
                    " | ".join(text for _, text in found))
    return Link(name, run.run_id, RESOLVED, tuple(sorted(set(identifiers))),
                detail)


def _ids(rows: Any, key: str) -> tuple[str, ...]:
    return tuple(str(r.get(key)) for r in rows if isinstance(r, dict)) \
        if isinstance(rows, list) else ()


def _strings(value: Any) -> tuple[str, ...]:
    return tuple(str(v) for v in value) if isinstance(value, list) else ()


def claims_of(run: RunRecord) -> tuple[Mapping[str, Any], ...]:
    rows = run.data_of(dc.PLANNER_AGENT).get("claim_ledger")
    return tuple(r for r in rows if isinstance(r, dict)) \
        if isinstance(rows, list) else ()


def policy_ledger_ids(run: RunRecord) -> frozenset[str]:
    return frozenset(_ids(run.data_of(dc.POLICY_AGENT).get("policy_ledger"),
                          "policy_id"))


def link_customer_assertion(run: RunRecord) -> Link:
    request = run.case.get("customer_request")
    case_id = str(run.case.get("case_id"))
    triage = run.data_of("CaseTriageAgent")
    problems = []
    if not isinstance(request, str) or not request.strip():
        problems.append((case_id, "the case input has no customer request"))
    if triage.get("case_id") != run.case.get("case_id"):
        problems.append((case_id, "triage did not return an output for %s"
                         % case_id))
    return _link("customer_assertion", run, problems, [case_id],
                 "The customer's request is in the case input and triage "
                 "answered for the same case.")


def link_evidence(run: RunRecord) -> Link:
    ledger = dc.ledger_of(run)
    if not ledger:
        return Link("evidence", run.run_id, BROKEN, (),
                    "The evidence agent produced no ledger, so nothing "
                    "downstream can point at a record.")
    values = dc.case_values(run.case)
    problems = [
        (str(e.get("evidence_id")), "%s does not resolve to a case record"
         % e.get("evidence_id"))
        for e in ledger
        if (str(e.get("source_record_id")), str(e.get("field"))) not in values
        or not dc.same_value(e.get("value"),
                             values[(str(e.get("source_record_id")),
                                     str(e.get("field")))])]
    return _link("evidence", run, problems, dc.ledger_ids(run),
                 "%d ledger entries, each resolves to a field of the case "
                 "input with the same value." % len(ledger))


def link_policy(run: RunRecord, catalog_ids: frozenset[str]) -> Link:
    cited = policy_ledger_ids(run)
    if not cited:
        return Link("policy", run.run_id, BROKEN, (),
                    "The policy agent produced no policy ledger.")
    problems = [(p, "%s is not in the policy catalog" % p)
                for p in sorted(cited - catalog_ids)]
    return _link("policy", run, problems, cited,
                 "%d policies, each resolves to a catalog record." % len(cited))


def link_claim_ledger(run: RunRecord) -> Link:
    claims = claims_of(run)
    if not claims:
        return Link("claim_ledger", run.run_id, BROKEN, (),
                    "The planner produced no claim ledger.")
    evidence, policies = dc.ledger_ids(run), policy_ledger_ids(run)
    problems = []
    for claim in claims:
        name = str(claim.get("claim_id"))
        cited_evidence = _strings(claim.get("evidence_ids"))
        if not cited_evidence:
            problems.append((name, "%s cites no evidence" % name))
        problems += [(e, "%s cites %s, not in the evidence ledger" % (name, e))
                     for e in cited_evidence if e not in evidence]
        problems += [(p, "%s cites %s, not in the policy ledger" % (name, p))
                     for p in _strings(claim.get("policy_ids"))
                     if p not in policies]
    return _link("claim_ledger", run, problems, _ids(list(claims), "claim_id"),
                 "%d claims, every evidence and policy id resolves." % len(claims))


def link_compliance(run: RunRecord) -> Link:
    data = run.data_of(dc.COMPLIANCE_AGENT)
    token = dc.compliance_token(run)
    known = frozenset(_ids(list(claims_of(run)), "claim_id"))
    problems = []
    if not data.get("decision"):
        problems.append(("decision", "no decision object, so no reasons to follow"))
    elif not str(data.get("compliance_summary") or "").strip():
        problems.append(("compliance_summary", "decision without reasons"))
    if token is None:
        problems.append(("route_token", "no route token"))
    problems += [(c, "compliance names %s, not in the claim ledger" % c)
                 for c in _strings(data.get("unsupported_claim_ids"))
                 if c not in known]
    return _link("compliance", run, problems,
                 ["decision:%s" % data.get("decision"), "token:%s" % token],
                 "Decision %s with reasons, token %s."
                 % (data.get("decision"), token))


def link_customer_response(run: RunRecord) -> Link:
    draft = run.data_of(dc.COMMUNICATION_AGENT)
    claims = frozenset(_ids(list(claims_of(run)), "claim_id"))
    evidence = dc.ledger_ids(run)
    problems = [(c, "draft cites %s, not in the claim ledger" % c)
                for c in _strings(draft.get("internal_claim_ids"))
                if c not in claims]
    problems += [(e, "draft cites %s, not in the evidence ledger" % e)
                 for e in _strings(draft.get("internal_evidence_ids"))
                 if e not in evidence]
    if not draft:
        problems.append(("draft", "no customer draft"))
    if run.released is not None and \
            run.released != workflow_map.compose_customer_message(dict(draft)):
        problems.append(("released", "the released text is not the draft's "
                                     "six customer fields"))
    if not problems and run.released is None:
        return Link("customer_response", run.run_id, NOT_TAKEN,
                    tuple(sorted(_strings(draft.get("internal_claim_ids")))),
                    "The draft resolves, but the message was withheld, so "
                    "nothing reached the customer.")
    return _link("customer_response", run, problems,
                 _strings(draft.get("internal_claim_ids")),
                 "The released text is the draft, and the draft's claim and "
                 "evidence ids resolve.")


def link_human_review_package(run: RunRecord, catalog_ids: frozenset[str]) -> Link:
    output = run.output(dc.ESCALATION_AGENT)
    if output is None:
        if dc.human_needed(run):
            return Link("human_review_package", run.run_id, BROKEN, (),
                        "A human was asked for but no handoff package exists.")
        return Link("human_review_package", run.run_id, NOT_TAKEN, (),
                    "No agent asked for a human and no package was built.")
    data = run.data_of(dc.ESCALATION_AGENT)
    evidence = dc.ledger_ids(run)
    routing = data.get("routing") if isinstance(data.get("routing"), dict) else {}
    problems = [(e, "package cites %s, not in the evidence ledger" % e)
                for e in sorted(set(dc.EVIDENCE_ID.findall(output.text)) - evidence)]
    problems += [(p, "package cites %s, not in the policy catalog" % p)
                 for p in sorted(set(dc.POLICY_ID.findall(output.text))
                                 - catalog_ids)]
    reviewer = str(routing.get("route_to") or data.get("recommended_reviewer")
                   or "").strip()
    if not reviewer:
        problems.append(("reviewer", "the package names no human reviewer"))
    return _link("human_review_package", run, problems,
                 ["reviewer:%s" % reviewer],
                 "The package names a reviewer and its evidence and policy "
                 "ids resolve.")


def link_audit(run: RunRecord) -> Link:
    data = run.data_of(dc.AUDIT_AGENT)
    if not data:
        return Link("audit", run.run_id, BROKEN, (), "No audit record.")
    expected = {
        "evidence_ids": dc.ledger_ids(run),
        "claim_ids": frozenset(_ids(list(claims_of(run)), "claim_id")),
        "policy_ids": policy_ledger_ids(run),
    }
    problems = []
    for field, known in expected.items():
        listed = frozenset(_strings(data.get(field)))
        problems += [(i, "audit lists %s under %s, which no agent produced"
                      % (i, field)) for i in sorted(listed - known)]
        problems += [(i, "audit omits %s from %s" % (i, field))
                     for i in sorted(known - listed)]
    audit = run.analysis.get("audit") or {}
    problems += [("platform_record", str(f)) for f in audit.get("findings") or []]
    return _link("audit", run, problems, ["audit:%s" % run.run_id],
                 "The audit lists exactly the evidence, claim and policy ids "
                 "the run produced, and agrees with the platform record.")


def trace(run: RunRecord, catalog_ids: frozenset[str]) -> tuple[Link, ...]:
    return (
        link_customer_assertion(run),
        link_evidence(run),
        link_policy(run, catalog_ids),
        link_claim_ledger(run),
        link_compliance(run),
        link_customer_response(run),
        link_human_review_package(run, catalog_ids),
        link_audit(run),
    )


def catalog_ids_from(path: str) -> frozenset[str]:
    with open(path, encoding="utf-8") as handle:
        return frozenset(p["policy_id"] for p in json.load(handle)["policies"])


def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    catalog = catalog_ids_from(
        os.path.join(root, "evaluation", "policy", "policy_catalog.json"))
    for run in load_all(os.path.join(root, "evidence", "runtime")):
        sys.stdout.write("%s (workflow v%s)\n" % (run.run_id, run.workflow_version))
        for link in trace(run, catalog):
            sys.stdout.write("  %-22s %-9s %s\n"
                             % (link.link, link.status, link.detail[:110]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
