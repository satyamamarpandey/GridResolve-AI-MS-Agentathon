# GridResolve Utility Toolbox

Date: 2026-09-19
Status: IMPLEMENTED LOCALLY, NOT ATTACHED TO ANY FOUNDRY AGENT.
Source: `control-center/src/tools/index.ts`, types in `control-center/src/tools/types.ts`
Test coverage: 37 tests in `control-center/src/tools/tools.test.ts`, all passing.

## 1. Why a toolbox exists at all

All nine Foundry agents currently have **zero tools attached**. Every number they
would produce comes out of a language model as prose. For a utility billing
dispute that is the wrong division of labor: a dollar figure in a customer letter
is a regulated statement, and it should come from tested code, not from sampling.

The thirteen functions below already exist, are pure, and are tested. They are
documented here as the function tools a future Foundry or Agent Framework
deployment would register. Registering them is deliberately **not** done, because
Phase 2 freeze prohibits modifying the nine active agents, and because validating
tool calls requires model execution, which spends money.

## 2. Design rules applied to every tool

1. **Pure.** No I/O, no clock, no network, no global state. Same input, same
   output, always.
2. **Errors are values, never thrown.** Every tool returns
   `ToolResult<T> = { ok, value, errors, notes }`. An agent receives a structured
   failure it can reason about instead of an exception that kills the turn.
3. **Validate at the boundary.** Inputs are checked before use. A tool never
   trusts that the caller passed a number.
4. **No authority.** No tool writes a record, applies an adjustment, contacts a
   customer, or approves anything. Every tool is read-and-compute only.
5. **Synthetic only.** No tool reaches a production billing system. The security
   boundary is the absence of a connection, not a permission check.
6. **Deterministic cost.** Every tool is local CPU work measured in microseconds.
   None of them calls a model, so none of them costs money to run.

## 3. Tool register

### 3.1 calculate_bill_change

| Field | Value |
| --- | --- |
| Input | `previousUsd: number`, `currentUsd: number` |
| Output | `{ deltaUsd, percentChange, direction }` |
| Errors | Non-finite input, negative amount, previous of zero when a percentage is requested |
| Security boundary | Arithmetic only. No account lookup, no record write. |
| Target agent | AccountEvidenceAgent, CustomerCommunicationAgent |
| Runtime cost | Microseconds, no model call |

The headline figure a customer actually asks about. Division by zero is an error
rather than an Infinity, because "your bill rose by Infinity percent" is exactly
the kind of sentence this project exists to prevent.

### 3.2 calculate_usage_change

| Field | Value |
| --- | --- |
| Input | `previousKwh`, `currentKwh`, `previousDays`, `currentDays` |
| Output | `{ deltaKwh, percentChange, dailyPreviousKwh, dailyCurrentKwh, normalizedComparable }` |
| Errors | Non-finite or negative values, zero-day billing period |
| Security boundary | Arithmetic only |
| Target agent | UsageAnomalyAgent |
| Runtime cost | Microseconds, no model call |

Normalizes to kWh per day. Without this, a 34 day period against a 29 day period
looks like a consumption spike when it is a calendar artifact. This is the single
most common false positive in high bill investigation.

### 3.3 calculate_rate_effect

| Field | Value |
| --- | --- |
| Input | Previous and current kWh, previous and current rate components |
| Output | `{ usageEffectUsd, rateEffectUsd, fixedEffectUsd, totalExplainedUsd, dominantDriver }` |
| Errors | Non-finite or negative rates, missing rate components |
| Security boundary | Arithmetic only |
| Target agent | UsageAnomalyAgent, ResolutionPlannerAgent |
| Runtime cost | Microseconds, no model call |

Decomposes the bill change into consumption, rate and fixed-charge effects. Usage
is priced at the **previous** rate so the effects do not double count, and
`totalExplainedUsd` must reconcile with `calculate_bill_change`. When it does not
reconcile, the inputs are inconsistent and that is a finding in itself.

### 3.4 validate_meter_reads

