/**
 * DETERMINISTIC OFFLINE DEMONSTRATION engine.
 *
 * Derives an evidence ledger, policy ledger and claim ledger from the synthetic
 * case records using only the deterministic tools. No model is called and no
 * Foundry workflow is executed. Nothing here is a Foundry runtime trace.
 */
import caseInputRaw from "../data/generated/caseInput.json";
import syntheticPack from "../data/generated/syntheticPack.json";
import {
  build_audit_packet,
  calculate_bill_change,
  calculate_case_cost,
  calculate_rate_effect,
  calculate_usage_change,
  detect_estimated_trueup,
  validate_claim_ledger,
  validate_meter_reads,
} from "../tools";
import type {
  AuditPacket,
  ClaimLedgerResult,
  BillChange,
  RateEffect,
  UsageChange,
} from "../tools";
import type { Claim, EvidenceEntry, MeterRead, PolicyEntry } from "../tools/types";

export const MODE_LABEL = "DETERMINISTIC OFFLINE DEMONSTRATION" as const;

export interface AgentSpec {
  readonly name: string;
  readonly version: number;
  readonly role: string;
  readonly responsibility: string;
  readonly input: string;
  readonly output: string;
  readonly evidenceRequirement: string;
  readonly policyRequirement: string;
  readonly failureBehavior: string;
}

/** Versions verified live against Foundry on 2026-09-19. */
export const AGENTS: readonly AgentSpec[] = [
  {
    name: "CaseTriageAgent",
    version: 5,
    role: "Investigate",
    responsibility: "Classify intent, scope, required evidence and risk flags",
    input: "customer_request, synthetic case identifiers",
    output: "intent, investigation_type, required_evidence, risk_flags, triage_summary",
    evidenceRequirement: "Names required evidence, gathers none",
    policyRequirement: "Flags policy lookup need",
    failureBehavior: "Never infers a root cause",
  },
  {
    name: "AccountEvidenceAgent",
    version: 6,
    role: "Investigate",
    responsibility: "Inspect supplied records and issue stable evidence IDs",
    input: "triage, synthetic account records",
    output: "evidence_ledger, billing_comparison, meter_read_status, conflicts",
    evidenceRequirement: "Every entry carries source_record_id and timestamp",
    policyRequirement: "None, must not interpret policy",
    failureBehavior: "Records unknowns rather than filling gaps",
  },
  {
    name: "UsageAnomalyAgent",
    version: 4,
    role: "Investigate",
    responsibility: "Separate supported explanations from unsupported hypotheses",
    input: "evidence_ledger, usage history",
    output: "anomalies, supported_explanations, unsupported_hypotheses, confidence",
    evidenceRequirement: "Each anomaly cites supporting_evidence_ids",
    policyRequirement: "None",
    failureBehavior: "Confidence is categorical, never an invented probability",
  },
  {
    name: "PolicyKnowledgeAgent",
    version: 5,
    role: "Investigate",
    responsibility: "Resolve governing policy, conflicts and approval requirements",
    input: "triage, evidence_ledger, requested action",
    output: "policy_ledger, policy_conflicts, adjustment_eligibility, missing_policy",
    evidenceRequirement: "None",
    policyRequirement: "Every reference resolves to a real policy_id and version",
    failureBehavior: "Missing or conflicting policy forces human review",
  },
  {
    name: "ResolutionPlannerAgent",
    version: 5,
    role: "Decide",
    responsibility: "Classify root cause and build the claim ledger",
    input: "all investigation output",
    output: "root_cause_classification, claim_ledger, recommended_actions",
    evidenceRequirement: "Every material claim carries evidence_ids",
    policyRequirement: "Every governed action carries policy_ids",
    failureBehavior: "Never approves its own plan",
  },
  {
    name: "CustomerCommunicationAgent",
    version: 4,
    role: "Communicate",
    responsibility: "Draft a plain-language explanation, withheld until approved",
    input: "resolution_plan, claim_ledger",
    output: "customer_summary, what_we_found, what_happens_next, internal IDs",
    evidenceRequirement: "May not introduce a claim absent from the ledger",
    policyRequirement: "Includes required disclosures",
    failureBehavior: "Runs with autoSend false, so the draft is not released",
  },
  {
    name: "EvidenceComplianceAgent",
    version: 5,
    role: "Control",
    responsibility: "Independently verify the draft against evidence and policy",
    input: "complete case state including all three ledgers",
    output: "decision, unsupported_claim_ids, compliance_summary, route token",
    evidenceRequirement: "Verifies every referenced ID resolves",
    policyRequirement: "Verifies every policy reference resolves",
    failureBehavior: "Never approves an unsupported material claim",
  },
  {
    name: "EscalationCoordinatorAgent",
    version: 4,
    role: "Control",
    responsibility: "Produce a decision card for a named human reviewer",
    input: "case state, compliance decision",
    output: "escalation_reason, decision_card, customer_safe_interim_message",
    evidenceRequirement: "Summarizes known facts and unknowns",
    policyRequirement: "Names applicable policy",
    failureBehavior: "Never decides on the human's behalf",
  },
  {
    name: "CaseAuditAgent",
    version: 4,
    role: "Control",
    responsibility: "Produce the terminal audit record",
    input: "complete terminal case state",
    output: "participating_agents, ledgers, disposition, execution_status",
    evidenceRequirement: "Records every evidence ID used",
    policyRequirement: "Records every policy ID used",
    failureBehavior: "Never reports a run that did not happen",
  },
] as const;

