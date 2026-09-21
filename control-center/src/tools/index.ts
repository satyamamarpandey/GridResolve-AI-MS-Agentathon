/**
 * GridResolve deterministic business tools.
 *
 * Every financial and evidential value in the Control Center comes from here.
 * No model is asked to calculate money, usage, or provenance. Each function is
 * pure, validates its input, and returns errors as values rather than throwing.
 */
import {
  type Adjustment,
  type BillingRecord,
  type CaseState,
  type Claim,
  type ComplianceDecision,
  type EvidenceEntry,
  type MeterRead,
  type PolicyEntry,
  type RateComponents,
  type SupportStatus,
  type ToolResult,
  fail,
  money,
  ok,
  pct,
} from "./types";

const finite = (n: unknown): n is number => typeof n === "number" && Number.isFinite(n);

/* ---------------------------------------------------------------- billing */

export interface BillChange {
  readonly previousUsd: number;
  readonly currentUsd: number;
  readonly deltaUsd: number;
  readonly percentChange: number;
  readonly direction: "increase" | "decrease" | "unchanged";
}

export function calculate_bill_change(
  previousUsd: number,
  currentUsd: number,
): ToolResult<BillChange> {
  if (!finite(previousUsd) || !finite(currentUsd)) {
    return fail(["previousUsd and currentUsd must be finite numbers"]);
  }
  if (previousUsd < 0 || currentUsd < 0) return fail(["bill amounts cannot be negative"]);
  const deltaUsd = money(currentUsd - previousUsd);
  const percentChange = previousUsd === 0 ? 0 : pct(((currentUsd - previousUsd) / previousUsd) * 100);
  const notes = previousUsd === 0 ? ["previous bill is zero, percent change reported as 0"] : [];
  return ok(
    {
      previousUsd: money(previousUsd),
      currentUsd: money(currentUsd),
      deltaUsd,
      percentChange,
      direction: deltaUsd > 0 ? "increase" : deltaUsd < 0 ? "decrease" : "unchanged",
    },
    notes,
  );
}

export interface UsageChange {
  readonly previousKwh: number;
  readonly currentKwh: number;
  readonly deltaKwh: number;
  readonly percentChange: number;
  readonly dailyPreviousKwh: number | null;
  readonly dailyCurrentKwh: number | null;
}

export function calculate_usage_change(
  previousKwh: number,
  currentKwh: number,
  previousDays?: number,
  currentDays?: number,
): ToolResult<UsageChange> {
  if (!finite(previousKwh) || !finite(currentKwh)) {
    return fail(["previousKwh and currentKwh must be finite numbers"]);
  }
  if (previousKwh < 0 || currentKwh < 0) return fail(["consumption cannot be negative"]);
  const notes: string[] = [];
  let dailyPreviousKwh: number | null = null;
  let dailyCurrentKwh: number | null = null;
  if (finite(previousDays) && finite(currentDays) && previousDays > 0 && currentDays > 0) {
    dailyPreviousKwh = Math.round((previousKwh / previousDays) * 100) / 100;
    dailyCurrentKwh = Math.round((currentKwh / currentDays) * 100) / 100;
    if (previousDays !== currentDays) {
      notes.push(
        `billing periods differ in length (${previousDays} vs ${currentDays} days), compare the daily rate`,
      );
    }
  }
  return ok(
    {
      previousKwh,
      currentKwh,
      deltaKwh: currentKwh - previousKwh,
      percentChange: previousKwh === 0 ? 0 : pct(((currentKwh - previousKwh) / previousKwh) * 100),
      dailyPreviousKwh,
      dailyCurrentKwh,
    },
    notes,
  );
}

export interface RateEffect {
  readonly usageEffectUsd: number;
  readonly rateEffectUsd: number;
  readonly fixedEffectUsd: number;
  readonly totalExplainedUsd: number;
  readonly dominantDriver: "usage" | "rate" | "fixed charge" | "none";
}

/**
 * Decomposes a bill change into usage, rate and fixed-charge effects.
 * Usage effect is priced at the previous rate, so the two effects do not double count.
 */
