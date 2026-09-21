/**
 * The three genuine Foundry executions of SYN-CASE-4003, as recorded facts.
 *
 * This application never calls Foundry. Every value here is derived from
 * generated/runtimeEvidence.json, which scripts/export_runtime_evidence.py
 * builds from the captured records in evidence/runtime, so the status page can
 * say what was run without pretending to have run it. Cost is derived from
 * returned token counts at list price and is provisional.
 */
import { RUNTIME_EVIDENCE, releaseSummary, runLabel, type RuntimeRun } from "./runtimeEvidence";

export type ComplianceToken = "APPROVED" | "ESCALATE";

export interface FoundryRun {
  readonly label: string;
  readonly workflowVersion: string;
  readonly evidenceFolder: string;
  readonly agentsThatDidTheirWork: string;
  readonly complianceToken: ComplianceToken;
  readonly sentToCustomer: string;
  readonly auditFindings: number;
  readonly inputTokens: number;
  readonly outputTokens: number;
  readonly provisionalUsd: number;
}

function complianceToken(run: RuntimeRun): ComplianceToken {
  const { token } = run.compliance;
  if (token === "APPROVED" || token === "ESCALATE") return token;
  throw new Error(`Unrecognised compliance token in ${run.evidence_folder}: ${token}`);
}

function toFoundryRun(run: RuntimeRun): FoundryRun {
  return {
    label: runLabel(run),
    workflowVersion: `v${run.workflow_version}`,
    evidenceFolder: run.evidence_folder,
    agentsThatDidTheirWork: `${run.agents_healthy} of ${run.agents_invoked}`,
    complianceToken: complianceToken(run),
    sentToCustomer: releaseSummary(run),
    auditFindings: run.audit.findings.length,
    inputTokens: run.usage.input_tokens,
    outputTokens: run.usage.output_tokens,
    provisionalUsd: run.provisional_usd,
  };
}

export const FOUNDRY_RUNS: readonly FoundryRun[] = RUNTIME_EVIDENCE.runs.map(toFoundryRun);

export const FINAL_ACCEPTANCE = {
  criteria: RUNTIME_EVIDENCE.final_acceptance.criteria,
  passed: RUNTIME_EVIDENCE.final_acceptance.passed,
  evidenceLedgerEntries: RUNTIME_EVIDENCE.final_acceptance.evidence_ledger_entries,
  policiesMapped: RUNTIME_EVIDENCE.final_acceptance.policies_mapped,
  plan: RUNTIME_EVIDENCE.final_acceptance.plan,
  result: RUNTIME_EVIDENCE.final_acceptance.result,
} as const;

export interface FoundryTotals {
  readonly runs: number;
  readonly inputTokens: number;
  readonly outputTokens: number;
  readonly provisionalUsd: number;
}

export function foundryTotals(runs: readonly FoundryRun[] = FOUNDRY_RUNS): FoundryTotals {
  return {
    runs: runs.length,
    inputTokens: runs.reduce((sum, r) => sum + r.inputTokens, 0),
    outputTokens: runs.reduce((sum, r) => sum + r.outputTokens, 0),
    provisionalUsd: Number(runs.reduce((sum, r) => sum + r.provisionalUsd, 0).toFixed(4)),
  };
}

/** Azure Cost Management returned no rows when last queried. Not a confirmed zero. */
export const BILLED_STATUS = "NOT_YET_VISIBLE" as const;
