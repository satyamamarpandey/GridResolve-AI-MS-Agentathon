# SYN-CASE-4003, a walkthrough for judges

One case, seven stages, told with the project's real data. Every figure below is
computed by deterministic code in `control-center/src/tools/`, not produced by a
language model.

**Read this first.** This walkthrough follows the local Control Center, which is
a deterministic offline demonstration. Nothing in the seven stages below is
Foundry model output. The Control Center shows the **designed path for an unsafe
draft**: a draft that asserts a meter fault is rejected and the case goes to a
person.

The hosted system has also run for real, three times, on 2026-09-20, and the real
runs did not follow that path. In the final run, on workflow v10, nine Foundry
agents investigated this same case. No agent asserted a meter fault, so there was
nothing to reject. The independent compliance agent **approved** the supported
customer message, with recorded reasons, the workflow released it, and a separate
follow-up decision sent the unresolved investigation to human review. That run
passed 14 of 14 acceptance criteria written beforehand. Each stage below ends
with a short note on what the final run actually did. Records:
`docs/CURRENT_STATUS.md` and `docs/FINAL_RUN_RESULT_2026-09-20.md`. Evidence:
`evidence/runtime/`.

The two are kept apart throughout, because a billing system that overstates its
own evidence is exactly the failure this project is about.

---

## The case in one paragraph

A customer's bill went from $152.80 to $203.40. They are certain the meter is
broken, and they have asked the utility to confirm that and correct the charge.
The evidence does not support a meter fault. It also does not disprove one. The
engineering problem is not producing a fluent explanation. It is making sure the
system cannot produce a confident one that nobody can defend.

---

## Stage 1. Customer complaint

**What is happening.** The case arrives with the customer's own words:

> "My bill jumped significantly this month. The meter has to be broken. Please
> confirm the meter caused the increase and fix the charge."

**Responsible agent.** `CaseTriageAgent`.

**Evidence available.** None yet. Only the request.

**Decision being made.** Classify intent as a high bill dispute, record that the
customer has alleged a meter fault, and note that the requested action is
`CONFIRM_METER_FAILURE_AND_ADJUST_BILL`.

**Why this matters.** The customer has asked for two things: a conclusion and a
refund. Recording the request verbatim, separately from what the evidence will
later support, is what makes it possible to refuse both without losing the
complaint. The request is never treated as a finding.

**Where to look.** Overview, and the Customer Assistant view.

---

## Stage 2. Billing and usage investigation

**What is happening.** Deterministic arithmetic over the billing records.

**Responsible agents.** `AccountEvidenceAgent` gathers records, `UsageAnomalyAgent`
analyses them.

**Evidence available.**

| Item | Previous period | Current period |
| --- | --- | --- |
| Bill | $152.80 | $203.40 |
| Consumption | 640 kWh | 870 kWh |
| Billing days | 30 | 31 |
| Daily average | 21.33 kWh/day | 28.06 kWh/day |

**Decision being made.** What actually drove the increase.

- The bill rose $50.60, which is 33.1 percent.
- Consumption rose 230 kWh.
- The energy charge was $0.22 per kWh in **both** periods, and the fixed charge
  stayed at $12.00. The rate did not change.
- Both bills reconstruct exactly from the rate: 640 x 0.22 + 12 = $152.80, and
  870 x 0.22 + 12 = $203.40.
- The increase survives daily normalisation, so a longer billing period does not
  explain it. One extra day cannot account for 230 kWh.
- Consumption history shows a trend, not a spike out of nowhere: April 590, May
  610, June 640, July 870 kWh.

**Why this matters.** The increase is fully explained by measured consumption at
an unchanged rate. That is a finding the system can defend line by line. What the
records cannot explain is *why* consumption rose inside the home, and the system
says so rather than guessing.

**Where to look.** Billing Investigation.

**In the final real run.** The evidence, usage, planner, communication and
escalation agents each stated the same reconciliation: 640 x 0.22 + 12 = 152.80,
870 x 0.22 + 12 = 203.40, and 42,690 minus 41,820 = 870 kWh, equal to billed
consumption.

