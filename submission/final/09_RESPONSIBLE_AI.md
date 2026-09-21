# Responsible AI

## Why this domain needs it

Utility billing decisions affect people who often cannot absorb an error. A wrong high-bill explanation can mean an unaffordable payment demand, and in some cases a disconnection process begins on a charge that was never properly established. The cost of confident wrongness is borne by the customer, not the utility.

That is the reason for evidence-first design, not a compliance afterthought.

## How the principles are actually implemented

**Reliability and safety.** The system fails closed. Anything short of explicit approval routes to a human rather than releasing an answer. Implemented in the workflow condition, validated on the real Power Fx engine, and observed in the hosted service: run 2 withheld the message and handed the case to a person, and the final run released a message only after all three gate terms held.

**Transparency.** Every material claim carries the evidence and policy IDs supporting it, and the platform record preserves which agents and versions produced the outcome. A customer-facing explanation can be traced to its source records. In the final run the compliance agent named the evidence, policies and checks it relied on, where in run 2 it gave no reasons at all, which is why reasons are now required.

**Accountability.** Nine separated roles mean no component both produces and approves an answer. Human authorization is required for every consequential action, and the decision card keeps the AI recommendation visibly distinct from established fact.

**Fairness.** Policy is applied from a versioned ledger rather than individual judgment, so the same evidence produces the same policy treatment. This build has not been tested for differential performance across customer segments, and with synthetic data it could not be meaningfully assessed. That is a real gap, named rather than glossed.

**Privacy and security.** Synthetic data only, enforced as a boundary rule in every agent. Real-data substitution is an explicit red-team scenario expected to produce CANNOT_RESOLVE_SAFELY. No customer identifiers, secrets or subscription identifiers appear in any artifact.

**Inclusiveness.** Customer-facing wording is contracted to be plain language with required disclosures, and vulnerable-customer status is a triage risk flag that forces human attention. Neither has been validated with real users.

## Specific harms considered

| Harm | Mitigation | Status |
|---|---|---|
| Confirming a meter fault that did not occur | Claim ledger plus independent compliance; the entire SYN-CASE-4003 scenario | Observed three times on one case. No run asserted a meter failure |
| Promising a credit the utility will not honor | No write path; adjustment authorization is human | Observed. No run promised a credit. The final message says a Human Billing Supervisor must approve any |
| Denying a legitimate meter problem | SYN-CASE-4016 is the contrast case: supported meter evidence must escalate, not be dismissed | Configured |
| Overwhelming a customer with internal detail | Communication contract separates internal IDs from customer text | Configured |
| Silent escalation leaving a customer waiting | Customer-safe interim message required on escalation | Configured. Produced in runs 2 and 3. No real customer or reviewer is notified, because no channel is integrated |
| Deferring to a confident but wrong customer | The scenario the system is built around | Demonstrated on one synthetic case. The released message declines to confirm the meter claim and also says remote diagnostics do not rule everything out |
| Sending the customer something unreadable | Six-field release, readable-field guard | Happened in run 1, which sent an unevaluated expression. Corrected, and the final run released readable text |

The fourth row is worth naming. A system tuned only to avoid false positives on meter faults would learn to dismiss every meter complaint, which is its own harm. SYN-CASE-4016 exists specifically so that suppressing a supported concern counts as a failure.

## Honest limits

The controls have met real model responses three times, on one benign synthetic case, and the final run behaved as designed. That is a demonstration, not a validation. No red-team scenario has been executed. No fairness assessment has been performed. No real customer has read a message. One run is one sample of a non-deterministic system, and nothing here supports a claim of production readiness.