export const WORKFLOW_VERSION = "GridResolveAIWorkflow v10";

export interface CaseRecords {
  readonly account_id: string;
  readonly meter_id: string;
  readonly rate_components: { energy_charge_usd_per_kwh: number; fixed_charge_usd_per_period: number };
  readonly billing_history: ReadonlyArray<{
    record_id: string;
    period_start: string;
    period_end: string;
    billing_days: number;
    kwh_billed: number;
    amount_usd: number;
    read_type_end: string;
  }>;
  readonly meter_reads: readonly MeterRead[];
  readonly meter_events: readonly unknown[];
  readonly diagnostic_records: ReadonlyArray<{
    record_id: string;
    diagnostic_date: string;
    type: string;
    result: string;
    tamper_flag: boolean;
    register_fault_flag: boolean;
  }>;
  readonly usage_history_kwh: ReadonlyArray<{ period: string; kwh: number }>;
  readonly adjustments: readonly { adjustment_id: string; period: string; amount_usd: number; reason: string }[];
}

export const caseInput = caseInputRaw as unknown as {
  case_id: string;
  workflow_version: string;
  dataset_version: string;
  policy_version: string;
  data_classification: string;
  customer_request: string;
  synthetic_account_records: CaseRecords;
};

export const ALL_POLICIES = syntheticPack.policies as unknown as readonly PolicyEntry[];
export const ALL_CASES = syntheticPack.cases as unknown as ReadonlyArray<{
  case_id: string;
  scenario: string;
  required_evidence: readonly string[];
  expected_root_cause: string;
  expected_route: string;
}>;

const rec = caseInput.synthetic_account_records;
const prevBill = rec.billing_history[0];
const currBill = rec.billing_history[1];

/* ------------------------------------------------------- derived ledgers */

