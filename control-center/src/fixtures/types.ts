/**
 * UI TEST FIXTURE TYPES.
 *
 * These mirror the shape of `gridresolve_case_state.schema.json` as supplied in
 * the UI test bundle, which declares `workflow_version: "GridResolveAIWorkflow-v4"`.
 *
 * They are deliberately SEPARATE from the canonical engine types in
 * `src/tools/types.ts`. The fixture bundle's own README is explicit about this:
 *
 *   "do not silently relabel a v4 case state as v5"
 *
 * So nothing here is renamed, renumbered or upgraded. The fixture keeps its v4
 * label and its SYN- prefixed identifiers, and the UI shows both verbatim. A
 * mapper adapts the shape for display; it never rewrites the contract.
 */

export type FixtureCaseState =
  | "INTAKE"
  | "INVESTIGATING"
  | "PLANNING"
  | "COMPLIANCE_REVIEW"
  | "SIMULATED_REJECTION"
  | "ESCALATED"
  | "RESOLVED";

export type FixtureClaimStatus = "SUPPORTED" | "UNSUPPORTED" | "PARTIALLY_SUPPORTED";

export interface FixtureEvidence {
  readonly evidence_id: string;
  readonly source_type: string;
  readonly source_record_id: string;
  readonly period: string;
  readonly field: string;
  readonly value: string | number | boolean | null;
  readonly observation: string;
  readonly source_timestamp: string;
  readonly data_version: string;
  readonly freshness_status: string;
}

export interface FixturePolicy {
  readonly policy_id: string;
  readonly policy_version: string;
  readonly section: string | null;
  readonly rule: string;
  readonly applies_to: readonly string[];
  readonly effect_on_resolution: string;
  readonly conflict_status: string;
}

export interface FixtureClaim {
  readonly claim_id: string;
  readonly claim_text: string;
  readonly claim_type: string;
  readonly source_agent: string;
  readonly evidence_ids: readonly string[];
  readonly policy_ids: readonly string[];
  readonly confidence: string;
  readonly status: FixtureClaimStatus;
}

export interface FixtureComplianceResult {
  readonly decision: string;
  readonly groundedness: string;
  readonly unsupported_claim_ids: readonly string[];
  readonly policy_ids: readonly string[];
  readonly missing_evidence: readonly string[];
  readonly customer_safe: boolean;
  readonly execution_status: string;
}

export interface FixtureEscalation {
  readonly status: string;
  readonly reviewer_role: string;
  readonly reason: string;
  readonly authorization_status: string;
  readonly synthetic_ui_only: boolean;
}

export interface FixtureAuditRecord {
  readonly audit_status: string;
  readonly execution_status: string;
  readonly case_id: string;
  readonly evidence_ids: readonly string[];
  readonly claim_ids: readonly string[];
  readonly policy_ids: readonly string[];
  readonly note: string;
}

export interface FixtureTriage {
  readonly intent?: string;
  readonly meter_concern?: boolean;
  readonly requested_action?: string;
  readonly display_status?: string;
}

export interface FixtureCaseSnapshot {
  readonly case_id: string;
  readonly workflow_version: string;
  readonly case_state: FixtureCaseState | string;
  readonly dataset_version: string;
  readonly policy_version: string;
  readonly customer_request: string;
  readonly triage: FixtureTriage;
  readonly evidence_ledger: readonly FixtureEvidence[];
  readonly policy_ledger: readonly FixturePolicy[];
  readonly claim_ledger: readonly FixtureClaim[];
  readonly resolution_plan: unknown | null;
  readonly customer_message: string | null;
  readonly compliance_result: FixtureComplianceResult | null;
  readonly correction_count: number;
  readonly escalation: FixtureEscalation | null;
  readonly final_disposition: string | null;
  readonly audit_record: FixtureAuditRecord | null;
}

export interface FixtureAssertion {
  readonly view: string;
  readonly check: string;
}

export interface FixtureExpectations {
  readonly test_fixture: string;
  readonly classification: string;
  readonly execution_status: string;
  readonly purpose: string;
  readonly expected_ui_assertions: readonly FixtureAssertion[];
  readonly expected_root_cause: string;
  readonly expected_route: string;
  readonly note: string;
}

/** The label every mocked runtime pane must display, per the bundle README. */
/**
 * Carries the exact OFFLINE_DEMONSTRATION token so that a reader of the screen,
 * a screenshot or the rendered HTML cannot mistake the simulated compliance
 * rejection for output from a real EvidenceComplianceAgent run.
 */
export const FIXTURE_BANNER =
  "OFFLINE_DEMONSTRATION • Synthetic UI Simulation • Not Executed" as const;
export const FIXTURE_STATUS = "SIMULATED_UI_DISPLAY_ONLY" as const;
export const FIXTURE_EXECUTION = "NOT_EXECUTED" as const;
