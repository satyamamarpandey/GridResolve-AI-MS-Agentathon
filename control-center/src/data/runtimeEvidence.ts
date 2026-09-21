/**
 * The three genuine Foundry runs, as exported from evidence/runtime by
 * scripts/export_runtime_evidence.py. This application ran none of them and
 * calls no model. Nothing in this file is typed in: it only gives the export a
 * shape and a few labels.
 */
import raw from "./generated/runtimeEvidence.json";

export interface RuntimeAgent {
  readonly agent: string;
  readonly version: string;
  readonly output_chars: number;
  readonly healthy: boolean;
  readonly problems: readonly string[];
}

export interface RuntimeUsage {
  readonly input_tokens: number;
  readonly cached_input_tokens: number;
  readonly output_tokens: number;
  readonly reasoning_tokens: number;
  readonly total_tokens: number;
}

export interface RuntimeLedger {
  readonly status: string;
  readonly count: number;
  readonly problems: readonly string[];
}

export interface RuntimeCompliance {
  readonly token: string;
  readonly final_line: string;
  readonly decision: string | null;
  readonly reasons_given: boolean;
  readonly failed_checks: number | null;
  readonly human_review_required: boolean | null;
  readonly summary_sentences: readonly string[];
  readonly summary_sentences_omitted: number;
  readonly evidence_ids_cited: readonly string[];
  readonly policy_ids_cited: readonly string[];
}

export interface RuntimeRoute {
  readonly observed: string;
  readonly gate_evaluated: boolean;
  readonly audit_ran: boolean;
}

export interface RuntimeRelease {
  readonly outcome: string;
  readonly customer_ready: boolean;
  readonly released_chars: number;
  readonly text: string;
  readonly equals_composed_draft: boolean;
}

export interface RuntimeDecisionCard {
  readonly parts: number;
  readonly known_facts: number;
  readonly unknowns: number;
  readonly applicable_policies: number;
}

export interface RuntimeHumanReview {
  readonly planner_token: string;
  readonly planner_resolution_status: string | null;
  readonly follow_up_observed: string;
  readonly follow_up_gate_evaluated: boolean;
  readonly findings: readonly string[];
  readonly package_produced: boolean;
  readonly recommended_reviewer: string | null;
  readonly routing_target: string | null;
  readonly routing_fallback: string | null;
  readonly disposition: string | null;
  readonly case_state: string | null;
  readonly decision_card: RuntimeDecisionCard | null;
}

export interface RuntimeAudit {
  readonly parsed: boolean;
  readonly accurate: boolean;
  readonly findings: readonly string[];
}

export interface RuntimeRun {
  readonly evidence_folder: string;
  readonly case_id: string;
  readonly case_sha256: string;
  readonly response_id: string;
  readonly final_status: string;
  readonly workflow_version: string;
  readonly started_at: string;
  readonly elapsed_seconds: number;
  readonly stream_events: number;
  readonly conversation_items: number;
  readonly agents: readonly RuntimeAgent[];
  readonly agents_invoked: number;
  readonly agents_healthy: number;
  readonly agents_not_observed: readonly string[];
  readonly investigation_complete: boolean;
  readonly usage: RuntimeUsage;
  readonly provisional_usd: number;
  readonly evidence_ledger: RuntimeLedger;
  readonly policy_mapping: RuntimeLedger;
  readonly compliance: RuntimeCompliance;
  readonly route: RuntimeRoute;
  readonly release: RuntimeRelease;
  readonly human_review: RuntimeHumanReview;
  readonly audit: RuntimeAudit;
}

export interface RuntimeAcceptanceItem {
  readonly number: number;
  readonly title: string;
  readonly verdict: string;
}

export interface RuntimeAcceptance {
  readonly criteria: number;
  readonly passed: number;
  readonly failed: number;
  readonly not_observable: number;
  readonly evidence_folder: string;
  readonly evidence_ledger_entries: number;
  readonly policies_mapped: number;
  readonly plan: string;
  readonly result: string;
  readonly items: readonly RuntimeAcceptanceItem[];
}

export interface RuntimeEvidenceFile {
  readonly content_kind: string;
  readonly generated_by: string;
  readonly source: string;
  readonly pricing: {
    readonly input_usd_per_million: number;
    readonly output_usd_per_million: number;
    readonly basis: string;
  };
  readonly runs: readonly RuntimeRun[];
  readonly totals: {
    readonly runs: number;
    readonly input_tokens: number;
    readonly output_tokens: number;
    readonly provisional_usd: number;
  };
  readonly final_acceptance: RuntimeAcceptance;
}

export const RUNTIME_EVIDENCE: RuntimeEvidenceFile = raw;

/** The last recorded run is the acceptance run. Earlier ones are numbered. */
export function runLabel(run: RuntimeRun, runs: readonly RuntimeRun[] = RUNTIME_EVIDENCE.runs): string {
  const index = runs.findIndex((r) => r.evidence_folder === run.evidence_folder);
  return index === runs.length - 1 ? "Final run" : `Run ${index + 1}`;
}

/** One line on what reached the customer, worded from the recorded release outcome. */
export function releaseSummary(run: RuntimeRun): string {
  const { outcome } = run.release;
  if (outcome === "DELIVERED_CUSTOMER_MESSAGE") return "A readable six-part message";
  if (outcome === "UNEVALUATED_EXPRESSION") return "An unevaluated expression, a defect";
  if (outcome === "NOT_RELEASED") {
    return run.compliance.reasons_given ? "Nothing, fail-closed" : "Nothing, fail-closed, no reasons given";
  }
  return outcome;
}
