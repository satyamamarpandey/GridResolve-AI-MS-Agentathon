import { describe, expect, it } from "vitest";
import caseInput from "../data/generated/caseInput.json";
import syntheticPack from "../data/generated/syntheticPack.json";
import {
  build_audit_packet,
  calculate_bill_change,
  calculate_case_cost,
  calculate_rate_effect,
  calculate_usage_change,
  detect_duplicate_adjustment,
  detect_estimated_trueup,
  lookup_synthetic_policy,
  validate_case_state,
  validate_claim_ledger,
  validate_evidence_ids,
  validate_meter_reads,
  validate_policy_ids,
} from "./index";
import type { Claim, EvidenceEntry, MeterRead, PolicyEntry } from "./types";

const rec = caseInput.synthetic_account_records;
const bills = rec.billing_history;
const reads = rec.meter_reads as MeterRead[];
const policies = syntheticPack.policies as unknown as PolicyEntry[];
const rate = rec.rate_components;

const evidence: EvidenceEntry[] = [
  {
    evidence_id: "EV-001",
    source_type: "meter_read",
    source_record_id: "SYN-READ-0003-B",
    period: "2026-07",
    field: "register_kwh",
    value: "42690",
    observation: "actual read",
  },
  {
    evidence_id: "EV-002",
    source_type: "diagnostic",
    source_record_id: "SYN-DIAG-0003-01",
    period: "2026-07",
    field: "result",
    value: "PASS",
    observation: "no fault",
  },
];

describe("calculate_bill_change", () => {
  it("matches the real synthetic bills", () => {
    const r = calculate_bill_change(bills[0].amount_usd, bills[1].amount_usd);
    expect(r.ok).toBe(true);
    expect(r.value?.deltaUsd).toBe(50.6);
    expect(r.value?.direction).toBe("increase");
    expect(r.value?.percentChange).toBeCloseTo(33.1, 1);
  });
  it("rejects non numeric input", () => {
    expect(calculate_bill_change(Number.NaN, 10).ok).toBe(false);
  });
  it("rejects negative amounts", () => {
    expect(calculate_bill_change(-1, 10).ok).toBe(false);
  });
  it("handles a zero previous bill without dividing by zero", () => {
    const r = calculate_bill_change(0, 50);
    expect(r.ok).toBe(true);
    expect(r.value?.percentChange).toBe(0);
    expect(r.notes.length).toBeGreaterThan(0);
  });
});

describe("calculate_usage_change", () => {
  it("computes the real 640 to 870 change", () => {
    const r = calculate_usage_change(640, 870, 30, 31);
    expect(r.value?.deltaKwh).toBe(230);
    expect(r.value?.percentChange).toBeCloseTo(35.9, 1);
    expect(r.value?.dailyPreviousKwh).toBeCloseTo(21.33, 2);
    expect(r.value?.dailyCurrentKwh).toBeCloseTo(28.06, 2);
    expect(r.notes.join(" ")).toContain("differ in length");
  });
  it("omits daily rates when days are absent", () => {
    expect(calculate_usage_change(640, 870).value?.dailyCurrentKwh).toBeNull();
  });
});

describe("calculate_rate_effect", () => {
  it("attributes this case to usage, since the rate did not change", () => {
    const r = calculate_rate_effect(640, 870, rate, rate);
    expect(r.value?.rateEffectUsd).toBe(0);
    expect(r.value?.fixedEffectUsd).toBe(0);
    expect(r.value?.usageEffectUsd).toBeCloseTo(50.6, 2);
    expect(r.value?.dominantDriver).toBe("usage");
  });
  it("detects a rate driven increase", () => {
    const higher = { ...rate, energy_charge_usd_per_kwh: 0.3 };
    const r = calculate_rate_effect(640, 640, rate, higher);
    expect(r.value?.dominantDriver).toBe("rate");
    expect(r.value?.usageEffectUsd).toBe(0);
  });
  it("decomposition reconciles with the actual bill difference", () => {
    const r = calculate_rate_effect(640, 870, rate, rate);
    const billDelta = calculate_bill_change(bills[0].amount_usd, bills[1].amount_usd).value!.deltaUsd;
    expect(r.value?.totalExplainedUsd).toBeCloseTo(billDelta, 2);
  });
});

