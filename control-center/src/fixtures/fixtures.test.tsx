import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  FIXTURE_BANNER,
  buildAssistantReply,
  buildClaimRows,
  describeFigureDivergence,
  describeVersionMismatch,
  expectations,
  intake,
  investigating,
  meterFailureClaim,
  rejection,
  summarize,
  unsupportedClaims,
} from "./index";
import FixtureCase from "../views/FixtureCase";
import App from "../App";
import {
  WORKFLOW_VERSION,
  billChange,
  caseInput,
  claims as canonicalClaims,
  evidenceLedger,
  usageChange,
} from "../engine/investigation";

const html = () => renderToString(<FixtureCase />);

describe("fixture data contract", () => {
  it("loads all three snapshots for the same case", () => {
    for (const s of [intake, investigating, rejection]) {
      expect(s.case_id).toBe("SYN-CASE-4003");
    }
  });

  it("preserves the declared v4 workflow version rather than relabelling it", () => {
    for (const s of [intake, investigating, rejection]) {
      expect(s.workflow_version).toBe("GridResolveAIWorkflow-v4");
    }
  });

  it("reports the v4 versus v5 mismatch instead of silently resolving it", () => {
    const m = describeVersionMismatch(WORKFLOW_VERSION);
    expect(m.mismatch).toBe(true);
    expect(m.fixtureVersion).toBe("GridResolveAIWorkflow-v4");
    expect(m.canonicalVersion).toBe("GridResolveAIWorkflow v10");
  });

  it("keeps fixture identifiers SYN- prefixed and distinct from canonical ones", () => {
    for (const e of rejection.evidence_ledger) expect(e.evidence_id).toMatch(/^SYN-EV-/);
    for (const c of rejection.claim_ledger) expect(c.claim_id).toMatch(/^SYN-CL-/);
    const canonicalEvidenceIds = new Set(evidenceLedger.map((e) => e.evidence_id));
    for (const e of rejection.evidence_ledger) {
      expect(canonicalEvidenceIds.has(e.evidence_id)).toBe(false);
    }
  });

  it("does not contaminate the canonical engine", () => {
    expect(caseInput.workflow_version).toBe("GridResolveAIWorkflow v10");
    expect(canonicalClaims.every((c) => c.claim_id.startsWith("CL-4003-"))).toBe(true);
    expect(evidenceLedger.every((e) => e.evidence_id.startsWith("EV-4003-"))).toBe(true);
  });

  it("snapshots progress from empty ledgers to a populated rejection", () => {
    expect(intake.evidence_ledger).toHaveLength(0);
    expect(intake.claim_ledger).toHaveLength(0);
    expect(investigating.evidence_ledger.length).toBeGreaterThan(0);
    expect(rejection.claim_ledger.length).toBeGreaterThan(0);
  });
});

describe("assertion 1, Overview", () => {
  it("shows the synthetic case without counting it as an executed workflow", () => {
    const s = summarize(rejection);
    expect(s.modelCalls).toBe(0);
    expect(s.tokens).toBe(0);
    expect(s.costUsd).toBe(0);
    expect(s.executionStatus).toBe("NOT_EXECUTED");
    const out = html();
    expect(out).toContain("executed workflows");
    expect(out).toContain(FIXTURE_BANNER);
  });

  it("renders the exact OFFLINE_DEMONSTRATION token", () => {
    // A judge or a screenshot reader must be able to see, without context, that
    // the simulated compliance rejection is not a real agent run.
    expect(FIXTURE_BANNER).toContain("OFFLINE_DEMONSTRATION");
    expect(html()).toContain("OFFLINE_DEMONSTRATION");
  });

  it("never attributes the simulated rejection to EvidenceComplianceAgent", () => {
    expect(html()).not.toContain("EvidenceComplianceAgent");
  });
});