export function calculate_rate_effect(
  previousKwh: number,
  currentKwh: number,
  previousRate: RateComponents,
  currentRate: RateComponents,
): ToolResult<RateEffect> {
  for (const [label, r] of [
    ["previousRate", previousRate],
    ["currentRate", currentRate],
  ] as const) {
    if (!r || !finite(r.energy_charge_usd_per_kwh) || !finite(r.fixed_charge_usd_per_period)) {
      return fail([`${label} must contain finite energy and fixed charges`]);
    }
  }
  if (!finite(previousKwh) || !finite(currentKwh)) return fail(["consumption must be finite"]);

  const usageEffectUsd = money((currentKwh - previousKwh) * previousRate.energy_charge_usd_per_kwh);
  const rateEffectUsd = money(
    currentKwh * (currentRate.energy_charge_usd_per_kwh - previousRate.energy_charge_usd_per_kwh),
  );
  const fixedEffectUsd = money(
    currentRate.fixed_charge_usd_per_period - previousRate.fixed_charge_usd_per_period,
  );
  const parts: ReadonlyArray<[RateEffect["dominantDriver"], number]> = [
    ["usage", Math.abs(usageEffectUsd)],
    ["rate", Math.abs(rateEffectUsd)],
    ["fixed charge", Math.abs(fixedEffectUsd)],
  ];
  const top = parts.reduce((a, b) => (b[1] > a[1] ? b : a));
  return ok({
    usageEffectUsd,
    rateEffectUsd,
    fixedEffectUsd,
    totalExplainedUsd: money(usageEffectUsd + rateEffectUsd + fixedEffectUsd),
    dominantDriver: top[1] === 0 ? "none" : top[0],
  });
}

/* ------------------------------------------------------------------ meter */

export interface MeterReadValidation {
  readonly readCount: number;
  readonly allActual: boolean;
  readonly estimatedCount: number;
  readonly registerDeltaKwh: number | null;
  readonly chronological: boolean;
  readonly rollback: boolean;
  readonly issues: readonly string[];
}

export function validate_meter_reads(reads: readonly MeterRead[]): ToolResult<MeterReadValidation> {
  if (!Array.isArray(reads)) return fail(["reads must be an array"]);
  if (reads.length === 0) return fail(["at least one meter read is required"]);

  const issues: string[] = [];
  const ids = new Set<string>();
  for (const r of reads) {
    if (!r?.record_id) issues.push("a read is missing record_id");
    else if (ids.has(r.record_id)) issues.push(`duplicate read record_id ${r.record_id}`);
    else ids.add(r.record_id);
    if (!finite(r?.register_kwh)) issues.push(`read ${r?.record_id} has a non numeric register value`);
    if (r?.read_type !== "actual" && r?.read_type !== "estimated") {
      issues.push(`read ${r?.record_id} has an unrecognized read_type`);
    }
    if (Number.isNaN(Date.parse(r?.read_date ?? ""))) {
      issues.push(`read ${r?.record_id} has an unparseable read_date`);
    }
  }

  const sorted = [...reads].sort((a, b) => Date.parse(a.read_date) - Date.parse(b.read_date));
  const chronological = sorted.every((r, i) => r.record_id === reads[i]?.record_id);
  const first = sorted[0];
  const last = sorted[sorted.length - 1];
  const registerDeltaKwh =
    reads.length >= 2 && finite(first.register_kwh) && finite(last.register_kwh)
      ? last.register_kwh - first.register_kwh
      : null;
  const rollback = registerDeltaKwh !== null && registerDeltaKwh < 0;
  if (rollback) issues.push("register value decreased between reads, which needs investigation");

  const estimatedCount = reads.filter((r) => r.read_type === "estimated").length;
  return ok({
    readCount: reads.length,
    allActual: estimatedCount === 0,
    estimatedCount,
    registerDeltaKwh,
    chronological,
    rollback,
    issues,
  });
}

export interface TrueUpDetection {
  readonly detected: boolean;
  readonly reason: string;
  readonly estimatedPeriods: readonly string[];
}

/** An estimated read followed by an actual read can produce a catch-up charge. */
export function detect_estimated_trueup(
  reads: readonly MeterRead[],
  bills: readonly BillingRecord[],
): ToolResult<TrueUpDetection> {
  if (!Array.isArray(reads) || !Array.isArray(bills)) {
    return fail(["reads and bills must both be arrays"]);
  }
  const estimatedPeriods = bills.filter((b) => b.read_type_end === "estimated").map((b) => b.record_id);
  const sorted = [...reads].sort((a, b) => Date.parse(a.read_date) - Date.parse(b.read_date));
  let followed = false;
  for (let i = 1; i < sorted.length; i += 1) {
    if (sorted[i - 1].read_type === "estimated" && sorted[i].read_type === "actual") followed = true;
  }
  const detected = followed || estimatedPeriods.length > 0;
  return ok({
    detected,
    reason: detected
      ? "an estimated read precedes an actual read, so part of this bill may be catch-up consumption"
      : "all reads are actual, so a true-up is not a supported explanation",
    estimatedPeriods,
  });
}

