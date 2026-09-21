# Governance

## Where control actually lives

A governance claim is only as strong as its enforcement point. This build has three, and they are not equal.

| Control | Enforced by | Strength |
|---|---|---|
| Fail-closed routing to a human | Workflow condition, escalation is the default branch | Strong. Structural, not advisory. Observed in the hosted service in run 2 |
| Draft withheld until approved | Workflow, autoSend false plus SendActivity on the approved branch only | Strong, within one conversation. Observed in all three runs |
| A stalled specialist cannot reach the customer | Third gate term: evidence, usage, policy and compliance outputs must each be a JSON object with its key field | Strong. Structural. Evaluated true in the final run, never yet false in the hosted service |
| A blank customer field cannot be released | Second gate term | Strong. Structural |
| Open case work survives an approved message | Separate follow-up gate on the planner's token, defaulting to a human handoff | Strong. Observed in the final run |
| Output shape of evidence, policy, communication and audit | Strict JSON schema enforced by the service | Strong for shape, silent on meaning |
| Claims must carry evidence and policy IDs | Agent output contracts | Moderate. A contract the model follows |
| Never approve an unsupported claim | EvidenceComplianceAgent instructions | Moderate |
| Compliance must record its reasons | EvidenceComplianceAgent instructions, backed by the third gate term | Moderate. Run 2 gave none, the final run gave them |
| Two-correction ceiling | Compliance contract | Weak today. The loop is not wired, so the ceiling is never reached |
| Synthetic-only boundary | Every agent's boundary rule | Moderate |

Being honest about the middle column is the point. Prompt-level rules are real controls but they are probabilistic. The workflow-level controls are deterministic. The architecture deliberately puts the most consequential decision, whether an answer reaches a customer, on the deterministic side.

## The twelve gates

1. Intent and scope must be classified before investigation.
2. Evidence must be issued with stable IDs and a source record reference.
3. Derived calculations must carry a formula and the evidence IDs used.
4. Usage hypotheses must be split into supported and unsupported.
5. Policy references must resolve to a real policy ID and version.
6. Missing policy for a governed action forces human review.
7. Policy conflict forces human review.
8. Every material claim must appear in the claim ledger with its support.
9. The customer message may not introduce a claim absent from the ledger.
10. Compliance must verify referenced IDs resolve to real ledger records.
11. Anything short of explicit approval routes to human escalation.
12. Every terminal case must produce an audit record with participating agents, ledgers and disposition.

## Decision authority

The system recommends. It never authorizes. Adjustments, credits, meter replacement and any commitment with financial or physical consequence require a named human reviewer. The escalation decision card exists to make that human's job fast: known facts, unknowns, applicable policy, risk, and a recommended next step, with the AI recommendation kept visibly separate from the established facts.

## Audit

CaseAuditAgent produces the terminal record: case ID, workflow version, participating agents and the status of each output, evidence IDs, policy IDs, claim IDs, the compliance route token, the compliance decision and its reasons, correction count, human review status, final disposition, audit completeness, and execution status.

The audit is a model's account of the conversation, so it is not the source of truth about the run. In runs 1 and 2 it misstated parts of what happened, including recording an approval when compliance had escalated. Two things changed. The audit agent now records every agent version as NOT_OBSERVED, because it cannot see platform metadata, and reads the route token before stating a decision. And the runner compares the audit with the platform record on every run: token against decision, route against disposition, each output status against what that output actually was. In the final run that comparison produced zero findings.

Execution status was corrected during this pass. The enum previously offered only CONFIGURED, PREPARED_NOT_EXECUTED and PRODUCTION_TARGET, so a successful run would have recorded itself as not executed. It now includes RUNTIME_EXECUTED and RUNTIME_FAILED, with an explicit instruction never to report a successful execution for a configuration review, a dry run, or an empty conversation.

## Known governance gaps

- The correction loop is not wired, so REJECT_AND_REPLAN and REJECT_AND_REWRITE currently behave as escalation rather than as bounded correction.
- Release control operates inside one Foundry conversation. A production deployment places the gate at the customer channel.
- Each gate has been exercised in the hosted service a small number of times, on one synthetic case. The approve route ran in run 1 and the final run, the fail-closed route in run 2. The follow-up branch where no person is needed has never run.
- The audit record has no field for what was released to the customer. The platform record holds that fact.