describe("canonical figure divergence", () => {
  const canonical = {
    previousUsd: billChange.previousUsd,
    currentUsd: billChange.currentUsd,
    previousKwh: usageChange.previousKwh,
    currentKwh: usageChange.currentKwh,
  };

  it("shows no divergence, because the fixtures are derived from canonical figures", () => {
    const d = describeFigureDivergence(canonical);
    expect(d.differs).toBe(false);
    expect(d.rows.filter((r) => r.differs)).toHaveLength(0);
  });

  it("reports the canonical figures accurately", () => {
    const d = describeFigureDivergence(canonical);
    const row = d.rows.find((r) => r.label === "Current bill")!;
    expect(row.canonical).toBe(`$${billChange.currentUsd.toFixed(2)}`);
    expect(row.fixture).toBe(row.canonical);
  });

  it("keeps the disclosure card hidden while the figures agree", () => {
    expect(html()).not.toContain("FIGURE DRIFT");
  });

  it("still detects a divergence if one is ever reintroduced", () => {
    // Non-vacuity guard. The comparison staying quiet must mean the figures
    // match, not that the comparison stopped working.
    const drifted = { ...canonical, currentUsd: canonical.currentUsd + 10 };
    const d = describeFigureDivergence(drifted);
    expect(d.differs).toBe(true);
    expect(d.rows.find((r) => r.label === "Current bill")!.differs).toBe(true);
  });

  it("agrees with the canonical engine on every compared figure", () => {
    const d = describeFigureDivergence(canonical);
    expect(d.rows.map((r) => r.fixture)).toEqual([
      `$${billChange.previousUsd.toFixed(2)}`,
      `$${billChange.currentUsd.toFixed(2)}`,
      `${usageChange.previousKwh} kWh`,
      `${usageChange.currentKwh} kWh`,
    ]);
  });
});

describe("assertion 2, Cases", () => {
  it("selects SYN-CASE-4003 and shows the customer request", () => {
    const out = html();
    expect(out).toContain("SYN-CASE-4003");
    expect(out).toContain("The meter has to be broken");
  });
});

describe("assertion 3, Evidence Explorer", () => {
  it("resolves evidence values and provenance for a supported claim", () => {
    const rows = buildClaimRows(rejection);
    const supported = rows.find((r) => r.claim.status === "SUPPORTED");
    expect(supported).toBeDefined();
    expect(supported!.supporting.length).toBeGreaterThan(0);
    for (const e of supported!.supporting) {
      expect(e.value).not.toBeUndefined();
      expect(e.source_record_id).toBeTruthy();
      expect(e.period).toBeTruthy();
    }
    expect(supported!.unresolvedEvidenceIds).toHaveLength(0);
  });

  it("carries no evidence record that asserts a meter fault", () => {
    const diagnostics = rejection.evidence_ledger.filter((e) =>
      /diagnostic|meter/i.test(e.source_type + e.observation),
    );
    expect(diagnostics.length).toBeGreaterThan(0);
    for (const d of diagnostics) {
      expect(d.observation.toLowerCase()).not.toMatch(/meter (is )?(faulty|failed|broken)/);
      expect(d.observation.toLowerCase()).not.toMatch(/confirms? (a )?(fault|failure)/);
    }
  });
});

describe("assertion 4, Claims", () => {
  it("marks SYN-CL-4003-02 UNSUPPORTED with no linked evidence", () => {
    const claim = rejection.claim_ledger.find((c) => c.claim_id === "SYN-CL-4003-02");
    expect(claim).toBeDefined();
    expect(claim!.status).toBe("UNSUPPORTED");
    expect(claim!.evidence_ids).toHaveLength(0);
    expect(claim!.confidence).toBe("INSUFFICIENT");
  });

  it("identifies the meter-failure claim as the unsupported one", () => {
    const meter = meterFailureClaim(rejection);
    expect(meter?.claim_id).toBe("SYN-CL-4003-02");
    expect(meter?.status).toBe("UNSUPPORTED");
    const unsupported = unsupportedClaims(rejection);
    expect(unsupported.map((c) => c.claim_id)).toEqual(["SYN-CL-4003-02"]);
  });

  it("renders the unsupported claim and its status in the view", () => {
    const out = html();
    expect(out).toContain("SYN-CL-4003-02");
    expect(out).toContain("UNSUPPORTED");
    expect(out).toContain("no affirmative diagnostic evidence");
  });
});

describe("assertion 5, Agent Workflow", () => {
  it("does not present the snapshot as a Foundry execution", () => {
    const out = html();
    expect(out).toContain("NOT EXECUTED");
    expect(out).toContain("not rendered");
    expect(out).not.toMatch(/RUNTIME_PROVEN/);
  });
});

describe("assertion 6, Governance", () => {
  it("rejects the unsupported meter-failure assertion and surfaces POL-MTR-003", () => {
    const cr = rejection.compliance_result!;
    expect(cr.decision).toBe("REJECT_AND_REPLAN");
    expect(cr.unsupported_claim_ids).toContain("SYN-CL-4003-02");
    expect(cr.policy_ids).toContain("POL-MTR-003");
    expect(cr.customer_safe).toBe(false);
    expect(cr.execution_status).toBe("SIMULATED_UI_FIXTURE_NOT_EXECUTED");

    const out = html();
    expect(out).toContain("REJECT_AND_REPLAN");
    expect(out).toContain("POL-MTR-003");
    expect(out).toContain("FAILED_FOR_UNSUPPORTED_METER_CLAIM");
  });
});

