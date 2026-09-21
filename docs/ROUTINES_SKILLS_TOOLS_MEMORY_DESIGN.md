# Routines, skills, tools and memory: design only

Written 2026-09-21. Nothing on this page is enabled, created or attached in
Foundry. The project has 0 schedules, 0 toolboxes, 0 memory stores, 0 vector
stores and no tool on any agent, and I checked that with read-only calls. An empty
Foundry page is not evidence of a capability, so I have not created placeholders.

Each section says what I would use the capability for, why it is off today, and
what would have to be true before I turned it on.

## Routines

| Routine | Trigger | What it would do | Why it is off |
| --- | --- | --- | --- |
| Overnight high-bill review | Schedule, once a night | Run the workflow over cases opened that day and leave escalation packages for the morning shift | Every firing runs nine model calls, about $0.07 per case at the final run's size. A schedule is a standing authorization to spend |
| Stale handoff reminder | Schedule, hourly | Find review assignments with no human decision after the service level and notify the fallback reviewer | Needs a case system that is not connected |
| Policy change re-check | Event, when the policy catalog version changes | Run `evaluation/policy/policy_change_impact.py` and list open cases that cite a changed policy | The local script already does this with no model. A routine adds nothing until there are open cases |

Conditions before enabling: documented pricing for routines (I found none), an
Azure budget with an alert, the runner's duplicate-run guard moved server side,
and a kill switch that a person can reach.

## Skills

I specify skills as deterministic local functions, because the rule in this
project is that a model never calculates a billing value.

| Skill | Input | Output | Where it lives today |
| --- | --- | --- | --- |
| Bill change | Two bill records | Amount and percentage change | Control Center tools, `calculate_bill_change` |
| Usage change | Two usage records | kWh and percentage change | `calculate_usage_change` |
| Rate effect | Usage and two rates | Dollar effect of a rate change | `calculate_rate_effect` |
| Estimated read true-up | Meter reads | Whether an estimated read was later corrected | `detect_estimated_trueup` |
| Meter read validation | Meter reads | Sequence and plausibility findings | `validate_meter_reads` |
| Claim ledger validation | Draft message and evidence ledger | Unsupported claims | `validate_claim_ledger` |
| Customer message composition | Approved draft | The released text | `runner/workflow_map.py`, `compose_customer_message` |

In the hosted runs the agents received the raw synthetic account records and no
tools, and my runner checked every figure in the evidence ledger against the case
input afterwards. Moving these functions into Foundry as callable skills would
mean attaching tools to validated agents, which needs a review and a paid run.

## Tools

No agent has a tool. That is a control, not an omission: an agent that can only
return text cannot take an action.

The production tool set is specified as typed ports in `integration/`, with
synthetic adapters and 138 local checks:

| Port | Direction | Notes |
| --- | --- | --- |
| `AccountEvidencePort`, `BillingEvidencePort`, `MeterEvidencePort`, `DiagnosticEvidencePort` | Read only | Scoped to one case. Another case or another customer's account gets one identical refusal |
| `CrmPort` | Read the case, send the approved message | Idempotent |
| `ReviewAssignmentPort` | Write, review assignments only | Carries the escalation package to a named role |
| `AdjustmentAuthorizationPort` | Request, then authorize | Only a human billing supervisor can authorize. An agent principal is refused. A supervisor cannot approve their own request |
| `AuditStorePort` | Append and verify only | Hash chained. No update or delete method exists |

Conditions before attaching any of them: the real system's owner agrees the
contract, the adapter runs behind a managed identity with read-only scope, and the
changed agent passes a fresh acceptance run.

## Memory

Off, and I would keep managed memory off for the resolution path.

A billing dispute has to be decided on the account's records, not on what the
system remembers from another conversation. Cross-case memory risks carrying one
customer's details into another customer's message, and Foundry memory bills for
chat and embedding tokens on every write and read.

What is worth remembering is narrow, and it is not conversational:

| Item | Store | Reason |
| --- | --- | --- |
| Case state and history | The system of record, through `CrmPort` | It is a record, not a memory |
| Reviewer decisions on similar cases | A reviewed, versioned precedent table | A person approves what goes in |
| Customer contact preferences | The customer system | It already lives there |

The Control Center keeps its demonstration state in the browser only.