/* ----------------------------------------------------------------- policy */

export function lookup_synthetic_policy(
  policyId: string,
  policies: readonly PolicyEntry[],
): ToolResult<PolicyEntry> {
  if (typeof policyId !== "string" || !policyId.trim()) return fail(["policyId must be a non empty string"]);
  if (!Array.isArray(policies)) return fail(["policies must be an array"]);
  const found = policies.find((p) => p.policy_id === policyId);
  return found
    ? ok(found)
    : fail([`policy ${policyId} is not present in the synthetic policy ledger`]);
}

/* ------------------------------------------------------------- provenance */

export interface IdValidation {
  readonly requested: readonly string[];
  readonly resolved: readonly string[];
  readonly missing: readonly string[];
  readonly allResolved: boolean;
}

const validateIds = (requested: readonly string[], known: ReadonlySet<string>): IdValidation => {
  const resolved = requested.filter((id) => known.has(id));
  const missing = requested.filter((id) => !known.has(id));
  return { requested, resolved, missing, allResolved: missing.length === 0 };
};

export function validate_evidence_ids(
  ids: readonly string[],
  ledger: readonly EvidenceEntry[],
): ToolResult<IdValidation> {
  if (!Array.isArray(ids) || !Array.isArray(ledger)) return fail(["ids and ledger must be arrays"]);
  return ok(validateIds(ids, new Set(ledger.map((e) => e.evidence_id))));
}

export function validate_policy_ids(
  ids: readonly string[],
  ledger: readonly PolicyEntry[],
): ToolResult<IdValidation> {
  if (!Array.isArray(ids) || !Array.isArray(ledger)) return fail(["ids and ledger must be arrays"]);
  return ok(validateIds(ids, new Set(ledger.map((p) => p.policy_id))));
}

export interface ClaimAssessment {
  readonly claim_id: string;
  readonly statement: string;
  readonly material: boolean;
  readonly status: SupportStatus;
  readonly missingEvidenceIds: readonly string[];
  readonly missingPolicyIds: readonly string[];
  readonly reason: string;
}

export interface ClaimLedgerResult {
  readonly assessments: readonly ClaimAssessment[];
  readonly unsupportedMaterialClaims: readonly string[];
  readonly overallStatus: SupportStatus;
}

/**
 * The core provenance check. A material claim that cites no evidence, or cites
 * an evidence or policy ID that does not resolve, is UNSUPPORTED. Any unsupported
 * material claim forces the whole ledger to HUMAN_REVIEW_REQUIRED.
 */
export function validate_claim_ledger(
  claims: readonly Claim[],
  evidence: readonly EvidenceEntry[],
  policies: readonly PolicyEntry[],
): ToolResult<ClaimLedgerResult> {
  if (!Array.isArray(claims)) return fail(["claims must be an array"]);
  const knownEvidence = new Set(evidence.map((e) => e.evidence_id));
  const knownPolicy = new Set(policies.map((p) => p.policy_id));

  const assessments = claims.map((c): ClaimAssessment => {
    const evidenceIds: readonly string[] = c.evidence_ids ?? [];
    const policyIds: readonly string[] = c.policy_ids ?? [];
    const missingEvidenceIds = evidenceIds.filter((id) => !knownEvidence.has(id));
    const missingPolicyIds = policyIds.filter((id) => !knownPolicy.has(id));
    const citesEvidence = evidenceIds.length > 0;

    let status: SupportStatus;
    let reason: string;
    if (!citesEvidence) {
      status = "UNSUPPORTED";
      reason = "the claim cites no evidence";
    } else if (missingEvidenceIds.length > 0) {
      status = "UNSUPPORTED";
      reason = `evidence ${missingEvidenceIds.join(", ")} does not resolve to a ledger record`;
    } else if (missingPolicyIds.length > 0) {
      status = "PARTIALLY_SUPPORTED";
      reason = `policy ${missingPolicyIds.join(", ")} does not resolve to the policy ledger`;
    } else if ((c.policy_ids ?? []).length === 0) {
      status = "PARTIALLY_SUPPORTED";
      reason = "evidence resolves, but no governing policy is cited";
    } else {
      status = "SUPPORTED";
      reason = "all cited evidence and policy resolve to ledger records";
    }
    return {
      claim_id: c.claim_id,
      statement: c.statement,
      material: c.material,
      status,
      missingEvidenceIds,
      missingPolicyIds,
      reason,
    };
  });

  const unsupportedMaterialClaims = assessments
    .filter((a) => a.material && a.status === "UNSUPPORTED")
    .map((a) => a.claim_id);

  const overallStatus: SupportStatus =
    unsupportedMaterialClaims.length > 0
      ? "HUMAN_REVIEW_REQUIRED"
      : assessments.some((a) => a.status === "PARTIALLY_SUPPORTED")
        ? "PARTIALLY_SUPPORTED"
        : assessments.length === 0
          ? "UNSUPPORTED"
          : "SUPPORTED";

  return ok({ assessments, unsupportedMaterialClaims, overallStatus });
}

