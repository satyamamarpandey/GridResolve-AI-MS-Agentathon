/**
 * DISABLED Live Foundry adapter for GridResolveAIWorkflow v10.
 *
 * This module CANNOT execute the workflow as written. `LIVE_FOUNDRY_ENABLED` is
 * false, there is no credential anywhere in this bundle, and every entry point
 * refuses before it would reach the network.
 *
 * Security contract, non negotiable:
 *   - No API key, subscription key, connection string or access token appears in
 *     this file or anywhere else in the browser bundle.
 *   - The browser never talks to Foundry directly. It talks to a backend broker
 *     that holds a Microsoft Entra identity and performs the call server side.
 *   - The browser therefore cannot execute the workflow even if this flag were
 *     flipped, because it has nothing to authenticate with. That is intentional
 *     defense in depth rather than an oversight.
 *
 * Verification status: the exact request and response shapes for executing a
 * Foundry workflow have NOT been observed. Executing one costs money, and
 * probing the API to discover the response format would itself be an execution.
 * The interfaces below are therefore declared and marked
 * AWAITING_RUNTIME_VERIFICATION. They are a contract to fill in, not a
 * description of observed behavior.
 */

/** Master switch. Flipping this alone does not enable execution. */
export const LIVE_FOUNDRY_ENABLED = false as const;

export const ADAPTER_STATUS = {
  state: "DISABLED_BY_DEFAULT",
  verification: "AWAITING_RUNTIME_VERIFICATION",
  reason:
    "Executing GridResolveAIWorkflow v10 calls gpt-5-mini across nine agents and costs money. No run has been authorized.",
  observed_response_shape: false,
  credential_in_bundle: false,
} as const;

/* ------------------------------------------------------------------ config */

export interface FoundryEndpointConfig {
  /** Project endpoint, for example https://<resource>.services.ai.azure.com */
  readonly baseUrl: string;
  /** Foundry project name. */
  readonly project: string;
  /** Workflow agent name. */
  readonly workflowName: string;
  /** API version string, for example "v1". */
  readonly apiVersion: string;
  /** Backend broker path. The browser calls this, never Foundry directly. */
  readonly brokerPath: string;
  /** Hard timeout for a single attempt, milliseconds. */
  readonly timeoutMs: number;
}

/**
 * Configuration is supplied at runtime by the host, never compiled in.
 * These defaults are non secret identifiers and placeholders only.
 */
export const DEFAULT_CONFIG: FoundryEndpointConfig = {
  baseUrl: "",
  project: "",
  workflowName: "GridResolveAIWorkflow",
  apiVersion: "v1",
  brokerPath: "/api/foundry/run",
  timeoutMs: 120_000,
};

/* ------------------------------------------------------------- data shapes */

export interface WorkflowRunRequest {
  readonly case_id: string;
  readonly workflow_version: string;
  readonly synthetic_case_payload: Readonly<Record<string, unknown>>;
  /** Must be the literal confirmation phrase. Checked, not trusted. */
  readonly execution_confirmation: string;
  /** Operator acknowledgement of the projected cost. */
  readonly cost_acknowledged_usd: number;
}

/** AWAITING_RUNTIME_VERIFICATION. Field names are a contract, not an observation. */
export interface WorkflowRunResponse {
  readonly run_id: string;
  readonly status: string;
  readonly messages: readonly { readonly role: string; readonly content: string }[];
  readonly usage?: {
    readonly input_tokens?: number;
    readonly output_tokens?: number;
    readonly total_tokens?: number;
  };
}

export type AdapterError =
  | { readonly kind: "DISABLED"; readonly message: string }
  | { readonly kind: "NOT_CONFIGURED"; readonly message: string }
  | { readonly kind: "INVALID_REQUEST"; readonly message: string; readonly issues: readonly string[] }
  | { readonly kind: "NOT_CONFIRMED"; readonly message: string }
  | { readonly kind: "TIMEOUT"; readonly message: string }
  | { readonly kind: "TRANSPORT"; readonly message: string }
  | { readonly kind: "INVALID_RESPONSE"; readonly message: string; readonly issues: readonly string[] };

export type AdapterResult<T> =
  | { readonly ok: true; readonly value: T }
  | { readonly ok: false; readonly error: AdapterError };

/* ------------------------------------------------------------ cost warning */

export const EXECUTION_CONFIRMATION_PHRASE = "APPROVE ONE SYNTHETIC DEMO RUN" as const;

export interface CostWarning {
  readonly agentInvocations: number;
  readonly estimatedUsd: number;
  readonly reversible: false;
  readonly headline: string;
  readonly detail: string;
}

export function buildCostWarning(estimatedUsd: number): CostWarning {
  return {
    agentInvocations: 9,
    estimatedUsd,
    reversible: false,
    headline: `This run calls gpt-5-mini across nine agents and costs about $${estimatedUsd.toFixed(4)}.`,
    detail:
      "Tokens are billed the moment the run starts and cannot be refunded or cancelled mid run. " +
      `Type ${EXECUTION_CONFIRMATION_PHRASE} to proceed. Anything else cancels.`,
  };
}

/* -------------------------------------------------------------- validation */

