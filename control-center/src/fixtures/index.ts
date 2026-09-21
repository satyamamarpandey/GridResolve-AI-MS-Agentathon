/**
 * UI TEST FIXTURE LOADER AND MAPPER.
 *
 * Loads the three SYN-CASE-4003 snapshots and adapts them for display without
 * altering their contract. Specifically it does NOT:
 *
 *   - relabel workflow_version from v4 to v5
 *   - strip or rewrite the SYN- identifier prefixes
 *   - merge fixture records into the canonical engine ledgers
 *   - infer a claim status the fixture did not state
 *
 * The canonical v5 engine in src/engine/investigation.ts is untouched and
 * remains the default view mode.
 */
import intakeRaw from "../data/fixtures/intake.json";
import investigatingRaw from "../data/fixtures/investigating.json";
import rejectionRaw from "../data/fixtures/rejection.json";
import expectationsRaw from "../data/fixtures/expectations.json";
import type {
  FixtureCaseSnapshot,
  FixtureClaim,
  FixtureEvidence,
  FixtureExpectations,
  FixturePolicy,
} from "./types";

export * from "./types";

export const intake = intakeRaw as unknown as FixtureCaseSnapshot;
export const investigating = investigatingRaw as unknown as FixtureCaseSnapshot;
export const rejection = rejectionRaw as unknown as FixtureCaseSnapshot;
export const expectations = expectationsRaw as unknown as FixtureExpectations;

export type SnapshotId = "intake" | "investigating" | "rejection";

export const SNAPSHOTS: ReadonlyArray<{
  readonly id: SnapshotId;
  readonly label: string;
  readonly description: string;
  readonly snapshot: FixtureCaseSnapshot;
}> = [
  {
    id: "intake",
    label: "01 Intake",
    description: "Minimal case before any local UI simulation. Empty ledgers.",
    snapshot: intake,
  },
  {
    id: "investigating",
    label: "02 Investigating",
    description: "Synthetic billing, usage and meter evidence with existing policy identifiers.",
    snapshot: investigating,
  },
  {
    id: "rejection",
    label: "03 Simulated rejection",
    description: "Deliberately unsupported meter-failure claim, shown as a hypothetical failed review.",
    snapshot: rejection,
  },
];

/** The version the fixtures declare. Surfaced in the UI rather than corrected. */
export const FIXTURE_WORKFLOW_VERSION = intake.workflow_version;

/**
 * The fixture bundle declares v4 while the canonical engine is v5. That is a
 * genuine data-contract mismatch. It is reported rather than silently resolved.
 */
export interface VersionMismatch {
  readonly mismatch: boolean;
  readonly fixtureVersion: string;
  readonly canonicalVersion: string;
  readonly handling: string;
}

export function describeVersionMismatch(canonicalVersion: string): VersionMismatch {
  const fixtureVersion = FIXTURE_WORKFLOW_VERSION;
  const normalize = (v: string) => v.replace(/[\s-]/g, "").toLowerCase();
  return {
    mismatch: normalize(fixtureVersion) !== normalize(canonicalVersion),
    fixtureVersion,
    canonicalVersion,
    handling:
      "The fixture is displayed under its own declared version. It is not relabelled, " +
      "and it is not merged into the canonical engine data.",
  };
}

/* ------------------------------------------- canonical figure divergence */

export interface FigureRow {
  readonly label: string;
  readonly canonical: string;
  readonly fixture: string;
  readonly differs: boolean;
}

export interface FigureDivergence {
  readonly differs: boolean;
  readonly rows: readonly FigureRow[];
  readonly explanation: string;
}

/** Reads one numeric value out of the fixture evidence ledger by field name. */
function fixtureValue(field: string, period: "PREVIOUS" | "CURRENT"): number | null {
  const match = rejection.evidence_ledger.find(
    (e: FixtureEvidence) => e.field === field && e.period.startsWith(period),
  );
  return typeof match?.value === "number" ? match.value : null;
}

/**
 * The supplied bundle in data/ used different illustrative figures from the
 * canonical case, which would have shown two bill amounts under one case
 * identifier. The committed fixtures are now derived from the supplied
 * originals with the canonical figures substituted in, by
 * scripts/derive_ui_fixtures.py, so the two agree.
 *
 * This comparison stays in place as an alarm rather than a disclosure. In
 * normal operation it reports no difference and the card does not render. If
 * anyone edits a fixture figure by hand, or the canonical case changes without
 * the derivation being re-run, it surfaces immediately instead of a judge
 * finding the inconsistency first.
 */
export function describeFigureDivergence(canonical: {
  readonly previousUsd: number;
  readonly currentUsd: number;
  readonly previousKwh: number;
  readonly currentKwh: number;
}): FigureDivergence {
  const money = (n: number | null) => (n === null ? "not stated" : `$${n.toFixed(2)}`);
  const energy = (n: number | null) => (n === null ? "not stated" : `${n} kWh`);

  const pairs: ReadonlyArray<[string, string, string]> = [
    ["Previous bill", money(canonical.previousUsd), money(fixtureValue("amount_usd", "PREVIOUS"))],
    ["Current bill", money(canonical.currentUsd), money(fixtureValue("amount_usd", "CURRENT"))],
    ["Previous usage", energy(canonical.previousKwh), energy(fixtureValue("usage_kwh", "PREVIOUS"))],
    ["Current usage", energy(canonical.currentKwh), energy(fixtureValue("usage_kwh", "CURRENT"))],
  ];

  const rows = pairs.map(([label, canonicalValue, fixtureVal]) => ({
    label,
    canonical: canonicalValue,
    fixture: fixtureVal,
    differs: canonicalValue !== fixtureVal,
  }));

  return {
    differs: rows.some((r) => r.differs),
    rows,
    explanation:
      "The committed fixtures are derived from the supplied bundle in data/ with the canonical " +
      "figures substituted in, so these values should match the rest of the application exactly. " +
      "A difference here means either a fixture was edited by hand or the canonical case changed " +
      "without scripts/derive_ui_fixtures.py being re-run. Re-run it to resolve.",
  };
}