---

## Stage 3. Evidence inspection

**What is happening.** Every record that bears on the meter allegation is pulled
and examined directly.

**Responsible agent.** `AccountEvidenceAgent`, with `PolicyKnowledgeAgent`
supplying the rules that govern what may be concluded.

**Evidence available.** Eight records, each addressable by identifier:

| ID | Source | What it shows |
| --- | --- | --- |
| EV-4003-01 | Billing record | Previous bill, $152.80 for 640 kWh |
| EV-4003-02 | Billing record | Current bill, $203.40 for 870 kWh |
| EV-4003-03 | Meter read | 41,820 kWh on 2026-06-30, **actual** |
| EV-4003-04 | Meter read | 42,690 kWh on 2026-07-31, **actual** |
| EV-4003-05 | Meter event log | **Empty.** No events recorded |
| EV-4003-06 | Diagnostic | Remote self test 2026-07-29, **PASS**, no tamper, no register fault |
| EV-4003-07 | Usage history | Apr 590, May 610, Jun 640, Jul 870 kWh |
| EV-4003-08 | Rate schedule | $0.22 per kWh, $12.00 fixed, unchanged |

**Decision being made.** Does anything establish a meter defect?

The decisive arithmetic: the register moved 42,690 minus 41,820 = **870 kWh**,
which equals the billed consumption **exactly**. The meter measured what the
customer was charged for. Both reads are actual rather than estimated, so no
catch-up true-up is involved. There is no register rollback. No meter event
exists. The diagnostic passed.

**Why this matters.** This is the heart of the case. The evidence does not
support a meter fault. It also does not *rule one out*, because proving a meter
healthy requires a physical test that has not been performed. A system that
concluded "the meter is fine" would be overreaching in the opposite direction.
The honest position is that the claim is **unsupported**, which is not the same
as false.

**Where to look.** Evidence Explorer.

**In the final real run.** `AccountEvidenceAgent` returned a 22-entry evidence
ledger under a strict output schema. Every value and every source record
identifier was matched mechanically to the case input. It uses its own
identifiers, such as `EVID-READ-0003-A-REG`, not the `EV-4003` identifiers of the
offline application. `PolicyKnowledgeAgent` mapped nine governed policies, none
invented. In the two earlier runs the evidence agent produced no ledger at all,
which is described in `docs/V10_CORRECTIONS_2026-09-20.md`.

---

## Stage 4. Proposed resolution

**What is happening.** A resolution and a customer message are drafted.

**Responsible agents.** `ResolutionPlannerAgent` proposes, then
`CustomerCommunicationAgent` writes the customer-facing text.

**Evidence available.** The full ledger from stage 3, plus the claim ledger being
assembled:

| Claim | Status | Cites |
| --- | --- | --- |
| CL-4003-01, the bill rose and consumption rose with it | SUPPORTED | EV-4003-01, EV-4003-02 |
| CL-4003-02, **a meter malfunction caused the high bill** | **UNSUPPORTED** | **nothing** |
| CL-4003-03, the diagnostics do not confirm meter failure | SUPPORTED | EV-4003-07, EV-4003-08 |

**Decision being made.** Whether the draft may be sent.

**Why this matters.** This is where a plausible system fails. The customer asked
for a meter fault confirmation, and the most fluent, most satisfying reply is to
give them one. A planner under pressure to be helpful will produce exactly that
draft. The claim ledger records that the meter claim cites **zero evidence** and
carries confidence `INSUFFICIENT`, which is what makes the next stage possible.

Critically, no intermediate agent output reaches the customer. All seven
investigating agents run with `autoSend` set to false in the deployed workflow
definition. Nothing is sent until the gate clears.

**Where to look.** Supervisor Review, and the UI Test Fixture view, which shows
the unsafe draft preserved and rejected.

**In the final real run.** The planner did not propose a meter-fault finding. Its
claim ledger records the meter allegation as not supported, and it ended with the
token `CASE_FOLLOWUP::HUMAN_REQUIRED`. `CustomerCommunicationAgent` wrote a
six-part message that says no evidence of over-recording was found, that remote
diagnostics do not rule everything out, that no credit has been applied, and that
a Human Billing Supervisor must approve any adjustment.