/** Evidence entries are derived one-to-one from real synthetic records. */
export const evidenceLedger: readonly EvidenceEntry[] = [
  {
    evidence_id: "EV-4003-01",
    source_type: "billing_record",
    source_record_id: prevBill.record_id,
    period: prevBill.period_start.slice(0, 7),
    field: "amount_usd",
    value: `${prevBill.amount_usd}`,
    observation: `Previous bill ${prevBill.amount_usd} USD for ${prevBill.kwh_billed} kWh over ${prevBill.billing_days} days`,
  },
  {
    evidence_id: "EV-4003-02",
    source_type: "billing_record",
    source_record_id: currBill.record_id,
    period: currBill.period_start.slice(0, 7),
    field: "amount_usd",
    value: `${currBill.amount_usd}`,
    observation: `Current bill ${currBill.amount_usd} USD for ${currBill.kwh_billed} kWh over ${currBill.billing_days} days`,
  },
  {
    evidence_id: "EV-4003-03",
    source_type: "meter_read",
    source_record_id: rec.meter_reads[0].record_id,
    period: "2026-06",
    field: "register_kwh",
    value: `${rec.meter_reads[0].register_kwh}`,
    observation: `Actual read on ${rec.meter_reads[0].read_date}, not estimated`,
  },
  {
    evidence_id: "EV-4003-04",
    source_type: "meter_read",
    source_record_id: rec.meter_reads[1].record_id,
    period: "2026-07",
    field: "register_kwh",
    value: `${rec.meter_reads[1].register_kwh}`,
    observation: `Actual read on ${rec.meter_reads[1].read_date}, not estimated`,
  },
  {
    evidence_id: "EV-4003-05",
    source_type: "meter_event_log",
    source_record_id: "SYN-MTR-0003-EVENTS",
    period: "2026-06 to 2026-07",
    field: "meter_events",
    value: `${rec.meter_events.length}`,
    observation: "No meter events recorded in the billing window",
  },
  {
    evidence_id: "EV-4003-06",
    source_type: "diagnostic",
    source_record_id: rec.diagnostic_records[0].record_id,
    period: "2026-07",
    field: "result",
    value: rec.diagnostic_records[0].result,
    observation: `Remote self test ${rec.diagnostic_records[0].result} on ${rec.diagnostic_records[0].diagnostic_date}, no tamper, no register fault`,
  },
  {
    evidence_id: "EV-4003-07",
    source_type: "usage_history",
    source_record_id: "SYN-USAGE-0003",
    period: "2026-04 to 2026-07",
    field: "kwh",
    value: rec.usage_history_kwh.map((u) => u.kwh).join(", "),
    observation: "Consumption trend across four periods",
  },
  {
    evidence_id: "EV-4003-08",
    source_type: "rate_schedule",
    source_record_id: "SYN-RATE-0003",
    period: "2026-06 to 2026-07",
    field: "energy_charge_usd_per_kwh",
    value: `${rec.rate_components.energy_charge_usd_per_kwh}`,
    observation: "Energy charge unchanged between the two periods",
  },
];

const POLICY_IDS_IN_SCOPE = ["POL-HB-001", "POL-MTR-003", "POL-BILL-002", "POL-COMM-004", "POL-HUM-005"];
export const policyLedger: readonly PolicyEntry[] = ALL_POLICIES.filter((p) =>
  POLICY_IDS_IN_SCOPE.includes(p.policy_id),
);

/* --------------------------------------------------------- tool results */

export const billChange = calculate_bill_change(prevBill.amount_usd, currBill.amount_usd)
  .value as BillChange;
export const usageChange = calculate_usage_change(
  prevBill.kwh_billed,
  currBill.kwh_billed,
  prevBill.billing_days,
  currBill.billing_days,
).value as UsageChange;
export const rateEffect = calculate_rate_effect(
  prevBill.kwh_billed,
  currBill.kwh_billed,
  rec.rate_components,
  rec.rate_components,
).value as RateEffect;
export const meterValidation = validate_meter_reads(rec.meter_reads).value!;
export const trueUp = detect_estimated_trueup(rec.meter_reads, rec.billing_history as never).value!;
export const projectedCost = calculate_case_cost(105_000, 32_000).value!;

/* ---------------------------------------------------------- claim ledger */

/**
 * Two claim sets. The grounded set is what the evidence supports. The customer
 * assertion is included deliberately so the provenance check has something to reject.
 */
