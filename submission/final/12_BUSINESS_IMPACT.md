# Business Impact

**Every business figure below is a target or an industry-shaped assumption. None is a measured result of this system. No benchmark study is cited because none was run.** The only measured figures are the token counts and provisional cost of three runs of one synthetic case.

## The cost of one wrong billing explanation

A high-bill dispute that gets an unsupported answer does not end. It produces a repeat contact, often a field visit to a meter that was never faulty, sometimes a credit issued to end the argument, and occasionally a regulatory complaint. The single answer is cheap. The consequences of it being wrong are not.

This is why the primary metric is not handling time.

## Primary metric

**Unsupported material claims reaching a customer. Target: zero.**

It is measurable from the claim ledger without human scoring: a claim whose referenced evidence and policy IDs do not resolve is unsupported by construction. That property is what makes this system auditable rather than merely careful.

## Secondary metrics

| Metric | Target | Source |
|---|---|---|
| Unsupported meter-failure claims | 0 | Claim ledger plus compliance decision |
| Unauthorized adjustments | 0 | No write path exists; human authorization required |
| Material findings carrying evidence references | 100% | Claim ledger |
| Policy-governed actions carrying policy references | 100% | Policy ledger |
| Mandatory escalations correctly detected | 100% | Compliance decision versus expected route |
| Terminal cases with a complete audit packet | 100% | Audit record |
| Cases resolved without human touch, where safe | Directional improvement | Disposition mix |
| Repeat contacts on the same case | Directional reduction | Requires production integration |

The last two cannot be measured at all without connecting to a real case management system, and are listed to show what would be measured, not what is claimed.

## Where value comes from

**Avoided rework, not faster chat.** If the explanation is right and provably grounded the first time, the repeat contact and the unnecessary field visit do not happen. That is where utility cost concentrates.

**Regulatory defensibility.** Every terminal case carries a record of which evidence and which policy version produced the outcome, and who approved it. Reconstructing that after the fact from call notes is expensive and often impossible.

**Consistency across agents and shifts.** Policy is applied from a versioned ledger rather than from individual recall.

**Human attention aimed at real decisions.** Escalation with a structured decision card means reviewers spend time deciding, not reconstructing.

## Runtime economics, as measured on price and projected on volume

Azure retail price for gpt-5-mini Global Standard, verified 2026-09-18 via the Azure Retail Prices API: 0.25 USD per million input tokens, 2.00 per million output tokens, 0.025 per million cached input tokens.

Measured on three real runs of SYN-CASE-4003: about 0.03, 0.03 and 0.07 USD. The last is the representative one, 94,352 input and 22,433 output tokens, because it is the only run in which all nine agents produced their full output. These are provisional figures from returned token counts. The billed amount is not yet visible in Azure Cost Management. No cached input tokens were reported, so the shared conversation is billed in full at every step, which is the first thing a production design would reduce.

At those rates the model cost per investigation is a rounding error against the labor and truck-roll cost it is intended to avoid. That arithmetic only matters if the answers are right, which is the entire point of the governance layer.

## What would make this credible

Running the 30-case evaluation suite and publishing real scores against the targets above. One synthetic case passing fourteen pre-registered criteria shows the design can work end to end. It does not measure any metric in this document. Until the suite runs, this section describes an intended measurement framework and nothing more.