/* -------------------------------------------------------------- financial */

export interface DuplicateAdjustment {
  readonly duplicate: boolean;
  readonly matchedIds: readonly string[];
  readonly reason: string;
}

export function detect_duplicate_adjustment(
  existing: readonly Adjustment[],
  proposed: Pick<Adjustment, "period" | "amount_usd">,
): ToolResult<DuplicateAdjustment> {
  if (!Array.isArray(existing)) return fail(["existing adjustments must be an array"]);
  if (!proposed || !finite(proposed.amount_usd) || typeof proposed.period !== "string") {
    return fail(["proposed adjustment needs a period and a finite amount"]);
  }
  const matched = existing.filter(
    (a) => a.period === proposed.period && Math.abs(a.amount_usd - proposed.amount_usd) < 0.01,
  );
  return ok({
    duplicate: matched.length > 0,
    matchedIds: matched.map((a) => a.adjustment_id),
    reason: matched.length
      ? `an adjustment for ${proposed.period} at this amount already exists`
      : "no prior adjustment matches this period and amount",
  });
}

/* ------------------------------------------------------------------- cost */

export const PRICE_USD_PER_1M = {
  input: 0.25,
  cachedInput: 0.025,
  output: 2.0,
} as const;

export interface CaseCost {
  readonly inputTokens: number;
  readonly outputTokens: number;
  readonly cachedInputTokens: number;
  readonly inputCostUsd: number;
  readonly outputCostUsd: number;
  readonly cachedCostUsd: number;
  readonly totalUsd: number;
  readonly measured: boolean;
}

/**
 * Cost at the verified Azure retail price for gpt-5-mini Global Standard.
 * `measured` must be false unless the token counts came from a real run.
 */
export function calculate_case_cost(
  inputTokens: number,
  outputTokens: number,
  cachedInputTokens = 0,
  measured = false,
): ToolResult<CaseCost> {
  if (!finite(inputTokens) || !finite(outputTokens) || !finite(cachedInputTokens)) {
    return fail(["token counts must be finite numbers"]);
  }
  if (inputTokens < 0 || outputTokens < 0 || cachedInputTokens < 0) {
    return fail(["token counts cannot be negative"]);
  }
  const inputCostUsd = (inputTokens / 1e6) * PRICE_USD_PER_1M.input;
  const outputCostUsd = (outputTokens / 1e6) * PRICE_USD_PER_1M.output;
  const cachedCostUsd = (cachedInputTokens / 1e6) * PRICE_USD_PER_1M.cachedInput;
  return ok(
    {
      inputTokens,
      outputTokens,
      cachedInputTokens,
      inputCostUsd: Math.round(inputCostUsd * 1e4) / 1e4,
      outputCostUsd: Math.round(outputCostUsd * 1e4) / 1e4,
      cachedCostUsd: Math.round(cachedCostUsd * 1e4) / 1e4,
      totalUsd: Math.round((inputCostUsd + outputCostUsd + cachedCostUsd) * 1e4) / 1e4,
      measured,
    },
    measured ? [] : ["token counts are projected, not measured from a run"],
  );
}

/* ------------------------------------------------------------ case + audit */