| Field | Value |
| --- | --- |
| Input | `reads: readonly MeterRead[]` |
| Output | `{ readCount, allActual, estimatedCount, registerDeltaKwh, rollback, anomalies }` |
| Errors | Fewer than two reads, non-chronological reads, missing register values |
| Security boundary | Reads a supplied array. No meter system connection exists. |
| Target agent | AccountEvidenceAgent |
| Runtime cost | Microseconds, no model call |

Detects register rollback, which is the signature of a meter replacement or a
genuine fault. Reports whether every read is actual rather than estimated. The
register delta is then checked against billed consumption, and an exact match is
the strongest single piece of evidence against a metering error.

### 3.5 detect_estimated_trueup

| Field | Value |
| --- | --- |
| Input | `reads: readonly MeterRead[]`, `billing: readonly BillingRecord[]` |
| Output | `{ detected, reason, estimatedPeriods }` |
| Errors | Empty inputs, mismatched period coverage |
| Security boundary | Arithmetic and pattern matching only |
| Target agent | UsageAnomalyAgent |
| Runtime cost | Microseconds, no model call |

An estimated read followed by an actual read produces catch-up consumption that
lands entirely in one bill. The customer sees a spike; the cause is the previous
under-estimate. This is a leading benign explanation for a high bill and must be
ruled in or out before anyone looks at the meter hardware.

### 3.6 lookup_synthetic_policy

| Field | Value |
| --- | --- |
| Input | `policyId: string`, `policies: readonly PolicyEntry[]` |
| Output | The matching `PolicyEntry` |
| Errors | Unknown policy id, malformed id |
| Security boundary | Reads the supplied synthetic policy library only. No document store, no retrieval service, no network. |
| Target agent | PolicyKnowledgeAgent |
| Runtime cost | Microseconds, no model call |

Named `lookup_synthetic_policy` rather than `lookup_policy` on purpose. The name
carries the data classification, so a future reader cannot mistake it for a
connection to a real policy repository.

### 3.7 validate_evidence_ids

| Field | Value |
| --- | --- |
| Input | `ids: readonly string[]`, `evidence: readonly EvidenceEntry[]` |
| Output | `{ valid, missing }` |
| Errors | Non-array input |
| Security boundary | Set membership only |
| Target agent | EvidenceComplianceAgent |
| Runtime cost | Microseconds, no model call |

### 3.8 validate_policy_ids

| Field | Value |
| --- | --- |
| Input | `ids: readonly string[]`, `policies: readonly PolicyEntry[]` |
| Output | `{ valid, missing }` |
| Errors | Non-array input |
| Security boundary | Set membership only |
| Target agent | EvidenceComplianceAgent, PolicyKnowledgeAgent |
| Runtime cost | Microseconds, no model call |

### 3.9 validate_claim_ledger

| Field | Value |
| --- | --- |
| Input | `claims`, `evidence`, `policies` |
| Output | `{ assessments[], unsupportedMaterialClaims[], overallStatus }` |
| Errors | Non-array claims |
| Security boundary | Pure resolution against supplied ledgers |
| Target agent | EvidenceComplianceAgent |
| Runtime cost | Microseconds, no model call |

The most important tool in the set. Rules, in order:

- A claim citing no evidence is `UNSUPPORTED`.
- A claim citing an evidence id that does not resolve is `UNSUPPORTED`.
- A claim missing a policy citation, or citing an unresolvable policy, is
  `PARTIALLY_SUPPORTED`.
- Any `UNSUPPORTED` claim marked material forces
  `overallStatus = HUMAN_REVIEW_REQUIRED`.

This turns "is this answer grounded" from a judgement into a computation. A model
can write a fluent paragraph citing EV-4003-99; this function notices that
EV-4003-99 does not exist, and the case escalates.

### 3.10 detect_duplicate_adjustment

| Field | Value |
| --- | --- |
| Input | `proposed: Adjustment`, `existing: readonly Adjustment[]` |
| Output | `{ duplicate, matchedAdjustmentId, reason }` |
| Errors | Missing amount or period on the proposed adjustment |
| Security boundary | Comparison only. Cannot create, apply or reverse an adjustment. |
| Target agent | ResolutionPlannerAgent |
| Runtime cost | Microseconds, no model call |

