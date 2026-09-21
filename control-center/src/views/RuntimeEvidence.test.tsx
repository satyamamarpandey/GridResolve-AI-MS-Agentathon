import { renderToString } from "react-dom/server";
import { describe, expect, it } from "vitest";
import RuntimeEvidence from "./RuntimeEvidence";
import Overview from "./Overview";
import { CONTENT_KINDS } from "../components/ContentLegend";
import { RUNTIME_EVIDENCE, runLabel } from "../data/runtimeEvidence";
import { FINAL_ACCEPTANCE, FOUNDRY_RUNS, foundryTotals } from "../data/foundryRuns";
import { MODE_LABEL } from "../engine/investigation";

/** React inserts comment nodes between adjacent text fragments. */
const render = (index: number): string =>
  renderToString(<RuntimeEvidence initialRun={index} />).replace(/<!-- -->/g, "");

const RUNS = RUNTIME_EVIDENCE.runs;
/** En dash and em dash, named by code point so this file holds neither. */
const DASHES = new RegExp(`[${String.fromCharCode(0x2013, 0x2014)}]`);

describe("runtime evidence data", () => {
  it("holds exactly the three genuine runs, oldest first, all marked as actual executions", () => {
    expect(RUNTIME_EVIDENCE.content_kind).toBe("ACTUAL_FOUNDRY_EXECUTION");
    expect(RUNS.map((r) => r.workflow_version)).toEqual(["6", "9", "10"]);
    expect(RUNS.map((r) => runLabel(r, RUNS))).toEqual(["Run 1", "Run 2", "Final run"]);
    for (const run of RUNS) {
      expect(run.response_id).toMatch(/^wfresp_/);
      expect(run.evidence_folder).toMatch(/^\d{8}T\d{6}Z_SYN-CASE-4003_[0-9a-f]{8}$/);
      expect(run.final_status).toBe("completed");
    }
  });

  it("sums to the recorded totals and matches the status page data", () => {
    expect(RUNTIME_EVIDENCE.totals).toEqual({
      runs: 3,
      input_tokens: 186614,
      output_tokens: 42155,
      provisional_usd: 0.1311,
    });
    const totals = foundryTotals();
    expect(totals.inputTokens).toBe(RUNTIME_EVIDENCE.totals.input_tokens);
    expect(totals.outputTokens).toBe(RUNTIME_EVIDENCE.totals.output_tokens);
    expect(totals.provisionalUsd).toBe(RUNTIME_EVIDENCE.totals.provisional_usd);
  });

  it("derives the status page rows from the export rather than typed constants", () => {
    expect(FOUNDRY_RUNS.map((r) => r.agentsThatDidTheirWork)).toEqual(["7 of 8", "6 of 9", "9 of 9"]);
    expect(FOUNDRY_RUNS.map((r) => r.complianceToken)).toEqual(["APPROVED", "ESCALATE", "APPROVED"]);
    expect(FOUNDRY_RUNS.map((r) => r.auditFindings)).toEqual([7, 6, 0]);
    expect(FOUNDRY_RUNS.map((r) => r.provisionalUsd)).toEqual([0.0334, 0.0292, 0.0685]);
    expect(FOUNDRY_RUNS.map((r) => r.workflowVersion)).toEqual(["v6", "v9", "v10"]);
    expect(FINAL_ACCEPTANCE.criteria).toBe(14);
    expect(FINAL_ACCEPTANCE.passed).toBe(14);
    expect(FINAL_ACCEPTANCE.evidenceLedgerEntries).toBe(22);
    expect(FINAL_ACCEPTANCE.policiesMapped).toBe(9);
  });

  it("prices every run from its own token counts", () => {
    const { input_usd_per_million: inRate, output_usd_per_million: outRate } = RUNTIME_EVIDENCE.pricing;
    for (const run of RUNS) {
      const cost = (run.usage.input_tokens * inRate + run.usage.output_tokens * outRate) / 1_000_000;
      expect(run.provisional_usd).toBe(Number(cost.toFixed(4)));
      expect(run.usage.cached_input_tokens).toBe(0);
    }
  });

  it("carries no typographic dash", () => {
    expect(JSON.stringify(RUNTIME_EVIDENCE)).not.toMatch(DASHES);
  });
});