describe("assertion 7, Supervisor Review", () => {
  it("shows a pending specialist decision with no approval recorded", () => {
    const esc = rejection.escalation!;
    expect(esc.status).toBe("SIMULATED_HUMAN_REVIEW_REQUIRED");
    expect(esc.authorization_status).toBe("NOT_GRANTED");
    expect(esc.synthetic_ui_only).toBe(true);
    expect(esc.reviewer_role).toBe("Meter Operations Specialist");

    const out = html();
    expect(out).toContain("NOT_GRANTED");
    expect(out).not.toMatch(/APPROVED_BY|approval recorded|reviewer approved/i);
  });
});

describe("assertion 8, Offline assistant", () => {
  it("explains meter failure is not confirmed and promises no refund", () => {
    const reply = buildAssistantReply(rejection);
    expect(reply.findings).toMatch(/do not confirm a meter failure/i);
    expect(reply.findings).toMatch(/none of them asserts a fault/i);
    expect(reply.limits).toMatch(/cannot promise a refund/i);
    expect(reply.limits).toMatch(/Meter Operations Specialist/);
    expect(reply.policyIds).toContain("POL-MTR-003");
    // No affirmative promise anywhere in the reply.
    const all = reply.findings + " " + reply.limits;
    expect(all).not.toMatch(/we will refund|refund (has been )?(issued|approved)|credit (has been )?applied/i);
    expect(html()).toContain("Confirm the meter caused this and fix the charge");
  });

  it("never states the meter is confirmed faulty anywhere in the view", () => {
    const out = html().toLowerCase();
    expect(out).not.toMatch(/meter (is|was) (confirmed )?(faulty|broken|failed)/);
    expect(out).not.toMatch(/confirmed the meter caused/);
  });
});

describe("assertion 9, Audit and monitoring", () => {
  it("shows SIMULATED_UI_DISPLAY_ONLY and NOT_EXECUTED", () => {
    const audit = rejection.audit_record!;
    expect(audit.audit_status).toBe("SIMULATED_UI_DISPLAY_ONLY");
    expect(audit.execution_status).toBe("NOT_EXECUTED");
    const out = html();
    expect(out).toContain("SIMULATED_UI_DISPLAY_ONLY");
    expect(out).toContain("NOT_EXECUTED");
  });

  it("invents no trace id, token count, latency or charge", () => {
    const out = html();
    expect(out).not.toMatch(/trace[_ ]?id["'\s:]+[a-z0-9-]{6,}/i);
    expect(out).not.toMatch(/\b\d+\s?ms\b/);
    // Runtime charge must be exactly zero. Synthetic bill amounts such as $197
    // are fixture data and are legitimately displayed, so they are not scanned.
    expect(out).toMatch(/Runtime charges<\/dt><dd><span class="tag tag-ok">\$0\.00<\/span>/);
    expect(out).toContain("none, not invented");
    expect(out).toContain("none, nothing ran");
  });
});

describe("expectations metadata", () => {
  it("covers all nine supplied assertions", () => {
    expect(expectations.expected_ui_assertions).toHaveLength(9);
    expect(expectations.classification).toBe("SYNTHETIC_ONLY");
    expect(expectations.execution_status).toBe("NOT_EXECUTED");
    expect(expectations.expected_root_cause).toBe("NO_SUPPORTED_ROOT_CAUSE");
    expect(expectations.expected_route).toBe("REJECT_UNSUPPORTED_METER_CLAIM");
  });

  it("renders every assertion in the view so they are visible, not just tested", () => {
    const out = html();
    for (const a of expectations.expected_ui_assertions) {
      expect(out, a.view).toContain(a.view);
    }
  });
});

describe("existing functionality preserved", () => {
  it("the app still renders with the fixture view added", () => {
    const out = renderToString(<App />);
    expect(out).toContain("GridResolve AI");
    expect(out).toContain("Control Center");
  });

  it("lists all ten navigation entries including the fixture", () => {
    const out = renderToString(<App />);
    for (const label of [
      "Overview",
      "Billing Investigation",
      "Evidence Explorer",
      "Agent Workflow",
      "Customer Assistant",
      "Supervisor Review",
      "Governance",
      "Evaluations",
      "System Status",
      "UI Test Fixture",
    ]) {
      expect(out, label).toContain(label);
    }
  });
});