const VALID_STATES: readonly CaseState[] = [
  "INTAKE",
  "INVESTIGATING",
  "PLANNING",
  "DRAFTING",
  "COMPLIANCE_REVIEW",
  "CORRECTION",
  "HUMAN_REVIEW",
  "APPROVED",
  "CLOSED",
  "CANNOT_RESOLVE_SAFELY",
];

export interface CaseStateValidation {
  readonly caseId: string;
  readonly state: CaseState;
  readonly terminal: boolean;
  readonly issues: readonly string[];
}

export function validate_case_state(
  caseId: string,
  state: string,
  correctionCount = 0,
): ToolResult<CaseStateValidation> {
  const issues: string[] = [];
  if (typeof caseId !== "string" || !/^SYN-CASE-\d{4}$/.test(caseId)) {
    return fail([`case id ${String(caseId)} is not a valid synthetic case identifier`]);
  }
  if (!VALID_STATES.includes(state as CaseState)) {
    return fail([`case state ${String(state)} is not a recognized state`]);
  }
  if (!finite(correctionCount) || correctionCount < 0) return fail(["correctionCount must be zero or more"]);
  if (correctionCount >= 2 && state !== "HUMAN_REVIEW" && state !== "CANNOT_RESOLVE_SAFELY") {
    issues.push("the two correction ceiling is reached, so the case must route to human review");
  }
  return ok({
    caseId,
    state: state as CaseState,
    terminal: state === "CLOSED" || state === "CANNOT_RESOLVE_SAFELY",
    issues,
  });
}

export interface AuditPacket {
  readonly case_id: string;
  readonly workflow_version: string;
  readonly participating_agents: readonly string[];
  readonly evidence_ids: readonly string[];
  readonly policy_ids: readonly string[];
  readonly claim_ids: readonly string[];
  readonly compliance_decision: ComplianceDecision | "NOT_RUN";
  readonly correction_count: number;
  readonly human_review_status: string;
  readonly final_disposition: string;
  readonly audit_completeness: "COMPLETE" | "INCOMPLETE";
  readonly execution_status: "CONFIGURED" | "PREPARED_NOT_EXECUTED" | "RUNTIME_EXECUTED" | "RUNTIME_FAILED";
  readonly generated_by: string;
}

export interface AuditInput {
  readonly caseId: string;
  readonly workflowVersion: string;
  readonly agents: readonly string[];
  readonly evidence: readonly EvidenceEntry[];
  readonly policies: readonly PolicyEntry[];
  readonly claims: readonly Claim[];
  readonly complianceDecision: ComplianceDecision | "NOT_RUN";
  readonly correctionCount: number;
  readonly humanReviewStatus: string;
  readonly finalDisposition: string;
}

/**
 * Builds the terminal audit record. execution_status is never RUNTIME_EXECUTED here,
 * because this function runs locally and no workflow execution has occurred.
 */
export function build_audit_packet(input: AuditInput): ToolResult<AuditPacket> {
  if (!input || typeof input.caseId !== "string") return fail(["a caseId is required"]);
  const required: ReadonlyArray<[string, unknown]> = [
    ["workflowVersion", input.workflowVersion],
    ["agents", input.agents],
    ["evidence", input.evidence],
    ["policies", input.policies],
    ["claims", input.claims],
  ];
  const missing = required.filter(([, v]) => v === undefined || v === null).map(([k]) => k);
  if (missing.length) return fail([`audit packet is missing ${missing.join(", ")}`]);

  const complete =
    input.evidence.length > 0 &&
    input.policies.length > 0 &&
    input.claims.length > 0 &&
    input.agents.length > 0;

  return ok(
    {
      case_id: input.caseId,
      workflow_version: input.workflowVersion,
      participating_agents: input.agents,
      evidence_ids: input.evidence.map((e) => e.evidence_id),
      policy_ids: input.policies.map((p) => p.policy_id),
      claim_ids: input.claims.map((c) => c.claim_id),
      compliance_decision: input.complianceDecision,
      correction_count: input.correctionCount,
      human_review_status: input.humanReviewStatus,
      final_disposition: input.finalDisposition,
      audit_completeness: complete ? "COMPLETE" : "INCOMPLETE",
      execution_status: "PREPARED_NOT_EXECUTED",
      generated_by: "GridResolve Control Center, local deterministic tools",
    },
    ["execution_status is PREPARED_NOT_EXECUTED because no Foundry workflow run has occurred"],
  );
}