describe("runtime evidence view", () => {
  it.each([0, 1, 2])("renders run index %i with its identity", (index) => {
    const html = render(index);
    expect(html).toContain(RUNS[index].response_id);
    expect(html).toContain(RUNS[index].evidence_folder);
    expect(html).toContain("ACTUAL FOUNDRY EXECUTION");
    expect(html).toContain("this application did not run it");
    expect(html).not.toMatch(DASHES);
  });

  it("falls back to the final run when the index is out of range", () => {
    expect(renderToString(<RuntimeEvidence initialRun={99} />)).toContain(RUNS[2].response_id);
    expect(renderToString(<RuntimeEvidence />)).toContain(RUNS[2].response_id);
  });

  it("shows run 1 releasing an unevaluated expression as a defect", () => {
    const html = render(0);
    expect(html).toContain("=Last(Local.VarCustomerDraft).Text");
    expect(html).toContain("DEFECT");
    expect(html).toContain("7 of 8");
    expect(html).toContain("NOT_PRODUCED");
    expect(html).not.toContain("Acceptance result");
  });

  it("shows run 2 escalating with nothing sent and no reasons", () => {
    const html = render(1);
    expect(html).toContain("ESCALATE");
    expect(html).toContain("ESCALATED_TO_HUMAN");
    expect(html).toMatch(/Nothing was sent to the customer/);
    expect(html).toMatch(/gave no reasons/i);
    expect(html).toContain("6 of 9");
    expect(html).not.toContain("Acceptance result");
  });

  it("shows the final run as recorded", () => {
    const html = render(2);
    expect(html).toContain("9 of 9");
    expect(html).toContain(">APPROVE<");
    expect(html).toContain("ROUTE_DECISION::GRIDRESOLVE_APPROVED");
    expect(html).toContain("22 entries");
    expect(html).toContain("9 policies");
    expect(html).toContain("0 findings");
    expect(html).toContain("14 of 14");
    expect(html).toContain("Billing Supervisor");
    expect(html).toContain("PENDING_HUMAN_REVIEW");
    expect(html).toContain("docs/FINAL_RUN_RESULT_2026-09-20.md");
  });

  it("shows the released message verbatim", () => {
    const released = RUNS[2].release.text;
    expect(released.length).toBe(2592);
    const escaped = released
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#x27;");
    expect(render(2)).toContain(escaped);
  });

  it("never presents itself as the offline demonstration", () => {
    for (const index of [0, 1, 2]) {
      const banners = [...render(index).matchAll(/class="banner mode"><span class="tag tag-accent">([^<]+)</g)];
      expect(banners.map((b) => b[1])).toEqual(["ACTUAL FOUNDRY EXECUTION"]);
    }
  });

  it("does not claim production readiness or a billed amount", () => {
    const html = render(2);
    expect(html).toMatch(/provisional/i);
    expect(html).toContain("NOT_YET_VISIBLE");
    expect(html).not.toMatch(/production-ready/i);
  });
});

describe("content legend", () => {
  it("names the four kinds of content once each", () => {
    expect(CONTENT_KINDS.map((k) => k.label)).toEqual([
      "ACTUAL FOUNDRY EXECUTION",
      "DETERMINISTIC OFFLINE DEMONSTRATION",
      "PREPARED EVALUATION",
      "FUTURE PRODUCTION INTEGRATION",
    ]);
    expect(CONTENT_KINDS[1].label).toBe(MODE_LABEL);
  });

  it.each([
    ["Runtime Evidence", () => render(2)],
    ["Overview", () => renderToString(<Overview />)],
  ])("appears on %s with all four labels", (_name, html) => {
    const out = html();
    for (const kind of CONTENT_KINDS) expect(out).toContain(kind.label);
    expect(out).toMatch(/not executed/i);
    expect(out).toMatch(/planned, not live/i);
  });

  it("keeps the offline Overview labelled as offline, never as a Foundry execution", () => {
    const banners = [
      ...renderToString(<Overview />).matchAll(/class="banner mode"><span class="tag tag-accent">([^<]+)</g),
    ];
    expect(banners.map((b) => b[1])).toEqual([MODE_LABEL]);
  });
});
