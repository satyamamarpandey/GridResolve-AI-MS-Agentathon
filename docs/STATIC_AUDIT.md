# Static Audit (no model calls, no spend)

Date: 2026-09-19. Method: Foundry agents API GET, workflow YAML, local files, Microsoft Power Fx documentation. Nothing was executed.

## A1 CRITICAL: the fail-closed compliance gate probably fails OPEN

Workflow condition: `=Not("APPROVE" in Local.Var1497)` where Var1497 is the whole EvidenceComplianceAgent output.

Microsoft documents the Power Fx `in` operator as matching **regardless of case**, with `exactin` being the case-sensitive form. So the test matches "approve", "Approve", "not approved", "cannot approve" and "disapprove".

EvidenceComplianceAgent returns `compliance_summary` and `correction_instructions` as free text. A rejection explanation is very likely to contain the word "approve", for example "cannot approve an unsupported meter claim". In that case:

- `"APPROVE" in output` is TRUE
- `Not(TRUE)` is FALSE
- the escalation branch does NOT run
- flow goes straight to CaseAuditAgent

The gate therefore skips escalation exactly when escalation is required. This is the project's headline differentiator, and it is likely broken.

Proposed fix (config only, free to apply, needs one paid run to confirm):
`=Not(StartsWith(Trim(Local.Var1497.decision), "APPROVE"))` or test an exact decision token with `exactin` against the parsed `decision` field rather than the whole object. Exact syntax depends on whether Var1497 is text or a record, which is not determinable without a run.

Status: NOT APPLIED. Awaiting decision.

## A2 HIGH: CaseAuditAgent cannot record a successful execution

CaseAuditAgent's `execution_status` enum is `CONFIGURED`, `PREPARED_NOT_EXECUTED`, or `PRODUCTION_TARGET`. None of these means "this run executed". After a live demo the terminal audit record will still say CONFIGURED or PREPARED_NOT_EXECUTED, which contradicts the runtime proof and reads badly to a judge.

Proposed fix: add `EXECUTED` to the enum. Config only, free.
Status: NOT APPLIED.

## A3 HIGH: two manifest artifacts did not exist (FIXED)

`gridresolve_submission_manifest.json` and the dossier both referenced `gridresolve_evaluation_suite.jsonl` and `gridresolve_red_team_pack.jsonl`. Neither existed on disk. A judge opening the submission would have found two of six listed files missing.

Both were authored deterministically from the dossier and synthetic pack, with no model involvement:
- `gridresolve_evaluation_suite.jsonl`: 30 cases plus a metadata line, covering all 16 synthetic cases and 14 targeted checks, with the 15 named evaluators and the weighted rubric.
- `gridresolve_red_team_pack.jsonl`: all 16 attack classes named in dossier section 14, with probes and expected behavior.

Both validated as parseable JSONL. Status marked PREPARED_NOT_EXECUTED, which remains accurate.

## A4 MEDIUM: metadata drift in all nine agents

Every agent's instructions carry `workflow_target=GridResolveAIWorkflow v3` while the live workflow is v4. Every agent also carries `execution_status=CONFIGURED`, which becomes stale after a run.

Impact: presentation and credibility, not behavior.
Proposed fix: update both tokens. Config only, free, creates one new version per agent.
Status: NOT APPLIED.

## A5 MEDIUM: shared-state field naming is inconsistent

The shared case-state model (defined in CaseTriageAgent and expected by EvidenceComplianceAgent) names the ledgers `evidence_ledger`, `policy_ledger`, `claim_ledger`. But:

| Agent | Emits | State expects |
|---|---|---|
| AccountEvidenceAgent | `evidence_records` | `evidence_ledger` |
| PolicyKnowledgeAgent | `applicable_policies` | `policy_ledger` |
| ResolutionPlannerAgent | `claim_ledger` | `claim_ledger` (consistent) |

EvidenceComplianceAgent is instructed to check `evidence_ledger` and `policy_ledger`. If the upstream agents emit the other names, compliance may report missing ledgers and reject or escalate for the wrong reason. A capable model will probably map them, but this is an unforced risk in the exact chain the demo depends on.

Proposed fix: have AccountEvidenceAgent emit `evidence_ledger` and PolicyKnowledgeAgent emit `policy_ledger`, keeping the record shape. Config only, free.
Status: NOT APPLIED.

## A6 MEDIUM: compliance is a review, not a release gate

Every workflow node uses `output.autoSend: true`, including CustomerCommunicationAgent. The draft customer message is therefore published to the conversation before EvidenceComplianceAgent ever inspects it. Nothing withholds it.

This does not break the demo, but the submission must not claim that compliance blocks the message from reaching the customer. Accurate wording: compliance is an independent review whose decision is recorded in the case and drives escalation and audit. A true release gate is a PRODUCTION_TARGET.

## A7 INFO: no screenshots on disk

The manifest lists S01, S03, S04, S06 and S16 as CAPTURED. No image files exist anywhere in the project. They may be elsewhere on your machine. The submission requires screenshots, so this needs resolving.

## A8 RESOLVED: web_search tool binding removed

All nine agents had a live `web_search` tool binding, a real paid-tool and grounding risk. Removed on 2026-09-18 by creating tool-free versions. Instructions, model and reasoning unchanged. Old versions retained.

## Summary

| ID | Severity | Item | Status |
|---|---|---|---|
| A1 | CRITICAL | Fail-closed gate likely fails open | Fix proposed, not applied |
| A2 | HIGH | Audit cannot record execution | Fix proposed, not applied |
| A3 | HIGH | Missing manifest artifacts | FIXED |
| A4 | MEDIUM | Stale workflow_target metadata | Fix proposed, not applied |
| A5 | MEDIUM | Ledger field naming mismatch | Fix proposed, not applied |
| A6 | MEDIUM | autoSend publishes draft pre-compliance | Wording correction required |
| A7 | INFO | Screenshots absent from disk | User action |
| A8 | RESOLVED | web_search bound to all agents | FIXED |
