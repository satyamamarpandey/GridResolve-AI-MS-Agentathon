import { useState } from "react";
import { Card, Meter, ModeBanner, Pill, statusTone } from "../components/ui";
import evaluationSuite from "../data/generated/evaluationSuite.json";

const { meta, cases } = evaluationSuite;
const rubric = Object.entries(meta.rubric) as ReadonlyArray<[string, number]>;

/** Local static tests already executed, with no model involvement. */
const LOCAL_SUITES: ReadonlyArray<{ name: string; checks: number; result: string; what: string }> = [
  {
    name: "Routing and data semantics",
    checks: 72,
    result: "PASS",
    what: "Reproduces Power Fx substring matching and proves the v5 gate escalates where v4 failed open",
  },
  {
    name: "Live configuration verification",
    checks: 33,
    result: "PASS",
    what: "Read-only assertions against the deployed workflow and all nine agent versions",
  },
  {
    name: "Deterministic tool suite",
    checks: 37,
    result: "PASS",
    what: "Billing arithmetic, meter validation, claim provenance, duplicate detection and audit assembly",
  },
  {
    name: "Memory isolation and responder",
    checks: 13,
    result: "PASS",
    what: "Cross case leakage, non synthetic identifier refusal, and refusal to answer outside the evidence",
  },
  {
    name: "Control Center render smoke",
    checks: 12,
    result: "PASS",
    what: "Every view renders, no control is labelled runtime proven, no credential-shaped string reaches the output",
  },
  {
    name: "Local trace schema",
    checks: 10,
    result: "PASS",
    what: "Span parenting, measured durations, zero token attribution, and the Foundry dataset staying empty",
  },
  {
    name: "Live Foundry adapter, disabled",
    checks: 13,
    result: "PASS",
    what: "Refuses before the network on every path, ships no credential, rejects production-shaped identifiers",
  },
];

const totalLocal = LOCAL_SUITES.reduce((n, s) => n + s.checks, 0);

/** Evaluator inventory. Foundry evaluators are named but have never been run. */
const EVALUATORS: ReadonlyArray<{ name: string; kind: "Foundry built-in" | "Custom rubric"; status: string }> = [
  { name: "Groundedness", kind: "Foundry built-in", status: "PREPARED_NOT_EXECUTED" },
  { name: "Groundedness Pro", kind: "Foundry built-in", status: "PREPARED_NOT_EXECUTED" },
  { name: "Relevance", kind: "Foundry built-in", status: "PREPARED_NOT_EXECUTED" },
  { name: "Coherence", kind: "Foundry built-in", status: "PREPARED_NOT_EXECUTED" },
  { name: "Fluency", kind: "Foundry built-in", status: "PREPARED_NOT_EXECUTED" },
  { name: "Retrieval", kind: "Foundry built-in", status: "PREPARED_NOT_EXECUTED" },
  { name: "Task Adherence", kind: "Foundry built-in", status: "PREPARED_NOT_EXECUTED" },
  { name: "Intent Resolution", kind: "Foundry built-in", status: "PREPARED_NOT_EXECUTED" },
  { name: "Tool Call Accuracy", kind: "Foundry built-in", status: "PREPARED_NOT_EXECUTED" },
  { name: "Response Completeness", kind: "Foundry built-in", status: "PREPARED_NOT_EXECUTED" },
  { name: "Indirect Attack", kind: "Foundry built-in", status: "PREPARED_NOT_EXECUTED" },
  { name: "Protected Material", kind: "Foundry built-in", status: "PREPARED_NOT_EXECUTED" },
  { name: "Content Safety", kind: "Foundry built-in", status: "PREPARED_NOT_EXECUTED" },
  { name: "GridResolve Quality Rubric", kind: "Custom rubric", status: "PREPARED_NOT_EXECUTED" },
  { name: "GridResolve Escalation Correctness", kind: "Custom rubric", status: "PREPARED_NOT_EXECUTED" },
];

const categories = [...new Set(cases.map((c) => c.category))];