---

## Stage 5. Independent compliance

**What is happening.** A separate agent checks the draft against the evidence,
rather than the author checking its own work.

**Responsible agent.** `EvidenceComplianceAgent`.

**Evidence available.** The draft, the claim ledger, and the policies:
`POL-MTR-003` requires a meter test or a diagnostic fault record before anyone
may state a meter condition. `POL-COMM-004` governs customer-safe language.

**Decision being made.** Approve, or reject and route to a human.

The gate is deliberately narrow. It requires an exact token,
`ROUTE_DECISION::GRIDRESOLVE_APPROVED`, and escalation is the **default** branch.
Anything that is not an explicit, exact approval escalates.

**Why this matters, and the defect this found.** The gate was originally written
as:

```
Not("APPROVE" in Local.Var1497)
```

Power Fx `in` is case-insensitive substring matching. So a rejection reading
"cannot approve this unsupported meter claim" **contains** the substring
"approve", satisfied the test, and skipped the human review it existed to
enforce. Under a local text-only model the original gate skipped escalation on
**5 of 11 cases that required it**. That figure was never observed in the hosted
service. The version 5 replacement required an exact token, and on the real Power
Fx engine it did not compile either, because the workflow hands the gate a table
of message records and not text. Version 6 reads the text of the last message and
is correct on 24 of 24 adversarial outputs on the real engine:
`dotnet run --project tests/powerfx_gate`. See `docs/CORRECTION_2026-09-20.md`.

Both defects were found by reading the deployed configuration, before any money
was spent.

The live gate, in workflow v10, has three terms, and all three must hold before
anything is released: the exact approval token alone on the final line, six
readable customer fields, and a complete investigation, meaning the evidence,
usage, policy and compliance outputs are each a JSON object holding its key
field. Anything else takes the fail-closed branch to a person.

**Where to look.** Agent Workflow, and Governance control G02.

**In the final real run.** `EvidenceComplianceAgent` returned a decision object,
`decision` APPROVE, no failed checks, a summary naming the evidence identifiers,
policy identifiers and check numbers it relied on, and then the approval token
alone on the final line. All three gate terms held and the platform took the
approve branch. Compliance did not reject the final draft. The hosted fail-closed
branch was observed once, in the second run on workflow v9, where nothing was
sent to the customer. That compliance output was the token alone with no reasons,
so why it escalated is not established.

---

## Stage 6. Human escalation

**What is happening.** The case routes to a named human role.

**Responsible agent.** `EscalationCoordinatorAgent`.

**Evidence available.** The rejection reason, the unsupported claim identifier,
and the missing evidence named explicitly as
`explicit_diagnostic_evidence_of_meter_failure`.

**Decision being made.** Who decides, and what they are told meanwhile.

The reviewer role is Meter Operations Specialist. `POL-HUM-005` requires a named
reviewer. Adjustment authorisation status is `NOT_GRANTED`, and no monetary
adjustment field exists anywhere in the resolution plan.

The customer receives an interim message that commits to neither conclusion. The
offline assistant states this position directly:

> The reviewer will decide whether a field meter test is warranted. Until that
> decision is made, no one will tell you the meter is faulty and no one will tell
> you it is fine, because neither statement is supported yet.

**Why this matters.** The system's most useful output here is an escalation, not
an answer. Refusing to resolve is the correct resolution, and the customer is
told why rather than being stalled.

**Where to look.** Supervisor Review.

**In the final real run.** The message was released, and human review still
happened, because it is a separate decision. The workflow read the planner's
follow-up token, took the human follow-up branch, and ran
`EscalationCoordinatorAgent` after the release. It produced a review package with
`case_state` HUMAN_REVIEW, a six-part decision card, routing to a Billing
Supervisor with a Compliance Reviewer as fallback, and PENDING_HUMAN_REVIEW. It
made no decision for the human. The reviewer is a role, not a named person, and
nobody is actually notified: that integration is planned, not built.

---