describe("validate_meter_reads", () => {
  it("accepts the real reads and computes the register delta", () => {
    const r = validate_meter_reads(reads);
    expect(r.value?.allActual).toBe(true);
    expect(r.value?.registerDeltaKwh).toBe(870);
    expect(r.value?.issues).toHaveLength(0);
  });
  it("register delta equals billed kWh, which is the integrity check", () => {
    expect(validate_meter_reads(reads).value?.registerDeltaKwh).toBe(bills[1].kwh_billed);
  });
  it("flags a register rollback", () => {
    const bad = [reads[1], { ...reads[0], read_date: "2026-08-31" }] as MeterRead[];
    const r = validate_meter_reads(bad);
    expect(r.value?.rollback).toBe(true);
    expect(r.value?.issues.join(" ")).toContain("decreased");
  });
  it("flags duplicate record ids", () => {
    const r = validate_meter_reads([reads[0], reads[0]] as MeterRead[]);
    expect(r.value?.issues.join(" ")).toContain("duplicate");
  });
  it("rejects an empty array", () => {
    expect(validate_meter_reads([]).ok).toBe(false);
  });
});

describe("detect_estimated_trueup", () => {
  it("does not claim a true-up when every read is actual", () => {
    const r = detect_estimated_trueup(reads, bills as never);
    expect(r.value?.detected).toBe(false);
    expect(r.value?.reason).toContain("not a supported explanation");
  });
  it("detects an estimated read followed by an actual read", () => {
    const mixed = [
      { ...reads[0], read_type: "estimated" as const },
      reads[1],
    ] as MeterRead[];
    expect(detect_estimated_trueup(mixed, []).value?.detected).toBe(true);
  });
});

describe("policy lookup and id validation", () => {
  it("finds the meter concern policy", () => {
    const r = lookup_synthetic_policy("POL-MTR-003", policies);
    expect(r.ok).toBe(true);
    expect(r.value?.title).toContain("Meter");
  });
  it("fails closed on an invented policy", () => {
    const r = lookup_synthetic_policy("POL-FAKE-999", policies);
    expect(r.ok).toBe(false);
    expect(r.errors[0]).toContain("not present");
  });
  it("reports missing evidence ids", () => {
    const r = validate_evidence_ids(["EV-001", "EV-999"], evidence);
    expect(r.value?.missing).toEqual(["EV-999"]);
    expect(r.value?.allResolved).toBe(false);
  });
  it("reports resolved policy ids", () => {
    const r = validate_policy_ids(["POL-MTR-003"], policies);
    expect(r.value?.allResolved).toBe(true);
  });
});

describe("validate_claim_ledger", () => {
  const supported: Claim = {
    claim_id: "CL-1",
    statement: "Consumption rose and both reads are actual",
    material: true,
    evidence_ids: ["EV-001"],
    policy_ids: ["POL-HB-001"],
  };
  const meterFault: Claim = {
    claim_id: "CL-2",
    statement: "The meter is defective",
    material: true,
    evidence_ids: [],
    policy_ids: ["POL-MTR-003"],
  };

  it("marks a fully cited claim SUPPORTED", () => {
    const r = validate_claim_ledger([supported], evidence, policies);
    expect(r.value?.assessments[0].status).toBe("SUPPORTED");
    expect(r.value?.overallStatus).toBe("SUPPORTED");
  });

  it("marks the unsupported meter-fault claim UNSUPPORTED and forces human review", () => {
    const r = validate_claim_ledger([supported, meterFault], evidence, policies);
    const cl2 = r.value?.assessments.find((a) => a.claim_id === "CL-2");
    expect(cl2?.status).toBe("UNSUPPORTED");
    expect(cl2?.reason).toContain("cites no evidence");
    expect(r.value?.unsupportedMaterialClaims).toContain("CL-2");
    expect(r.value?.overallStatus).toBe("HUMAN_REVIEW_REQUIRED");
  });

  it("catches a fabricated evidence id", () => {
    const tampered: Claim = { ...meterFault, evidence_ids: ["EV-9999"] };
    const r = validate_claim_ledger([tampered], evidence, policies);
    expect(r.value?.assessments[0].status).toBe("UNSUPPORTED");
    expect(r.value?.assessments[0].missingEvidenceIds).toEqual(["EV-9999"]);
  });

  it("downgrades a claim with evidence but no policy", () => {
    const r = validate_claim_ledger([{ ...supported, policy_ids: [] }], evidence, policies);
    expect(r.value?.assessments[0].status).toBe("PARTIALLY_SUPPORTED");
  });
});

