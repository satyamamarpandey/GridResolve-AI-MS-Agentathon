/**
 * OpenTelemetry-compatible local trace schema.
 *
 * Two datasets exist and they are never merged.
 *
 *   LOCAL_EXECUTION   real spans, timed from actual deterministic tool calls in
 *                     this browser. These are genuine measurements.
 *   FOUNDRY_EXECUTION spans from a real GridResolveAIWorkflow run. Three real
 *                     runs happened. Foundry sent its own spans to the
 *                     Application Insights resource connected to the project.
 *                     This app does not import them. This dataset stays empty,
 *                     and nothing in this file may ever populate it with
 *                     invented spans.
 *
 * Field names follow the OpenTelemetry span model so that these records could be
 * exported to a collector unchanged. This app has no collector and transmits
 * nothing. The Application Insights resource that came with the Foundry project
 * is separate from this file.
 */
import {
  build_audit_packet,
  calculate_bill_change,
  calculate_rate_effect,
  calculate_usage_change,
  detect_estimated_trueup,
  validate_claim_ledger,
  validate_meter_reads,
} from "../tools";
import {
  AGENTS,
  ALL_POLICIES,
  WORKFLOW_VERSION,
  caseInput,
  claims,
  complianceOutcome,
  evidenceLedger,
  policyLedger,
} from "./investigation";

export type TraceSource = "LOCAL_EXECUTION" | "FOUNDRY_EXECUTION";
export type SpanStatus = "OK" | "ERROR" | "UNSET";

/** One span. Field names mirror the OpenTelemetry span model. */
export interface TraceSpan {
  readonly source: TraceSource;
  readonly case_id: string;
  readonly trace_id: string;
  readonly span_id: string;
  readonly parent_span_id: string | null;
  readonly operation: string;
  readonly start_time_unix_ms: number;
  readonly end_time_unix_ms: number;
  readonly duration_ms: number;
  readonly status: SpanStatus;
  readonly attributes: Readonly<Record<string, string | number | boolean>>;
}

export interface TraceSummary {
  readonly source: TraceSource;
  readonly case_id: string;
  readonly trace_id: string;
  readonly span_count: number;
  readonly total_duration_ms: number;
  readonly evidence_count: number;
  readonly policy_count: number;
  readonly claim_count: number;
  readonly compliance_result: string;
  readonly final_disposition: string;
  readonly model_calls: number;
  readonly tokens_consumed: number;
  readonly cost_usd: number;
}

export interface LocalTrace {
  readonly summary: TraceSummary;
  readonly spans: readonly TraceSpan[];
}

let counter = 0;
const nextSpanId = (): string => `span-${(++counter).toString(16).padStart(4, "0")}`;

const now = (): number =>
  typeof performance !== "undefined" && typeof performance.now === "function"
    ? performance.timeOrigin + performance.now()
    : Date.now();

/**
 * Runs the deterministic pipeline and records what actually happened.
 * Durations are measured, not assigned.
 */