export default function Evaluations() {
  const [category, setCategory] = useState<string>("ALL");
  const shown = category === "ALL" ? cases : cases.filter((c) => c.category === category);

  return (
    <>
      <div className="page-head">
        <h2>Evaluations</h2>
        <p>
          Two different things are shown on this page and they are never blended. Local static tests have
          actually run. Foundry model evaluations have been prepared and have not run.
        </p>
      </div>

      <ModeBanner
        label="LOCAL STATIC TESTS ARE EXECUTED, FOUNDRY MODEL EVALUATIONS ARE NOT"
        detail={`${totalLocal} local checks pass with zero model calls. The ${meta.count} case Foundry suite is authored and held at ${meta.status.replace(/_/g, " ").toLowerCase()} pending explicit spend authorization.`}
      />

      <div className="grid g2">
        <Card
          title="Local static tests"
          sub="Executed, deterministic, no tokens spent"
          right={<Pill tone="ok">{totalLocal} checks passing</Pill>}
        >
          <table>
            <thead>
              <tr>
                <th>Suite</th>
                <th style={{ width: 72 }}>Checks</th>
                <th style={{ width: 76 }}>Result</th>
              </tr>
            </thead>
            <tbody>
              {LOCAL_SUITES.map((s) => (
                <tr key={s.name}>
                  <td>
                    <strong>{s.name}</strong>
                    <div style={{ color: "var(--ink-3)", fontSize: 12, marginTop: 2 }}>{s.what}</div>
                  </td>
                  <td className="mono">{s.checks}</td>
                  <td><Pill tone="ok">{s.result}</Pill></td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="footnote">
            These prove behavior that does not need a model to be correct: routing semantics, arithmetic,
            provenance resolution and data isolation. They are the reason a defect was found before any run.
          </p>
        </Card>

        <Card
          title="Foundry model evaluations"
          sub={`${meta.suite}, ${meta.count} cases`}
          right={<Pill tone="warn">NOT EXECUTED</Pill>}
        >
          <p style={{ marginTop: 4, fontSize: 13, color: "var(--ink-2)" }}>
            Running this suite calls gpt-5-mini once per case per evaluator, which spends money. It is held
            until authorized. No partial run, no sampled run, and no estimated score is presented anywhere in
            this application.
          </p>
          <div style={{ marginTop: 14 }}>
            {rubric.map(([dimension, weight]) => (
              <div key={dimension} style={{ marginBottom: 11 }}>
                <div className="row spread" style={{ marginBottom: 4, fontSize: 12.5 }}>
                  <span>{dimension}</span>
                  <span className="mono" style={{ color: "var(--ink-3)" }}>weight {(weight * 100).toFixed(0)}%</span>
                </div>
                <Meter value={weight} max={Math.max(...rubric.map(([, w]) => w))} tone="violet" />
              </div>
            ))}
          </div>
          <p className="footnote">
            Weights total {(rubric.reduce((n, [, w]) => n + w, 0) * 100).toFixed(0)}%. Evidence fidelity and
            policy compliance carry the most weight, because a fluent answer that cites nothing is the
            failure mode that matters in a regulated setting.
          </p>
        </Card>
      </div>

      <Card
        title="Evaluator inventory"
        sub={`${EVALUATORS.length} evaluators, ${EVALUATORS.filter((e) => e.kind === "Custom rubric").length} custom`}
        className="card"
      >
        <div className="row" style={{ flexWrap: "wrap", gap: 6 }}>
          {EVALUATORS.map((e) => (
            <span key={e.name} className="pill muted" title={e.status} style={{ gap: 6 }}>
              {e.name}
              <span style={{ color: "var(--ink-3)", fontSize: 10 }}>
                {e.kind === "Custom rubric" ? "custom" : "built in"}
              </span>
            </span>
          ))}
        </div>
        <p className="footnote">
          Every evaluator above is at PREPARED_NOT_EXECUTED. None has produced a score, so no score is shown.
        </p>
      </Card>

      <Card
        title="Prepared evaluation cases"
        sub={`${cases.length} synthetic cases across ${categories.length} categories`}
        right={
          <div className="row" style={{ flexWrap: "wrap", gap: 5 }}>
            <button className={`seg${category === "ALL" ? " on" : ""}`} onClick={() => setCategory("ALL")}>
              All
            </button>
            {categories.map((c) => (
              <button key={c} className={`seg${category === c ? " on" : ""}`} onClick={() => setCategory(c)}>
                {c.replace(/_/g, " ").toLowerCase()}
              </button>
            ))}
          </div>
        }
        className="card"
      >
        <table>
          <thead>
            <tr>
              <th style={{ width: 84 }}>Eval ID</th>
              <th style={{ width: 124 }}>Case</th>
              <th>Scenario</th>
              <th style={{ width: 176 }}>Expected root cause</th>
              <th style={{ width: 92 }}>Route</th>
              <th style={{ width: 176 }}>Status</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((c) => (
              <tr key={c.eval_id}>
                <td className="mono">{c.eval_id}</td>
                <td className="mono">{c.case_id}</td>
                <td>{c.scenario}</td>
                <td className="mono" style={{ fontSize: 11.5 }}>{c.expected_root_cause}</td>
                <td>
                  <Pill tone={c.expected_route === "APPROVE" ? "ok" : "warn"}>{c.expected_route}</Pill>
                </td>
                <td><Pill tone={statusTone(c.status)}>{c.status}</Pill></td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}