export function validateConfig(config: FoundryEndpointConfig): readonly string[] {
  const issues: string[] = [];
  if (!config.baseUrl) issues.push("baseUrl is not configured");
  else if (!/^https:\/\//.test(config.baseUrl)) issues.push("baseUrl must use https");
  if (!config.project) issues.push("project is not configured");
  if (!config.workflowName) issues.push("workflowName is not configured");
  if (!config.brokerPath.startsWith("/")) issues.push("brokerPath must be a same-origin path");
  if (!Number.isFinite(config.timeoutMs) || config.timeoutMs <= 0) issues.push("timeoutMs must be positive");
  return issues;
}

export function validateRequest(request: WorkflowRunRequest): readonly string[] {
  const issues: string[] = [];
  if (!/^SYN-CASE-\d{4}$/.test(request.case_id ?? "")) {
    issues.push("case_id must be a synthetic identifier matching SYN-CASE-NNNN");
  }
  if (!request.workflow_version) issues.push("workflow_version is required");
  if (!request.synthetic_case_payload || typeof request.synthetic_case_payload !== "object") {
    issues.push("synthetic_case_payload must be an object");
  }
  if (!Number.isFinite(request.cost_acknowledged_usd) || request.cost_acknowledged_usd < 0) {
    issues.push("cost_acknowledged_usd must be a non negative number");
  }
  const serialized = JSON.stringify(request.synthetic_case_payload ?? {});
  if (/\b(ACCT|MTR)-\d{6,}\b/.test(serialized)) {
    issues.push("payload contains a production-shaped account or meter identifier");
  }
  if (/(api[_-]?key|bearer\s|access_token|client_secret)/i.test(serialized)) {
    issues.push("payload contains a credential-shaped string");
  }
  return issues;
}

/** Response validation. Shape is unverified, so this checks minimum viability only. */
export function validateResponse(raw: unknown): readonly string[] {
  const issues: string[] = [];
  if (raw === null || typeof raw !== "object") {
    return ["response is not an object"];
  }
  const r = raw as Partial<WorkflowRunResponse>;
  if (typeof r.run_id !== "string" || !r.run_id) issues.push("run_id missing");
  if (typeof r.status !== "string" || !r.status) issues.push("status missing");
  if (!Array.isArray(r.messages)) issues.push("messages missing or not an array");
  return issues;
}

/* ---------------------------------------------------------------- execute */

export interface ExecuteOptions {
  readonly config?: FoundryEndpointConfig;
  readonly confirmation?: string;
  /** Injected for testing. Never defaults to a real network call while disabled. */
  readonly transport?: (url: string, init: RequestInit) => Promise<Response>;
}

/**
 * Refuses in every reachable case. Ordering is deliberate: the disabled check
 * runs first, so no other input can route around it.
 *
 * There is no retry. A failed paid call must never be repeated automatically,
 * because an automatic retry spends money a second time without a decision.
 */
export async function executeWorkflow(
  request: WorkflowRunRequest,
  options: ExecuteOptions = {},
): Promise<AdapterResult<WorkflowRunResponse>> {
  if (!LIVE_FOUNDRY_ENABLED) {
    return {
      ok: false,
      error: {
        kind: "DISABLED",
        message:
          "Live Foundry execution is disabled. Enabling it requires a backend broker with a Microsoft Entra identity, an explicit operator confirmation, and authorization to spend.",
      },
    };
  }

  /* istanbul ignore next: unreachable while LIVE_FOUNDRY_ENABLED is false */
  const config = options.config ?? DEFAULT_CONFIG;
  const configIssues = validateConfig(config);
  if (configIssues.length > 0) {
    return {
      ok: false,
      error: { kind: "NOT_CONFIGURED", message: "adapter is not configured", issues: configIssues } as AdapterError,
    };
  }

  if (options.confirmation !== EXECUTION_CONFIRMATION_PHRASE) {
    return {
      ok: false,
      error: { kind: "NOT_CONFIRMED", message: "the exact execution confirmation phrase was not supplied" },
    };
  }

  const requestIssues = validateRequest(request);
  if (requestIssues.length > 0) {
    return {
      ok: false,
      error: { kind: "INVALID_REQUEST", message: "request failed validation", issues: requestIssues },
    };
  }

  const transport = options.transport ?? fetch;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), config.timeoutMs);

  try {
    // Same-origin broker call. No credential is attached here, because the
    // browser holds none. The broker authenticates server side.
    const response = await transport(config.brokerPath, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
      signal: controller.signal,
      credentials: "same-origin",
    });

    if (!response.ok) {
      return {
        ok: false,
        error: { kind: "TRANSPORT", message: `broker returned HTTP ${response.status}. No retry was attempted.` },
      };
    }

    const parsed: unknown = await response.json();
    const responseIssues = validateResponse(parsed);
    if (responseIssues.length > 0) {
      return {
        ok: false,
        error: { kind: "INVALID_RESPONSE", message: "response failed validation", issues: responseIssues },
      };
    }
    return { ok: true, value: parsed as WorkflowRunResponse };
  } catch (error: unknown) {
    if (error instanceof Error && error.name === "AbortError") {
      return {
        ok: false,
        error: {
          kind: "TIMEOUT",
          message: `no response within ${config.timeoutMs} ms. Tokens may still have been spent. No retry was attempted.`,
        },
      };
    }
    return {
      ok: false,
      error: {
        kind: "TRANSPORT",
        message: error instanceof Error ? error.message : "unknown transport failure",
      },
    };
  } finally {
    clearTimeout(timer);
  }
}