Guards the failure where a case is reopened and a credit is applied twice. The
tool detects and reports; a human still authorizes.

### 3.11 calculate_case_cost

| Field | Value |
| --- | --- |
| Input | `inputTokens: number`, `outputTokens: number`, optional cached input tokens |
| Output | `{ inputUsd, outputUsd, totalUsd }` |
| Errors | Non-finite or negative token counts |
| Security boundary | Arithmetic against a constant price table |
| Target agent | CaseAuditAgent, and operations reporting |
| Runtime cost | Microseconds, no model call |

Prices against `PRICE_USD_PER_1M`, currently input $0.25, cached input $0.025 and
output $2.00 per million tokens, taken from the Azure Retail Prices API rather
than estimated. Supports POL-COST-009 by making the spend decision quantitative
before the spend happens.

### 3.12 validate_case_state

| Field | Value |
| --- | --- |
| Input | `from: CaseState`, `to: CaseState` |
| Output | `{ allowed, reason }` |
| Errors | Unknown state value |
| Security boundary | State machine validation only |
| Target agent | CaseTriageAgent, EscalationCoordinatorAgent |
| Runtime cost | Microseconds, no model call |

Prevents illegal transitions such as moving straight from intake to resolved
without passing the compliance gate.

### 3.13 build_audit_packet

| Field | Value |
| --- | --- |
| Input | Case id, workflow version, agents, evidence, policies, claims, compliance decision, correction count, human review status, final disposition |
| Output | `AuditPacket` |
| Errors | Missing case id or workflow version |
| Security boundary | Assembles a record in memory. Does not persist, transmit or sign it. |
| Target agent | CaseAuditAgent |
| Runtime cost | Microseconds, no model call |

Always sets `execution_status: "PREPARED_NOT_EXECUTED"`. That is hard-coded on
purpose: until a genuine workflow run produces a packet, no packet may imply one
happened. When real execution exists, this field becomes the honest place to
record it, and changing it will be a deliberate edit rather than an oversight.

## 4. Agent to tool mapping

| Agent | Tools it would register |
| --- | --- |
| CaseTriageAgent | validate_case_state |
| AccountEvidenceAgent | calculate_bill_change, validate_meter_reads |
| UsageAnomalyAgent | calculate_usage_change, calculate_rate_effect, detect_estimated_trueup |
| PolicyKnowledgeAgent | lookup_synthetic_policy, validate_policy_ids |
| ResolutionPlannerAgent | calculate_rate_effect, detect_duplicate_adjustment |
| CustomerCommunicationAgent | calculate_bill_change (read only, for wording accuracy) |
| EvidenceComplianceAgent | validate_evidence_ids, validate_policy_ids, validate_claim_ledger |
| EscalationCoordinatorAgent | validate_case_state |
| CaseAuditAgent | build_audit_packet, calculate_case_cost |

Note that EvidenceComplianceAgent holds the validation tools and none of the
calculators. The gate checks provenance; it does not recompute the arithmetic it
is judging. Separating those roles keeps the gate independent of the work.

## 5. Security boundary, stated once

No tool in this set:

- opens a network connection,
- reads or writes a file,
- touches a production billing, metering or CRM system,
- holds a credential, key, token or connection string,
- applies a financial adjustment,
- sends anything to a customer,
- approves a release.

The boundary is structural. These are pure functions over data handed to them, so
there is no privileged operation available to misuse, whether through prompt
injection or through a bug.

## 6. Why they are not attached

Four reasons, all standing:

1. **Phase 2 freeze.** The nine active agents must not be modified.
2. **Cost.** Validating tool calling requires model execution per tool per agent.
3. **Foundry tool contract unverified.** The exact registration schema and the
   shape of the tool-call payload for these agents have not been observed, only
   read about. Guessing it and writing it down as fact would be the kind of
   unverified claim this project refuses to make.
4. **Better target.** The Agent Framework migration is the natural place to
   register them, because orchestration there is code and the tools are already
   TypeScript. See `docs/AGENT_FRAMEWORK_MIGRATION.md`.

Execution status: PREPARED_NOT_EXECUTED_DUE_TO_ZERO_COST_CONSTRAINT.