describe("detect_duplicate_adjustment", () => {
  const existing = [
    { adjustment_id: "ADJ-1", period: "2026-07", amount_usd: 25, reason: "goodwill" },
  ];
  it("detects a same period same amount duplicate", () => {
    const r = detect_duplicate_adjustment(existing, { period: "2026-07", amount_usd: 25 });
    expect(r.value?.duplicate).toBe(true);
    expect(r.value?.matchedIds).toEqual(["ADJ-1"]);
  });
  it("allows a different period", () => {
    expect(
      detect_duplicate_adjustment(existing, { period: "2026-08", amount_usd: 25 }).value?.duplicate,
    ).toBe(false);
  });
});

describe("calculate_case_cost", () => {
  it("prices tokens at the verified retail rate", () => {
    const r = calculate_case_cost(105_000, 32_000);
    expect(r.value?.inputCostUsd).toBeCloseTo(0.0263, 4);
    expect(r.value?.outputCostUsd).toBeCloseTo(0.064, 4);
    expect(r.value?.totalUsd).toBeCloseTo(0.0903, 3);
  });
  it("marks projections as unmeasured", () => {
    const r = calculate_case_cost(1000, 1000);
    expect(r.value?.measured).toBe(false);
    expect(r.notes.join(" ")).toContain("projected");
  });
  it("rejects negative tokens", () => {
    expect(calculate_case_cost(-1, 0).ok).toBe(false);
  });
});

describe("validate_case_state", () => {
  it("accepts a valid synthetic case", () => {
    expect(validate_case_state("SYN-CASE-4003", "COMPLIANCE_REVIEW").ok).toBe(true);
  });
  it("rejects a non synthetic case id, which blocks cross case access", () => {
    expect(validate_case_state("REAL-ACCT-12345", "INTAKE").ok).toBe(false);
  });
  it("rejects an unknown state", () => {
    expect(validate_case_state("SYN-CASE-4003", "DONE").ok).toBe(false);
  });
  it("flags correction exhaustion that has not routed to a human", () => {
    const r = validate_case_state("SYN-CASE-4003", "DRAFTING", 2);
    expect(r.value?.issues.join(" ")).toContain("human review");
  });
  it("accepts correction exhaustion once routed to human review", () => {
    expect(validate_case_state("SYN-CASE-4003", "HUMAN_REVIEW", 2).value?.issues).toHaveLength(0);
  });
});

describe("build_audit_packet", () => {
  const base = {
    caseId: "SYN-CASE-4003",
    workflowVersion: "GridResolveAIWorkflow v10",
    agents: ["CaseTriageAgent v5", "CaseAuditAgent v4"],
    evidence,
    policies,
    claims: [
      {
        claim_id: "CL-1",
        statement: "s",
        material: true,
        evidence_ids: ["EV-001"],
        policy_ids: ["POL-HB-001"],
      },
    ],
    complianceDecision: "NOT_RUN" as const,
    correctionCount: 0,
    humanReviewStatus: "NOT_REQUIRED",
    finalDisposition: "PREPARED",
  };

  it("produces a complete packet from full input", () => {
    const r = build_audit_packet(base);
    expect(r.value?.audit_completeness).toBe("COMPLETE");
    expect(r.value?.evidence_ids).toContain("EV-001");
  });

  it("never claims a runtime execution that did not happen", () => {
    expect(build_audit_packet(base).value?.execution_status).toBe("PREPARED_NOT_EXECUTED");
  });

  it("marks a packet incomplete when evidence is absent", () => {
    const r = build_audit_packet({ ...base, evidence: [] });
    expect(r.value?.audit_completeness).toBe("INCOMPLETE");
  });
});
