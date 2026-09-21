import { describe, expect, it, vi } from "vitest";
import {
  ADAPTER_STATUS,
  DEFAULT_CONFIG,
  EXECUTION_CONFIRMATION_PHRASE,
  LIVE_FOUNDRY_ENABLED,
  buildCostWarning,
  executeWorkflow,
  validateConfig,
  validateRequest,
  validateResponse,
} from "./foundryAdapter";

const validRequest = {
  case_id: "SYN-CASE-4003",
  workflow_version: "GridResolveAIWorkflow v10",
  synthetic_case_payload: { customer_statement: "my bill doubled" },
  execution_confirmation: EXECUTION_CONFIRMATION_PHRASE,
  cost_acknowledged_usd: 0.09,
};

describe("live foundry adapter", () => {
  it("is disabled by default", () => {
    expect(LIVE_FOUNDRY_ENABLED).toBe(false);
    expect(ADAPTER_STATUS.state).toBe("DISABLED_BY_DEFAULT");
    expect(ADAPTER_STATUS.observed_response_shape).toBe(false);
  });

  it("refuses to execute even with a fully valid request and correct confirmation", async () => {
    const transport = vi.fn();
    const result = await executeWorkflow(validRequest, {
      confirmation: EXECUTION_CONFIRMATION_PHRASE,
      transport,
    });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.error.kind).toBe("DISABLED");
    // The decisive assertion: nothing reached the network.
    expect(transport).not.toHaveBeenCalled();
  });

  it("never attempts a network call from any entry point while disabled", async () => {
    const transport = vi.fn();
    for (const confirmation of ["", "yes", "approve", EXECUTION_CONFIRMATION_PHRASE]) {
      await executeWorkflow(validRequest, { confirmation, transport });
    }
    expect(transport).not.toHaveBeenCalled();
  });

  it("ships no credential and no configured endpoint", () => {
    expect(ADAPTER_STATUS.credential_in_bundle).toBe(false);
    expect(DEFAULT_CONFIG.baseUrl).toBe("");
    expect(DEFAULT_CONFIG.project).toBe("");
    expect(DEFAULT_CONFIG.brokerPath.startsWith("/")).toBe(true);
  });

  it("rejects an unconfigured endpoint", () => {
    const issues = validateConfig(DEFAULT_CONFIG);
    expect(issues).toContain("baseUrl is not configured");
    expect(issues).toContain("project is not configured");
  });

  it("requires https for the base url", () => {
    const issues = validateConfig({ ...DEFAULT_CONFIG, baseUrl: "http://example.com", project: "p" });
    expect(issues).toContain("baseUrl must use https");
  });

  it("accepts a well formed synthetic request", () => {
    expect(validateRequest(validRequest)).toHaveLength(0);
  });

  it("rejects a non synthetic case id", () => {
    const issues = validateRequest({ ...validRequest, case_id: "ACCT-100244387" });
    expect(issues.some((i) => i.includes("synthetic identifier"))).toBe(true);
  });

  it("rejects a payload carrying a production-shaped identifier", () => {
    const issues = validateRequest({
      ...validRequest,
      synthetic_case_payload: { account: "ACCT-100244387" },
    });
    expect(issues.some((i) => i.includes("production-shaped"))).toBe(true);
  });

  it("rejects a payload carrying a credential-shaped string", () => {
    const issues = validateRequest({
      ...validRequest,
      synthetic_case_payload: { note: "api_key=abc123" },
    });
    expect(issues.some((i) => i.includes("credential-shaped"))).toBe(true);
  });

  it("validates a response shape without assuming it was observed", () => {
    expect(validateResponse(null)).toEqual(["response is not an object"]);
    expect(validateResponse({})).toEqual(["run_id missing", "status missing", "messages missing or not an array"]);
    expect(validateResponse({ run_id: "r1", status: "completed", messages: [] })).toHaveLength(0);
  });

  it("builds a cost warning that names the amount and is not reversible", () => {
    const warning = buildCostWarning(0.0912);
    expect(warning.agentInvocations).toBe(9);
    expect(warning.reversible).toBe(false);
    expect(warning.headline).toContain("$0.0912");
    expect(warning.detail).toContain(EXECUTION_CONFIRMATION_PHRASE);
    expect(warning.detail).toContain("cannot be refunded");
  });

  it("requires the exact confirmation phrase, not a paraphrase", () => {
    expect(EXECUTION_CONFIRMATION_PHRASE).toBe("APPROVE ONE SYNTHETIC DEMO RUN");
    expect(buildCostWarning(1).detail).not.toContain("approve one synthetic demo run");
  });
});
