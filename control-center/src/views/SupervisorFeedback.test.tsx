import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import SupervisorFeedback from "./SupervisorFeedback";
import {
  RECORDS,
  SIMULATED_EXAMPLE,
  deriveAgreement,
  overrideRate,
  reviewTimeReduction,
  type HumanReviewRecord,
} from "../engine/supervisorFeedback";

const DASHES = new RegExp(`[${String.fromCharCode(0x2013, 0x2014)}]`);
const html = renderToString(<SupervisorFeedback />).replace(/<!-- -->/g, "");

const actualFixture: HumanReviewRecord = {
  ...SIMULATED_EXAMPLE,
  evidence_package_ref: "test fixture standing in for an actual record",
  human_decision: "REJECT_DRAFT",
  agreement: deriveAgreement("ESCALATED_TO_HUMAN", "REJECT_DRAFT"),
  override_reason: "test fixture override reason",
  record_kind: "ACTUAL_HUMAN_REVIEW",
};

describe("supervisor feedback view", () => {
  it("renders and states plainly that everything is an offline simulation", () => {
    expect(html.length).toBeGreaterThan(300);
    expect(html).toContain("OFFLINE_SIMULATION ONLY, NO ACTUAL HUMAN REVIEW RECORDED");
    expect(html).toContain("No supervisor has reviewed a GridResolve case");
  });

  it("shows every field of the human review record", () => {
    for (const key of Object.keys(SIMULATED_EXAMPLE) as (keyof HumanReviewRecord)[]) {
      const value = SIMULATED_EXAMPLE[key];
      if (typeof value === "string" && value) expect(html).toContain(value);
    }
    expect(html).toContain("ACTUAL_HUMAN_REVIEW records");
  });

  it("reports both metrics as not measured with a reason", () => {
    expect((html.match(/Not measured/g) ?? []).length).toBeGreaterThanOrEqual(2);
    expect(html).toContain("No actual human decision has been recorded");
    expect(html).toContain("A baseline is never invented");
  });

  it("holds only simulated records and never claims a proven or actual review", () => {
    expect(RECORDS.every((r) => r.record_kind === "OFFLINE_SIMULATION")).toBe(true);
    expect(html).not.toContain(">RUNTIME_PROVEN<");
    expect(html).not.toMatch(/override rate of \d/i);
  });

  it("uses no em dash or en dash", () => {
    expect(html).not.toMatch(DASHES);
  });
});

describe("supervisor feedback metrics mirror the Python rules", () => {
  it("derives agreement and never trusts a supplied value", () => {
    expect(deriveAgreement(" approve ", "APPROVE")).toBe("AGREE");
    expect(deriveAgreement("APPROVE", "REJECT")).toBe("DISAGREE");
  });

  it("does not measure an override rate from simulated records", () => {
    const result = overrideRate(RECORDS);
    expect("rate" in result).toBe(false);
    if (!("rate" in result)) {
      expect(result.actual_records).toBe(0);
      expect(result.simulated_records).toBe(RECORDS.length);
    }
  });

  it("measures an override rate only over actual records", () => {
    const result = overrideRate([...RECORDS, actualFixture]);
    expect("rate" in result).toBe(true);
    if ("rate" in result) {
      expect(result.actual_records).toBe(1);
      expect(result.overrides).toBe(1);
      expect(result.rate).toBe(1);
      expect(result.simulated_excluded).toBe(RECORDS.length);
    }
  });

  it("never measures a review-time reduction without a baseline", () => {
    const result = reviewTimeReduction([...RECORDS, actualFixture]);
    expect(result.metric).toBe("review_time_reduction");
    expect(result.reason).toContain("baseline");
    expect(result.simulated_records).toBe(RECORDS.length);
  });
});
