/**
 * Supervisor feedback loop model, mirrored from integration/supervisor_feedback.py.
 * Everything here is an OFFLINE_SIMULATION. No human review has been recorded, so
 * no override rate and no review-time reduction can be reported. No network, no model.
 */

export type RecordKind = "ACTUAL_HUMAN_REVIEW" | "OFFLINE_SIMULATION";
export type Agreement = "AGREE" | "DISAGREE";

export interface HumanReviewRecord {
  readonly case_id: string;
  readonly evidence_package_ref: string;
  readonly agent_recommendation: string;
  readonly human_decision: string;
  readonly agreement: Agreement;
  readonly review_started_at: string;
  readonly review_completed_at: string;
  readonly review_duration_seconds: number | null;
  readonly duration_note: string;
  readonly override_reason: string;
  readonly reviewer_comments: string;
  readonly final_disposition: string;
  readonly reviewer_principal_id: string;
  readonly reviewer_role: string;
  readonly record_kind: RecordKind;
}

export interface NotMeasured {
  readonly metric: string;
  readonly reason: string;
  readonly actual_records: number;
  readonly simulated_records: number;
}

export interface OverrideRate {
  readonly rate: number;
  readonly actual_records: number;
  readonly overrides: number;
  readonly simulated_excluded: number;
}

/** Derived, never supplied, exactly as the Python module does it. */
export const deriveAgreement = (recommendation: string, decision: string): Agreement =>
  recommendation.trim().toLowerCase() === decision.trim().toLowerCase() ? "AGREE" : "DISAGREE";

/** One simulated example. It is a fixture written by hand, not a decision anyone made. */
export const SIMULATED_EXAMPLE: HumanReviewRecord = {
  case_id: "SYN-CASE-4003",
  evidence_package_ref: "escalation package, run 2 (workflow v9), simulated review",
  agent_recommendation: "ESCALATED_TO_HUMAN",
  human_decision: "ESCALATED_TO_HUMAN",
  agreement: deriveAgreement("ESCALATED_TO_HUMAN", "ESCALATED_TO_HUMAN"),
  review_started_at: "2026-09-23T00:00:00+00:00",
  review_completed_at: "2026-09-23T00:01:30+00:00",
  review_duration_seconds: 90,
  duration_note: "measured from the two recorded timestamps of a simulated review, not a real one",
  override_reason: "",
  reviewer_comments:
    "Offline fixture. The run 2 escalation carried no reasons, so a real reviewer would have had to reconstruct them.",
  final_disposition: "PENDING_HUMAN_REVIEW",
  reviewer_principal_id: "human-supervisor-sim",
  reviewer_role: "Billing Supervisor",
  record_kind: "OFFLINE_SIMULATION",
};

export const RECORDS: readonly HumanReviewRecord[] = [SIMULATED_EXAMPLE];

/** Mirrors override_rate(): a value exists only once an ACTUAL_HUMAN_REVIEW record exists. */
export const overrideRate = (records: readonly HumanReviewRecord[]): OverrideRate | NotMeasured => {
  const actual = records.filter((r) => r.record_kind === "ACTUAL_HUMAN_REVIEW");
  const simulated = records.length - actual.length;
  if (actual.length === 0) {
    return {
      metric: "supervisor_override_rate",
      reason: "No actual human decision has been recorded. Simulated records are excluded from the rate.",
      actual_records: 0,
      simulated_records: simulated,
    };
  }
  const overrides = actual.filter((r) => r.agreement === "DISAGREE").length;
  return { rate: overrides / actual.length, actual_records: actual.length, overrides, simulated_excluded: simulated };
};

/** Mirrors review_time_reduction() with no baseline: always not measured. */
export const reviewTimeReduction = (records: readonly HumanReviewRecord[]): NotMeasured => ({
  metric: "review_time_reduction",
  reason:
    "No comparable baseline with provenance exists. A baseline is never invented and simulated durations are never used.",
  actual_records: records.filter((r) => r.record_kind === "ACTUAL_HUMAN_REVIEW" && r.review_duration_seconds !== null)
    .length,
  simulated_records: records.filter((r) => r.record_kind === "OFFLINE_SIMULATION").length,
});

export const RULES: readonly string[] = [
  "Only a session resolved to a human review role may record a decision. An agent, the workflow service and an auditor are refused, and the refusal is written to the audit chain.",
  "One record per case and evidence package. A second record for the same pair is refused.",
  "A missing decision, a missing timestamp, or a completion before the start is refused. Nothing is defaulted.",
  "Agreement is derived from the recommendation and the decision. A disagreement must carry an override reason.",
  "Every accepted record is appended to the per-case hash-chained audit record with the reviewer as the actor.",
  "The record kind, ACTUAL_HUMAN_REVIEW or OFFLINE_SIMULATION, is a field on the record itself.",
];