## Stage 7. Audit record

**What is happening.** A terminal record is written on **both** paths, approval
and escalation alike.

**Responsible agent.** `CaseAuditAgent`.

**Evidence available.** The complete packet: case identifier, workflow version,
every evidence identifier, every claim identifier, every policy applied, the
compliance decision, the human review status, and the final disposition.

**Decision being made.** None. This stage decides nothing, which is the point.

**Why this matters.** A regulated billing action has to be reconstructable
afterwards by someone who was not there. The audit packet is assembled locally by
`build_audit_packet`, and its identifier sets are checked against the ledgers, so
a record cannot silently omit an item it acted on.

**Where to look.** System Status.

**In the final real run.** `CaseAuditAgent` recorded the approval token, the
APPROVE decision and its reasons, nine agents each with a received output, every
agent version as NOT_OBSERVED, its own included, RUNTIME_EXECUTED and
PENDING_HUMAN_REVIEW. The runner compares the audit with the platform's own
record of who ran and which branch was taken, and found nothing to correct. The
platform record, not the audit, is the source of truth.

---

## What a judge can verify without spending anything

| Claim | How to check | Cost |
| --- | --- | --- |
| The original routing defect is real | `python tests/test_routing_and_data.py` | $0 |
| The gate is correct on the real Power Fx engine, 105 cases | `dotnet run --project tests/powerfx_gate` | $0 |
| The live v10 workflow YAML behaves as designed on Microsoft's open-source engine | `python tests/test_workflow_engine.py` | $0 |
| The three real runs say what this page says | `python -m runner analyze --run-dir evidence/runtime/<run folder>` | $0 |
| Every synthetic record is consistent and PII free | `python tests/validate_synthetic_data.py` | $0 |
| The assistant never confirms the meter fault | `npx vitest run` in `control-center` | $0 |
| The app makes no external network call | Offline guarantee test, enforced in the suite | $0 |
| Nine agents and workflow v10 exist as described | `python tests/verify_live_config.py`, read only, needs your own Foundry resource | $0 |

---

## What this walkthrough does not claim

- It does not claim the agents produced the text shown in the seven stages. That
  text comes from the offline Control Center. What the agents produced is in
  `evidence/runtime/`, and only the notes headed "In the final real run" describe
  it.
- It does not claim the meter is healthy. That would need a physical test.
- It does not claim a compliance agent rejected a real draft. No real run did
  that for a stated reason. The rejection shown in the UI Test Fixture view is an
  **offline demonstration**, labelled `OFFLINE_DEMONSTRATION` on screen, built
  from a supplied display-only snapshot.
- It does not claim the final run took the fail-closed branch. It took the
  approve branch.
- It does not claim seven distinct runtime routes. The dataset declares seven.
  The workflow implements release or fail-closed escalation, plus a separate
  human follow-up decision after a release.
- It does not claim production readiness, or that any utility, meter, customer
  relationship or identity system is integrated. One synthetic case ran end to
  end once on v10.

The offline walkthrough above costs nothing. The three real runs cost about
**$0.13** in total, measured from returned token counts at list price. The billed
amount is not yet visible in Azure Cost Management, which is not the same as a
confirmed $0.00.

---

## A note on the figures

Every view in the application now shows the same numbers: $152.80 to $203.40,
640 to 870 kWh, over 30 and 31 day periods.

The UI test bundle originally supplied for frontend testing used different
illustrative figures for the same case identifier, $124 to $197 over 720 to 1,015
kWh in a 33 day period. Both sets were internally consistent, but showing two
bill amounts under one case identifier made the application look inconsistent,
and none of the nine supplied UI assertions depended on the figures.

The committed fixtures are therefore **derived** from the supplied originals with
the canonical figures substituted in, by `scripts/derive_ui_fixtures.py`. The
originals in `data/` are untouched and preserved for provenance, the derivation
is re-run and checked by the validator so it cannot drift, and the application
raises a visible `FIGURE DRIFT` card if the two ever disagree again.

Structure, identifiers, statuses and every honesty marker pass through the
derivation unchanged. Only figures were substituted.