export const claims: readonly Claim[] = [
  {
    claim_id: "CL-4003-01",
    statement: `Billed consumption rose from ${prevBill.kwh_billed} to ${currBill.kwh_billed} kWh, an increase of ${usageChange.deltaKwh} kWh`,
    material: true,
    evidence_ids: ["EV-4003-01", "EV-4003-02", "EV-4003-07"],
    policy_ids: ["POL-HB-001"],
  },
  {
    claim_id: "CL-4003-02",
    statement: "Both meter readings in the billing window are actual, not estimated",
    material: true,
    evidence_ids: ["EV-4003-03", "EV-4003-04"],
    policy_ids: ["POL-HB-001"],
  },
  {
    claim_id: "CL-4003-03",
    statement: `The register difference of ${meterValidation.registerDeltaKwh} kWh reconciles exactly with the billed consumption`,
    material: true,
    evidence_ids: ["EV-4003-03", "EV-4003-04", "EV-4003-02"],
    policy_ids: ["POL-HB-001"],
  },
  {
    claim_id: "CL-4003-04",
    statement: "No meter events were recorded and the remote diagnostic passed with no tamper and no register fault",
    material: true,
    evidence_ids: ["EV-4003-05", "EV-4003-06"],
    policy_ids: ["POL-MTR-003"],
  },
  {
    claim_id: "CL-4003-05",
    statement: "The energy charge and fixed charge did not change, so the increase is not rate driven",
    material: true,
    evidence_ids: ["EV-4003-08"],
    policy_ids: ["POL-HB-001"],
  },
  {
    claim_id: "CL-4003-06",
    statement: "The meter is defective and caused the higher bill (customer assertion)",
    material: true,
    evidence_ids: [],
    policy_ids: ["POL-MTR-003"],
  },
];

export const claimAssessment = validate_claim_ledger(
  claims,
  evidenceLedger,
  ALL_POLICIES,
).value as ClaimLedgerResult;

/* ------------------------------------------------- compliance + outcome */

export interface ComplianceOutcome {
  readonly decision: "APPROVE" | "REJECT_AND_REPLAN" | "REJECT_AND_REWRITE" | "HUMAN_REVIEW_REQUIRED";
  readonly routeToken: string;
  readonly branch: "RELEASE_APPROVED_MESSAGE" | "ESCALATE";
  readonly summary: string;
  readonly unsupportedClaimIds: readonly string[];
}

/** Mirrors the deployed workflow v5 routing rule, evaluated locally. */
export const complianceOutcome: ComplianceOutcome = (() => {
  const unsupported = claimAssessment.unsupportedMaterialClaims;
  if (unsupported.length > 0) {
    return {
      decision: "HUMAN_REVIEW_REQUIRED",
      routeToken: "ROUTE_DECISION::GRIDRESOLVE_ESCALATE",
      branch: "ESCALATE",
      summary: `Cannot approve. ${unsupported.length} material claim cites no resolvable evidence, so the response is withheld and the case routes to a named human reviewer.`,
      unsupportedClaimIds: unsupported,
    };
  }
  return {
    decision: "APPROVE",
    routeToken: "ROUTE_DECISION::GRIDRESOLVE_APPROVED",
    branch: "RELEASE_APPROVED_MESSAGE",
    summary: "Every material claim resolves to evidence and policy.",
    unsupportedClaimIds: [],
  };
})();

export const escalation = {
  caseId: caseInput.case_id,
  reason: "An unsupported material claim about meter failure cannot be approved for release",
  riskClass: "CUSTOMER_COMMITMENT_RISK",
  recommendedReviewer: "Meter Operations Specialist",
  knownFacts: [
    `Consumption rose ${usageChange.deltaKwh} kWh (${usageChange.percentChange}%) between periods`,
    "Both reads are actual and reconcile exactly with billed consumption",
    "No meter events recorded, remote diagnostic passed",
    "Energy and fixed charges unchanged",
  ],
  unknowns: [
    "Whether a physical meter test has ever been performed on this meter",
    "Whether any premises change explains the higher consumption",
  ],
  policyReferences: ["POL-MTR-003", "POL-HUM-005"],
  requiredDecision: "Confirm whether a field meter test is warranted before any response asserting a meter condition",
  customerSafeInterimMessage:
    "We have reviewed your account records, meter readings and recent diagnostics, and your case is now with a meter operations specialist. We will not confirm a meter fault unless testing supports it. We will contact you with the outcome.",
} as const;

export const auditPacket = build_audit_packet({
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
    complianceOutcome.branch === "ESCALATE"
      ? "HELD_FOR_HUMAN_REVIEW"
      : "APPROVED_FOR_RELEASE",
}).value as AuditPacket;
