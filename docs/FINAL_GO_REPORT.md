# Final Demonstration Readiness: GO Report

> **Historical, superseded 2026-09-20. See `docs/CURRENT_STATUS.md`.** This is the
> go report written on 2026-09-19 for the first execution, against workflow v5.
> Before that run, the first of its three residual risks turned out to be real on
> the local Power Fx engine: the v5 gate does not compile against a table of
> messages, and v6 replaced it (`docs/CORRECTION_2026-09-20.md`). The second risk
> was real in the hosted service: run 1 delivered the release expression as literal
> text (`docs/FIRST_RUN_AND_CORRECTIONS_2026-09-20.md`). No authorization is
> outstanding and no further run is planned.
>
> Current facts: **three** genuine Foundry workflow executions of SYN-CASE-4003 on
> 2026-09-20, on workflow v6, v9 and v10. The live workflow is **v10**, with agents
> at versions 5, 9, 4, 6, 6, 5, 6, 5 and 7. The final run passed **14 of 14**
> acceptance criteria written beforehand: a 22-entry evidence ledger, nine policies
> mapped, the independent compliance agent **approved** the supported customer
> message with recorded reasons, a readable message was released, a separate
> follow-up decision sent the open investigation to human review, and the audit had
> zero findings. Provisional Azure cost is about **$0.13**, from returned token
> counts. The billed amount is not yet visible, which is not a confirmed $0.00.
> Local checks now total 813, plus 105 Power Fx cases and 94 read-only live checks.
> The 30 evaluation cases and 16 adversarial probes are still not executed. The
> system is a runtime-demonstrated, production-oriented prototype. It is not
> production-ready, and no utility integration is live.

Date: 2026-09-19. Case: SYN-CASE-4003. One controlled execution.

**Verdict: GO, conditional on you accepting the three unverifiable runtime behaviors listed at the end.**

Verification: `python tests/verify_live_config.py`, **33 of 33 live configuration checks passed**, all read-only.
Plus `python tests/test_routing_and_data.py`, **72 of 72 local static checks passed**.

## Required checks

| # | Check | Result | Evidence |
|---|---|---|---|
| 1 | Correct active workflow version | PASS | v5, state enabled, traffic 100% to @latest, not a draft |
| 2 | Correct agent versions | PASS | All nine match expected, verified live |
| 3 | External tools disabled | PASS | All nine have an empty tool list |
| 4 | Only gpt-5-mini | PASS | Verified on all nine |
| 5 | Synthetic input valid | PASS | Parses, SYNTHETIC_ONLY, arithmetic consistent, no answer leakage |
| 6 | Compliance routing configured | PASS | Exact sentinel token, old substring condition absent, escalation on the default branch |
| 7 | Customer release gate configured | PASS | 7 nodes autoSend false, SendActivity on the approved branch only |
| 8 | Audit agent included and terminal | PASS | CaseAuditAgent terminal on both paths, execution_status supports RUNTIME_EXECUTED |
| 9 | Expected cost documented | PASS | 0.09 USD expected, 0.26 conservative, 0.50 operational ceiling |
| 10 | No automatic retries | PASS | Manual single invocation, no retry logic anywhere |
| 11 | No new infrastructure required | PASS | Uses existing deployment; no App Insights, gateway, search or storage |

## Exact execution plan

One invocation. Input: `submission/SYN-CASE-4003_input.json`, sent verbatim as a single message, unmodified.

Expected path: Triage, AccountEvidence, UsageAnomaly, PolicyKnowledge, ResolutionPlanner, CustomerCommunication, EvidenceCompliance, then either SendActivity release on an exact approval token or EscalationCoordinatorAgent on anything else, then CaseAudit.

Not run: other cases, the evaluation suite, the red-team pack, LLM judge, Agent Optimizer, any external tool, any other model or workflow.

On failure: stop, capture, diagnose, **do not retry without fresh authorization.**

## Cost

Input 0.25, output 2.00, cached input 0.025 USD per million tokens, gpt-5-mini Global Standard, verified via the Azure Retail Prices API.

Expected about 0.09 USD. Conservative about 0.26 USD. Operational ceiling 0.50 USD, monitored by a person, not enforced by the platform.

Azure Cost Management reported no cost rows for the period immediately before this report.

## Three residual risks, accept before running

These cannot be resolved without executing, which is precisely what the run is for.

1. **Runtime type of `Local.Var1497`.** If the variable holds a message collection rather than text, the `in` operator may not evaluate the sentinel as expected. Failure mode is conservative: no token match means escalation, which is the safe direction.
2. **`SendActivity` with `activity: =Local.VarCustomerDraft`.** Rendering a stored agent response this way is undocumented for this shape. If it fails, the approved path may not emit a visible message. Failure mode is loud, not silent.
3. **`autoSend: false` on seven nodes.** Intended to withhold intermediate output. If it also suppresses the final response, the run completes with less visible output than expected.

All three are reversible. Workflow v4 remains deployed, active and selectable.

## What the run will and will not prove

Will prove: multi-agent execution, evidence and policy use, the behavior of the corrected gate on a real compliance response, terminal audit, real token counts, real latency, real cost.

Will not prove: parallel execution (sequential by design), correction loops (not wired), evaluation scores (suite not run), persisted traces (no Application Insights).

## Honest reporting commitment

The evidence determines the story. If compliance approves because no upstream agent ever asserted a meter fault, that is reported as the system resisting an unsupported assertion, not as a rejection. If the gate misroutes, that is reported. If the run fails, that is reported and diagnosed. Rules are in `submission/final/06_RUNTIME_PROOF.md`.

## Authorization

Awaiting the exact phrase: **APPROVE ONE SYNTHETIC DEMO RUN**

Nothing will be executed before it.
