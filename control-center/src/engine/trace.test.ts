import { describe, expect, it } from "vitest";
import {
  FOUNDRY_EXECUTION_SPANS,
  FOUNDRY_EXECUTION_STATUS,
  buildLocalTrace,
} from "./trace";
import { FOUNDRY_RUNS, foundryTotals } from "../data/foundryRuns";

describe("local trace", () => {
  it("emits a root span plus one span per deterministic operation", () => {
    const trace = buildLocalTrace();
    expect(trace.spans.length).toBe(8);
    expect(trace.spans[0].parent_span_id).toBeNull();
    expect(trace.spans[0].operation).toBe("gridresolve.local_investigation");
  });

  it("parents every non root span to the root", () => {
    const trace = buildLocalTrace();
    const root = trace.spans[0];
    for (const span of trace.spans.slice(1)) {
      expect(span.parent_span_id).toBe(root.span_id);
    }
  });

  it("uses unique span ids and a single trace id", () => {
    const trace = buildLocalTrace();
    const ids = new Set(trace.spans.map((s) => s.span_id));
    expect(ids.size).toBe(trace.spans.length);
    expect(new Set(trace.spans.map((s) => s.trace_id)).size).toBe(1);
  });

  it("measures real durations rather than assigning them", () => {
    const trace = buildLocalTrace();
    for (const span of trace.spans) {
      expect(span.duration_ms).toBeGreaterThanOrEqual(0);
      expect(span.end_time_unix_ms).toBeGreaterThanOrEqual(span.start_time_unix_ms);
      expect(span.duration_ms).toBe(span.end_time_unix_ms - span.start_time_unix_ms);
    }
    // The root must span at least as long as the longest child.
    const root = trace.spans[0];
    const longestChild = Math.max(...trace.spans.slice(1).map((s) => s.duration_ms));
    expect(root.duration_ms).toBeGreaterThanOrEqual(longestChild);
  });

  it("labels every local span as LOCAL_EXECUTION and never as Foundry", () => {
    const trace = buildLocalTrace();
    for (const span of trace.spans) {
      expect(span.source).toBe("LOCAL_EXECUTION");
    }
    expect(trace.summary.source).toBe("LOCAL_EXECUTION");
  });

  it("reports zero model calls, zero tokens and zero cost", () => {
    const { summary, spans } = buildLocalTrace();
    expect(summary.model_calls).toBe(0);
    expect(summary.tokens_consumed).toBe(0);
    expect(summary.cost_usd).toBe(0);
    for (const span of spans) {
      expect(span.attributes["gen_ai.usage.total_tokens"]).toBe(0);
    }
  });

  it("carries the case, evidence, policy and claim counts on the summary", () => {
    const { summary } = buildLocalTrace();
    expect(summary.case_id).toMatch(/^SYN-CASE-\d{4}$/);
    expect(summary.evidence_count).toBeGreaterThan(0);
    expect(summary.policy_count).toBeGreaterThan(0);
    expect(summary.claim_count).toBeGreaterThan(0);
    expect(summary.compliance_result).toBe("HUMAN_REVIEW_REQUIRED");
    expect(summary.final_disposition).toBe("HELD_FOR_HUMAN_REVIEW");
  });

  it("is reproducible in shape across repeated builds", () => {
    const a = buildLocalTrace();
    const b = buildLocalTrace();
    expect(a.spans.map((s) => s.operation)).toEqual(b.spans.map((s) => s.operation));
    expect(a.summary.compliance_result).toBe(b.summary.compliance_result);
  });

  it("keeps the Foundry span dataset empty, because this app imports no platform spans", () => {
    expect(FOUNDRY_EXECUTION_SPANS).toHaveLength(0);
    expect(FOUNDRY_EXECUTION_STATUS.span_count).toBe(0);
  });

  it("reports the three real runs without inventing spans for them", () => {
    expect(FOUNDRY_EXECUTION_STATUS.workflow_runs).toBe(foundryTotals().runs);
    expect(FOUNDRY_EXECUTION_STATUS.workflow_runs).toBe(3);
    expect(FOUNDRY_EXECUTION_STATUS.status).toBe("RUNS_RECORDED_SPANS_HELD_BY_PLATFORM");
    expect(FOUNDRY_EXECUTION_STATUS.platform_span_count).toBe(61);
    expect(FOUNDRY_EXECUTION_STATUS.reason).not.toMatch(/no span was recorded/i);
    expect(FOUNDRY_EXECUTION_STATUS.reason).not.toMatch(/never been executed/i);
  });

  it("sums the recorded runs to the provisional total", () => {
    const totals = foundryTotals();
    expect(totals.inputTokens).toBe(186614);
    expect(totals.outputTokens).toBe(42155);
    expect(totals.provisionalUsd).toBe(0.1311);
    expect(FOUNDRY_RUNS[FOUNDRY_RUNS.length - 1].auditFindings).toBe(0);
  });

  it("never mixes a Foundry span into the local trace", () => {
    const trace = buildLocalTrace();
    expect(trace.spans.some((s) => (s.source as string) === "FOUNDRY_EXECUTION")).toBe(false);
  });
});

describe("data version integrity", () => {
  it("the synthetic case input declares the same workflow version the engine uses", async () => {
    const { caseInput, WORKFLOW_VERSION } = await import("./investigation");
    expect(caseInput.workflow_version).toBe(WORKFLOW_VERSION);
  });

  it("no artifact still references the superseded v4 workflow as current", async () => {
    const { caseInput, WORKFLOW_VERSION } = await import("./investigation");
    expect(WORKFLOW_VERSION).toBe("GridResolveAIWorkflow v10");
    expect(caseInput.workflow_version).not.toContain("v4");
  });
});
