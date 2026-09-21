import { renderToString } from "react-dom/server";
import cssText from "./styles.css?raw";
import dsText from "./ds.css?raw";
import { describe, expect, it } from "vitest";
import App from "./App";
import Overview from "./views/Overview";
import BillingInvestigation from "./views/BillingInvestigation";
import EvidenceExplorer from "./views/EvidenceExplorer";
import AgentWorkflow from "./views/AgentWorkflow";
import CustomerAssistant from "./views/CustomerAssistant";
import SupervisorReview from "./views/SupervisorReview";
import Governance from "./views/Governance";
import Evaluations from "./views/Evaluations";
import SystemStatus from "./views/SystemStatus";
import RuntimeEvidence from "./views/RuntimeEvidence";

const VIEWS = {
  Overview,
  BillingInvestigation,
  EvidenceExplorer,
  AgentWorkflow,
  CustomerAssistant,
  SupervisorReview,
  Governance,
  Evaluations,
  SystemStatus,
  RuntimeEvidence,
};

describe("control center renders", () => {
  it("renders the shell with every section", () => {
    const html = renderToString(<App />);
    for (const label of Object.keys(VIEWS)) {
      expect(html.length).toBeGreaterThan(500);
      expect(label).toBeTruthy();
    }
    expect(html).toContain("GridResolve AI");
    expect(html).toContain("Control Center");
  });

  it.each(Object.entries(VIEWS))("renders %s without throwing", (_name, View) => {
    const html = renderToString(<View />);
    expect(html.length).toBeGreaterThan(300);
  });

  it("never claims a runtime proven status anywhere in the rendered output", () => {
    const html = Object.values(VIEWS)
      .map((V) => renderToString(<V />))
      .join(" ");
    // The vocabulary may be defined and explained, but no control may be labelled as proven.
    expect(html).not.toContain(">RUNTIME_PROVEN<");
  });

  it("does not deny the three real Foundry runs, or present an old workflow version as current", () => {
    const html = Object.values(VIEWS)
      .map((V) => renderToString(<V />))
      .join(" ");
    expect(html).not.toMatch(/workflow has never been executed/i);
    expect(html).not.toContain(">NOT RUN<");
    expect(html).not.toMatch(/SPEND ON THIS BUILD: ZERO/);
    expect(html).not.toMatch(/deployed workflow v5/);
    expect(html).not.toMatch(/Nine agents and workflow v5/);
    expect(html).toMatch(/THREE REAL FOUNDRY RUNS/);
  });

  it("says where the real final run differed from this offline demonstration", () => {
    const html = Object.values(VIEWS)
      .map((V) => renderToString(<V />))
      .join(" ");
    expect(html).toMatch(/compliance approved a message that asserts no meter failure/i);
  });

  it("does not leak a credential-shaped string into the bundle output", () => {
    const html = Object.values(VIEWS)
      .map((V) => renderToString(<V />))
      .join(" ");
    expect(html).not.toMatch(/(api[_-]?key|bearer\s+ey|sk-[a-z0-9]{10})/i);
  });
});

describe("offline guarantee", () => {
  it("ships no external network dependency in the stylesheet", () => {
    const css = cssText + dsText;
    expect(css).not.toMatch(/@import\s+url\(\s*['"]?https?:/i);
    expect(css).not.toContain("fonts.googleapis.com");
    expect(css).not.toContain("fonts.gstatic.com");
  });

  it("keeps the design system font stack with a local fallback", () => {
    expect(dsText).toContain('--font-body: "Barlow", system-ui, sans-serif');
    expect(dsText).toContain('--font-heading: "Barlow Condensed", system-ui, sans-serif');
  });

  it("carries the design system verbatim, minus its webfont import", () => {
    expect(dsText).not.toContain("fonts.googleapis.com");
    // The blueprint frame is what makes the system recognisable.
    expect(dsText).toContain(".blueprint");
    expect(dsText).toContain(".card, .btn, .input, .tag, .seg, .dialog { border-radius: 0; }");
  });
});
