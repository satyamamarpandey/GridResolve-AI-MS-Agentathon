/** Shared types for the deterministic business tools. */

export type SupportStatus =
  | "SUPPORTED"
  | "PARTIALLY_SUPPORTED"
  | "UNSUPPORTED"
  | "HUMAN_REVIEW_REQUIRED";

export type CaseState =
  | "INTAKE"
  | "INVESTIGATING"
  | "PLANNING"
  | "DRAFTING"
  | "COMPLIANCE_REVIEW"
  | "CORRECTION"
  | "HUMAN_REVIEW"
  | "APPROVED"
  | "CLOSED"
  | "CANNOT_RESOLVE_SAFELY";

export type ComplianceDecision =
  | "APPROVE"
  | "REJECT_AND_REPLAN"
  | "REJECT_AND_REWRITE"
  | "HUMAN_REVIEW_REQUIRED";

export type ReadType = "actual" | "estimated";

export interface MeterRead {
  readonly record_id: string;
  readonly read_date: string;
  readonly read_type: ReadType;
  readonly register_kwh: number;
}

export interface BillingRecord {
  readonly record_id: string;
  readonly period_start: string;
  readonly period_end: string;
  readonly billing_days: number;
  readonly kwh_billed: number;
  readonly amount_usd: number;
  readonly read_type_end: ReadType;
}

export interface RateComponents {
  readonly energy_charge_usd_per_kwh: number;
  readonly fixed_charge_usd_per_period: number;
}

export interface EvidenceEntry {
  readonly evidence_id: string;
  readonly source_type: string;
  readonly source_record_id: string;
  readonly period: string;
  readonly field: string;
  readonly value: string;
  readonly observation: string;
}

export interface PolicyEntry {
  readonly policy_id: string;
  readonly version: string;
  readonly title: string;
  readonly purpose: string;
  readonly conditions?: readonly string[];
  readonly required_evidence?: readonly string[];
  readonly allowed_actions?: readonly string[];
  readonly prohibited_actions?: readonly string[];
  readonly human_approval_requirement?: string;
  readonly conflict_behavior?: string;
}

export interface Claim {
  readonly claim_id: string;
  readonly statement: string;
  readonly material: boolean;
  readonly evidence_ids: readonly string[];
  readonly policy_ids: readonly string[];
}

export interface Adjustment {
  readonly adjustment_id: string;
  readonly period: string;
  readonly amount_usd: number;
  readonly reason: string;
}

/** Every tool returns this shape. Errors are values, never thrown for bad input. */
export interface ToolResult<T> {
  readonly ok: boolean;
  readonly value: T | null;
  readonly errors: readonly string[];
  readonly notes: readonly string[];
}

export const ok = <T>(value: T, notes: readonly string[] = []): ToolResult<T> => ({
  ok: true,
  value,
  errors: [],
  notes,
});

export const fail = <T>(errors: readonly string[]): ToolResult<T> => ({
  ok: false,
  value: null,
  errors,
  notes: [],
});

/** Round to cents without floating point drift surprising the caller. */
export const money = (n: number): number => Math.round(n * 100) / 100;
export const pct = (n: number): number => Math.round(n * 10) / 10;
