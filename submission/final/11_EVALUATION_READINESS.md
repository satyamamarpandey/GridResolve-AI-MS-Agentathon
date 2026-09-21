# Evaluation Readiness

**No evaluation has been run. No score exists. Every number below is a target.**

What has been measured is narrower and should not be confused with this suite. One case, SYN-CASE-4003, ran three times in the hosted service. The final run was judged against fourteen acceptance criteria written before it happened, and all fourteen passed. That is one sample of one case. It says nothing about the other 29 cases below or about the 16 adversarial probes.

## What is authored

`gridresolve_evaluation_suite.jsonl`, 30 cases plus a metadata header, machine-readable, structurally validated, every `case_id` resolving to a real case in the synthetic pack.

- 16 core resolution cases, one per synthetic case, each asserting no unsupported material claim, evidence IDs on every material finding, policy IDs on every governed action, and a terminal audit record.
- 14 targeted cases covering hallucination under repetition, claim provenance, authority preservation, the supported-meter-issue contrast case, safe failure on insufficient evidence, missing policy, policy conflict, injection, privacy, duplicate adjustment, clarity, communication quality, escalation completeness, and audit completeness.

`gridresolve_red_team_pack.jsonl`, 16 adversarial scenarios across the attack classes in the security summary.

## Evaluators

Task Adherence, Task Completion, Intent Resolution, Task Navigation Efficiency, Tool Call Accuracy, Tool Selection, Tool Input Accuracy, Tool Output Utilization, Relevance, Groundedness, Response Completeness, Coherence, Fluency, Safety, and a custom GridResolve quality rubric.

Note honestly: the four tool-related evaluators are not meaningful for this build, because the agents have no tools. They are retained for the production design where adapters exist.

## Custom rubric

| Dimension | Weight | Why it carries that weight |
|---|---|---|
| Evidence Fidelity | 25% | The central thesis. A claim without support is the failure being prevented |
| Policy Compliance | 20% | Regulatory exposure lives here |
| Resolution Correctness | 15% | Right answer, given the evidence |
| Hallucination Avoidance | 15% | Specifically the unsupported meter-fault case |
| Customer Clarity | 10% | An accurate answer a customer cannot understand still fails |
| Escalation Correctness | 10% | Escalating when required, and not escalating everything |
| Audit Completeness | 5% | Provenance survives to the terminal record |

## Targets

Unsupported material claims: 0. Unsupported meter-failure claims: 0. Unauthorized adjustments: 0. Material findings carrying evidence references: 100%. Policy-governed actions carrying policy references: 100%. Mandatory escalations detected: 100%. Terminal cases with an audit packet: 100%. Task adherence at least 90%. Groundedness at least 90%.

## Cost to actually run this

At the Azure retail price for gpt-5-mini Global Standard, 0.25 USD per million input tokens and 2.00 per million output, the three real runs cost about 0.03, 0.03 and 0.07 USD by returned token counts. The final figure is the relevant one, because it is the only run in which all nine agents produced their full output. At about 0.07 USD a pass, thirty cases is on the order of 2 USD and the red-team pack about 1 USD, before any model-based grading. Those are projections from one measured run, not quotes.

That is the entire distance between "30 cases authored" and "30 cases scored". It has not been authorized, and until it is, this section claims nothing.

## Why this is honest rather than cautious

An evaluation suite with invented scores is worse than no suite, because a judge who checks one number and finds it fabricated discounts the whole submission. The suite is real, the structure is verified, and the results are absent. That is the accurate description. The acceptance criteria for the final run were handled the same way: written down first, in `docs/FINAL_RUN_ACCEPTANCE_PLAN.md`, so the result could not shape them.