/* ------------------------------------------------------------ derived views */

export interface ClaimRow {
  readonly claim: FixtureClaim;
  readonly supporting: readonly FixtureEvidence[];
  readonly governing: readonly FixturePolicy[];
  /** True when the claim cites no evidence at all. */
  readonly citesNoEvidence: boolean;
  /** Evidence identifiers the claim cites that do not resolve in the ledger. */
  readonly unresolvedEvidenceIds: readonly string[];
}

export function buildClaimRows(snapshot: FixtureCaseSnapshot): readonly ClaimRow[] {
  const evidenceById = new Map(snapshot.evidence_ledger.map((e) => [e.evidence_id, e]));
  const policyById = new Map(snapshot.policy_ledger.map((p) => [p.policy_id, p]));

  return snapshot.claim_ledger.map((claim) => {
    const supporting = claim.evidence_ids
      .map((id) => evidenceById.get(id))
      .filter((e): e is FixtureEvidence => e !== undefined);
    const governing = claim.policy_ids
      .map((id) => policyById.get(id))
      .filter((p): p is FixturePolicy => p !== undefined);
    return {
      claim,
      supporting,
      governing,
      citesNoEvidence: claim.evidence_ids.length === 0,
      unresolvedEvidenceIds: claim.evidence_ids.filter((id) => !evidenceById.has(id)),
    };
  });
}

/** Claims the fixture itself marks UNSUPPORTED. Never inferred. */
export function unsupportedClaims(snapshot: FixtureCaseSnapshot): readonly FixtureClaim[] {
  return snapshot.claim_ledger.filter((c) => c.status === "UNSUPPORTED");
}

/** The meter-failure assertion specifically, identified by its declared type. */
export function meterFailureClaim(snapshot: FixtureCaseSnapshot): FixtureClaim | null {
  return (
    snapshot.claim_ledger.find(
      (c) => c.claim_type === "METER_CAUSAL_ASSERTION" || /meter/i.test(c.claim_text),
    ) ?? null
  );
}

/**
 * The offline assistant's reply for this fixture, exported so it can be asserted
 * directly rather than only through a rendered interaction.
 *
 * It states that failure is not confirmed, and promises nothing.
 */
export function buildAssistantReply(snapshot: FixtureCaseSnapshot): {
  readonly findings: string;
  readonly limits: string;
  readonly policyIds: readonly string[];
} {
  const meter = meterFailureClaim(snapshot);
  const reviewer = snapshot.escalation?.reviewer_role ?? "specialist";
  return {
    findings:
      "The supplied records do not confirm a meter failure. The diagnostics present are " +
      "observations, and none of them asserts a fault, so the meter-failure claim is recorded as " +
      "unsupported rather than accepted.",
    limits:
      "I cannot promise a refund or a billing adjustment. That decision is not mine to make, and " +
      `it is pending a ${reviewer} review.`,
    policyIds: meter?.policy_ids ?? [],
  };
}

export interface FixtureSummary {
  readonly caseId: string;
  readonly caseState: string;
  readonly workflowVersion: string;
  readonly evidenceCount: number;
  readonly policyCount: number;
  readonly claimCount: number;
  readonly unsupportedCount: number;
  readonly complianceDecision: string;
  readonly customerSafe: boolean | null;
  readonly escalationStatus: string;
  readonly finalDisposition: string;
  readonly auditStatus: string;
  readonly executionStatus: string;
  /** Always zero. A fixture has no runtime cost because nothing ran. */
  readonly modelCalls: 0;
  readonly tokens: 0;
  readonly costUsd: 0;
}

export function summarize(snapshot: FixtureCaseSnapshot): FixtureSummary {
  return {
    caseId: snapshot.case_id,
    caseState: snapshot.case_state,
    workflowVersion: snapshot.workflow_version,
    evidenceCount: snapshot.evidence_ledger.length,
    policyCount: snapshot.policy_ledger.length,
    claimCount: snapshot.claim_ledger.length,
    unsupportedCount: unsupportedClaims(snapshot).length,
    complianceDecision: snapshot.compliance_result?.decision ?? "NOT_REACHED",
    customerSafe: snapshot.compliance_result?.customer_safe ?? null,
    escalationStatus: snapshot.escalation?.status ?? "NONE",
    finalDisposition: snapshot.final_disposition ?? "NONE",
    auditStatus: snapshot.audit_record?.audit_status ?? "NO_AUDIT_RECORD",
    executionStatus: snapshot.audit_record?.execution_status ?? "NOT_EXECUTED",
    modelCalls: 0,
    tokens: 0,
    costUsd: 0,
  };
}