export function buildLocalTrace(): LocalTrace {
  counter = 0;
  const traceId = `local-${caseInput.case_id.toLowerCase()}`;
  const spans: TraceSpan[] = [];
  const rec = caseInput.synthetic_account_records;
  const [prev, curr] = rec.billing_history;

  const rootStart = now();
  const rootId = nextSpanId();

  const record = <T>(
    operation: string,
    parent: string | null,
    attributes: Record<string, string | number | boolean>,
    work: () => T,
  ): T => {
    const spanId = nextSpanId();
    const start = now();
    let status: SpanStatus = "OK";
    let result: T;
    try {
      result = work();
    } catch {
      status = "ERROR";
      throw new Error(`local span failed: ${operation}`);
    }
    const end = now();
    spans.push({
      source: "LOCAL_EXECUTION",
      case_id: caseInput.case_id,
      trace_id: traceId,
      span_id: spanId,
      parent_span_id: parent,
      operation,
      start_time_unix_ms: start,
      end_time_unix_ms: end,
      duration_ms: end - start,
      status,
      attributes: { ...attributes, "gridresolve.tool.deterministic": true, "gen_ai.usage.total_tokens": 0 },
    });
    return result;
  };

  record("calculate_bill_change", rootId, { "gridresolve.agent": "AccountEvidenceAgent" }, () =>
    calculate_bill_change(prev.amount_usd, curr.amount_usd),
  );
  record("calculate_usage_change", rootId, { "gridresolve.agent": "UsageAnomalyAgent" }, () =>
    calculate_usage_change(prev.kwh_billed, curr.kwh_billed, prev.billing_days, curr.billing_days),
  );
  record("calculate_rate_effect", rootId, { "gridresolve.agent": "UsageAnomalyAgent" }, () =>
    calculate_rate_effect(prev.kwh_billed, curr.kwh_billed, rec.rate_components, rec.rate_components),
  );
  record("validate_meter_reads", rootId, { "gridresolve.agent": "AccountEvidenceAgent" }, () =>
    validate_meter_reads(rec.meter_reads),
  );
  record("detect_estimated_trueup", rootId, { "gridresolve.agent": "UsageAnomalyAgent" }, () =>
    detect_estimated_trueup(rec.meter_reads, rec.billing_history as never),
  );
  record(
    "validate_claim_ledger",
    rootId,
    {
      "gridresolve.agent": "EvidenceComplianceAgent",
      "gridresolve.claim.count": claims.length,
      "gridresolve.evidence.count": evidenceLedger.length,
    },
    () => validate_claim_ledger(claims, evidenceLedger, ALL_POLICIES),
  );
  record(
    "build_audit_packet",
    rootId,
    { "gridresolve.agent": "CaseAuditAgent" },
    () =>
      build_audit_packet({
        caseId: caseInput.case_id,
        workflowVersion: WORKFLOW_VERSION,
        agents: AGENTS.map((a) => `${a.name} v${a.version}`),
        evidence: evidenceLedger,
        policies: policyLedger,
        claims,
        complianceDecision: complianceOutcome.decision,
        correctionCount: 0,
        humanReviewStatus: complianceOutcome.branch === "ESCALATE" ? "REQUIRED" : "NOT_REQUIRED",
        finalDisposition:
          complianceOutcome.branch === "ESCALATE" ? "HELD_FOR_HUMAN_REVIEW" : "APPROVED_FOR_RELEASE",
      }),
  );

  const rootEnd = now();
  const finalDisposition =
    complianceOutcome.branch === "ESCALATE" ? "HELD_FOR_HUMAN_REVIEW" : "APPROVED_FOR_RELEASE";

  spans.unshift({
    source: "LOCAL_EXECUTION",
    case_id: caseInput.case_id,
    trace_id: traceId,
    span_id: rootId,
    parent_span_id: null,
    operation: "gridresolve.local_investigation",
    start_time_unix_ms: rootStart,
    end_time_unix_ms: rootEnd,
    duration_ms: rootEnd - rootStart,
    status: "OK",
    attributes: {
      "gridresolve.workflow.version": WORKFLOW_VERSION,
      "gridresolve.mode": "DETERMINISTIC_OFFLINE",
      "gridresolve.compliance.decision": complianceOutcome.decision,
      "gridresolve.final_disposition": finalDisposition,
      "gen_ai.usage.total_tokens": 0,
    },
  });

  return {
    spans,
    summary: {
      source: "LOCAL_EXECUTION",
      case_id: caseInput.case_id,
      trace_id: traceId,
      span_count: spans.length,
      total_duration_ms: rootEnd - rootStart,
      evidence_count: evidenceLedger.length,
      policy_count: policyLedger.length,
      claim_count: claims.length,
      compliance_result: complianceOutcome.decision,
      final_disposition: finalDisposition,
      model_calls: 0,
      tokens_consumed: 0,
      cost_usd: 0,
    },
  };
}

/**
 * Foundry execution traces.
 *
 * Empty by construction. A span may only enter this dataset by being read back
 * from a real GridResolveAIWorkflow run. There is no code path that synthesizes
 * one, and adding such a path would be fabricating runtime evidence.
 */
export const FOUNDRY_EXECUTION_SPANS: readonly TraceSpan[] = [];

export const FOUNDRY_EXECUTION_STATUS = {
  source: "FOUNDRY_EXECUTION" as const,
  span_count: 0,
  platform_span_count: 61,
  workflow_runs: 3,
  status: "RUNS_RECORDED_SPANS_HELD_BY_PLATFORM",
  reason:
    "Three real workflow runs happened. Foundry recorded 61 spans for them in the Application Insights resource that was connected when the project was created. I read them back on 2026-09-21, read only. This app imports none of them. A redacted summary is in evidence/platform_telemetry.",
  how_to_populate:
    "Import spans only from a read-only export of the platform record. Spans are never reconstructed after the fact.",
} as const;
