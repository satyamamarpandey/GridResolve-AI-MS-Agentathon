# Local Trace Schema

Date: 2026-09-19
Implementation: `control-center/src/engine/trace.ts`
Tests: `control-center/src/engine/trace.test.ts`, 10 tests passing
Status: LOCAL_EXECUTION spans are real. FOUNDRY_EXECUTION is empty.
This application transmits nothing. Corrected 2026-09-21: the Foundry project
does have a connected Application Insights resource, and the platform wrote its
own spans there for the three real runs. Those are separate from this schema.
See `docs/OPERATIONS_MONITORING_AND_COST.md`.

## 1. The rule this schema exists to enforce

Observability is where fabrication is easiest and most damaging. A screenshot of
a trace waterfall is read as proof that something ran. So the schema keeps two
datasets that are never merged:

| Dataset | Contents | Current state |
| --- | --- | --- |
| `LOCAL_EXECUTION` | Spans measured from deterministic tool calls in the browser | 8 spans, real timings |
| `FOUNDRY_EXECUTION` | Spans from a real GridResolveAIWorkflow run | **Empty. Zero runs have occurred.** |

`FOUNDRY_EXECUTION_SPANS` is an empty frozen array and there is no function in
the codebase that appends to it. A span can only enter it by being read back from
an actual run. This is enforced by test, not by convention:

```
it("keeps the Foundry execution dataset empty", ...)
it("never mixes a Foundry span into the local trace", ...)
```

## 2. Span schema

Field names follow the OpenTelemetry span model, so these records could be
exported to a collector unchanged if one ever existed.

| Field | Type | Meaning |
| --- | --- | --- |
| `source` | `LOCAL_EXECUTION` or `FOUNDRY_EXECUTION` | Which dataset the span belongs to. Never inferred. |
| `case_id` | string | Synthetic case, `SYN-CASE-NNNN` |
| `trace_id` | string | One per investigation |
| `span_id` | string | Unique within the trace |
| `parent_span_id` | string or null | `null` only for the root |
| `operation` | string | The tool or stage that ran |
| `start_time_unix_ms` | number | Measured, from `performance.timeOrigin + performance.now()` |
| `end_time_unix_ms` | number | Measured |
| `duration_ms` | number | Exactly `end - start`, asserted by test |
| `status` | `OK`, `ERROR`, `UNSET` | Real outcome of the call |
| `attributes` | map | See below |

### Attributes

| Attribute | Meaning |
| --- | --- |
| `gridresolve.tool.deterministic` | Always `true` on local spans |
| `gridresolve.agent` | Which agent would own this operation in production |
| `gridresolve.workflow.version` | `GridResolveAIWorkflow v5` |
| `gridresolve.mode` | `DETERMINISTIC_OFFLINE` |
| `gridresolve.compliance.decision` | Root span only |
| `gridresolve.final_disposition` | Root span only |
| `gridresolve.evidence.count`, `.claim.count` | On the compliance span |
| `gen_ai.usage.total_tokens` | Always `0`, asserted by test on every span |

The `gen_ai.*` prefix is the OpenTelemetry generative AI semantic convention. It
is present and set to zero rather than omitted, because an explicit zero is a
stronger statement than a missing field.

## 3. Summary record

Emitted alongside the spans, carrying exactly the fields requested:

| Field | Current value |
| --- | --- |
| `case_id` | `SYN-CASE-4003` |
| `trace_id` | `local-syn-case-4003` |
| `span_count` | 8 |
| `total_duration_ms` | Measured per page load, sub-millisecond |
| `evidence_count` | 8 |
| `policy_count` | 5 in scope |
| `claim_count` | 6 |
| `compliance_result` | `HUMAN_REVIEW_REQUIRED` |
| `final_disposition` | `HELD_FOR_HUMAN_REVIEW` |
| `model_calls` | 0 |
| `tokens_consumed` | 0 |
| `cost_usd` | 0 |

## 4. Span tree, as actually produced

```
gridresolve.local_investigation            root
  |- calculate_bill_change                 AccountEvidenceAgent
  |- calculate_usage_change                UsageAnomalyAgent
  |- calculate_rate_effect                 UsageAnomalyAgent
  |- validate_meter_reads                  AccountEvidenceAgent
  |- detect_estimated_trueup               UsageAnomalyAgent
  |- validate_claim_ledger                 EvidenceComplianceAgent
  |- build_audit_packet                    CaseAuditAgent
```

The tree is flat under the root on purpose. The real workflow is sequential, so
drawing nested spans would imply an orchestration depth that does not exist.

## 5. What these spans do and do not prove

Prove:

- The deterministic pipeline executes end to end.
- Each tool completes without error.
- Real wall-clock cost of the deterministic path, which is sub-millisecond.
- The compliance decision and final disposition the local engine reaches.
- That zero tokens were consumed.

Do not prove:

- Anything about agent behavior. No agent ran.
- Anything about model latency, quality or token use.
- That the deployed workflow routes the same way at runtime. The local engine
  mirrors the v5 rule and is separately tested against Power Fx semantics, but a
  mirror is not an observation.

## 6. Production path

To populate `FOUNDRY_EXECUTION` honestly:

1. Obtain authorization to spend.
2. Run GridResolveAIWorkflow v5 once against `SYN-CASE-4003`.
3. Read back the run record and map it into this schema, preserving real
   timestamps and real token counts.
4. Set `source: "FOUNDRY_EXECUTION"` on those spans only.
5. Leave the local spans untouched and unmerged.

Application Insights would be the production collector. I provisioned nothing
for this application. The resource that came with the Foundry project already
receives the platform's spans, which I found on 2026-09-21. The schema is deliberately collector-shaped so that adding an
exporter later is configuration rather than a rewrite.

Execution status: PREPARED_NOT_EXECUTED_DUE_TO_ZERO_COST_CONSTRAINT.
