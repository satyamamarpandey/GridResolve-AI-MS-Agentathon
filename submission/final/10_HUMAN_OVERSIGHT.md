# Human Oversight

## The principle

The system recommends. A person authorizes. There is no path by which GridResolve AI commits money, changes a bill, dispatches a field visit, or tells a customer that a physical asset has failed.

## When a human is mandatory

- Any billing adjustment or credit, regardless of amount
- Any conclusion that a meter is defective
- Any policy conflict
- Any governed action with no applicable policy
- Any unsupported material claim reaching compliance
- Low or insufficient confidence on a material finding
- Two corrections already attempted on one case
- Suspected real-data contamination
- Legal, regulatory, fraud or vulnerable-customer flags

In the deployed workflow this set is broader in practice than in design, because the correction loop is not wired: REJECT_AND_REPLAN and REJECT_AND_REWRITE currently escalate rather than retry. That is more conservative than intended, not less.

## Two separate questions

Whether a customer message is safe to send, and whether the case still needs a person, are different questions, and the workflow keeps them apart. The compliance agent answers the first. The planner answers the second with a follow-up token, and the workflow reads it only after a message is approved, defaulting to a human handoff unless the token says exactly that none is required.

The final run shows why this matters. The message was safe, so it was approved and released. The case was not finished, because the customer still alleges a fault that only a physical test can settle and any adjustment needs a supervisor. So the case went to a person anyway. An approved message did not erase the open work.

## Reviewer personas

| Persona | Receives | Decides |
|---|---|---|
| Billing Resolution Specialist | Unsupported claim, ambiguous root cause | Whether the explanation may proceed |
| Meter Operations Reviewer | Any meter concern, supported or not | Whether to test or replace a meter |
| Adjustment Approver | Recommended credit or adjustment | Whether funds move |
| Compliance Supervisor | Policy conflict, missing policy, regulatory flag | Which policy governs |

## The decision card

Escalation is only useful if the human can act quickly. EscalationCoordinatorAgent produces a structured card rather than a transcript:

`decision_needed`, `known_facts`, `unknowns`, `applicable_policies`, `risk`, `recommended_next_step`, plus a `customer_safe_interim_message` that can be sent immediately without committing to a cause.

The agent contract requires the AI recommendation to be kept visibly separate from established facts, so a reviewer is never nudged into rubber-stamping a machine conclusion.

In the final run the card held four known facts with their evidence IDs, four unknowns, five applicable policies, a four-part risk statement and a recommended next step, and it routed to a Billing Supervisor with a Compliance Reviewer as fallback. It made no decision on the reviewer's behalf. The reviewer is a role, not a named person, and no real person was notified, because no case management system is integrated.

## Why the interim message matters

The common failure in escalation design is silence: the case goes to a human queue and the customer hears nothing for days. The interim message lets the customer be told promptly that their case is under review, without asserting a cause that has not been established. It is the difference between a safe system and an unresponsive one.

## Oversight of the AI itself

Beyond per-case review: every agent is versioned in Foundry with full history, every change is reversible, the terminal audit record names participating agents and versions, and the 30-case evaluation suite exists to measure behavior over time rather than trusting a single demonstration.

Per-case oversight has been exercised in the hosted service on one synthetic case. Run 2 took the fail-closed route and produced a review package with nothing sent to the customer. The final run released an approved message and then handed the open case to a human. What has not happened: a real reviewer acting on a card, or a notification reaching anyone.
