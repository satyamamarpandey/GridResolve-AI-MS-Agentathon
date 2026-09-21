import { useState } from "react";
import { Card, ModeBanner, Pill } from "../components/ui";
import { AGENTS, WORKFLOW_VERSION, complianceOutcome } from "../engine/investigation";

const investigators = AGENTS.slice(0, 7);
const escalation = AGENTS[7];
const audit = AGENTS[8];

export default function AgentWorkflow() {
  const [open, setOpen] = useState<string | null>("EvidenceComplianceAgent");
  const detail = AGENTS.find((a) => a.name === open);

  return (
    <>
      <div className="page-head">
        <h2>Agent Workflow</h2>
        <p>
          The actual deployed orchestration, {WORKFLOW_VERSION}. Execution is strictly sequential. No parallel
          fan-out, no fan-in, and no automatic correction loop is implemented, so none is drawn here.
        </p>
      </div>

      <ModeBanner
        label="ACTUAL FOUNDRY CONFIGURATION"
        detail="Node order and autoSend settings follow the deployed workflow definition. The live version is v10, which ran once for real, in the final run. This page draws the configuration. It does not replay that run."
      />

      <div className="grid" style={{ gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: 14 }}>
        <Card title="Runtime sequence" sub="Click any agent for its contract">
          <div className="flow">
            {investigators.map((a, i) => (
              <button
                key={a.name}
                className={`node${a.role === "Control" ? " control" : ""}`}
                style={{ textAlign: "left", cursor: "pointer", font: "inherit", color: "inherit", width: "100%" }}
                onClick={() => setOpen(a.name)}
              >
                <span className="idx">{i + 1}</span>
                <span className="grow">
                  <span className="nm">{a.name}</span>
                  <span className="rs" style={{ display: "block" }}>{a.responsibility}</span>
                </span>
                <Pill tone="muted">autoSend false</Pill>
              </button>
            ))}

            <div style={{ padding: "10px 13px", border: "1px dashed var(--line)", borderRadius: 8, background: "var(--surface-2)" }}>
              <div className="row" style={{ justifyContent: "space-between" }}>
                <strong style={{ fontSize: 13 }}>ConditionGroup, fail closed</strong>
                <Pill tone="warn">decision point</Pill>
              </div>
              <code className="inline" style={{ display: "block", marginTop: 8, fontSize: 11.5, padding: "6px 8px" }}>
                ={'("ROUTE_DECISION::GRIDRESOLVE_APPROVED" in Local.Var1497)'}
              </code>
            </div>

            <div className="branch">
              <div className="node" style={{ borderColor: "#a9cbb7" }}>
                <span className="idx" style={{ background: "#e8f3ec", color: "var(--ok)" }}>A</span>
                <span className="grow">
                  <span className="nm">SendActivity, release approved message</span>
                  <span className="rs" style={{ display: "block" }}>Only on an exact token match</span>
                </span>
              </div>
              <button
                className="node control"
                style={{ textAlign: "left", cursor: "pointer", font: "inherit", color: "inherit", width: "100%" }}
                onClick={() => setOpen(escalation.name)}
              >
                <span className="idx">8</span>
                <span className="grow">
                  <span className="nm">{escalation.name}</span>
                  <span className="rs" style={{ display: "block" }}>Default branch, every other outcome</span>
                </span>
                <Pill tone="bad">default</Pill>
              </button>
            </div>

            <button
              className="node control"
              style={{ textAlign: "left", cursor: "pointer", font: "inherit", color: "inherit", width: "100%" }}
              onClick={() => setOpen(audit.name)}
            >
              <span className="idx">9</span>
              <span className="grow">
                <span className="nm">{audit.name}</span>
                <span className="rs" style={{ display: "block" }}>Terminal on both paths</span>
              </span>
              <Pill tone="muted">autoSend true</Pill>
            </button>
          </div>

          <p className="footnote">
            For this case the deterministic engine reaches{" "}
            <Pill tone={complianceOutcome.branch === "ESCALATE" ? "bad" : "ok"}>{complianceOutcome.branch}</Pill>{" "}
            locally. That is a local computation of the same rule, not an observed Foundry run.
          </p>
        </Card>

        <div className="stack">
          {detail && (
            <Card title={detail.name} sub={`v${detail.version}, ${detail.role}`} right={<Pill tone={detail.role === "Control" ? "warn" : "muted"}>{detail.role}</Pill>}>
              <dl className="kv" style={{ gridTemplateColumns: "150px 1fr" }}>
                <dt>Responsibility</dt>
                <dd>{detail.responsibility}</dd>
                <dt>Input contract</dt>
                <dd className="mono" style={{ fontSize: 11.5 }}>{detail.input}</dd>
                <dt>Output contract</dt>
                <dd className="mono" style={{ fontSize: 11.5 }}>{detail.output}</dd>
                <dt>Evidence requirement</dt>
                <dd>{detail.evidenceRequirement}</dd>
                <dt>Policy requirement</dt>
                <dd>{detail.policyRequirement}</dd>
                <dt>Failure behavior</dt>
                <dd style={{ color: "var(--warn)" }}>{detail.failureBehavior}</dd>
              </dl>
            </Card>
          )}

          <Card title="Configured versus production target" sub="Drawn separately so the diagram is not aspirational">
            <table>
              <thead>
                <tr>
                  <th>Capability</th>
                  <th style={{ width: 176 }}>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr><td>Sequential nine-agent orchestration</td><td><Pill tone="violet">CONFIGURED</Pill></td></tr>
                <tr><td>Fail-closed routing, escalation default</td><td><Pill tone="info">STATICALLY_VALIDATED</Pill></td></tr>
                <tr><td>Draft withheld until approved</td><td><Pill tone="info">STATICALLY_VALIDATED</Pill></td></tr>
                <tr><td>Parallel investigation fan-out and join</td><td><Pill tone="muted">PRODUCTION_TARGET</Pill></td></tr>
                <tr><td>Automatic replan and rewrite loops</td><td><Pill tone="muted">PRODUCTION_TARGET</Pill></td></tr>
                <tr><td>Four-way typed decision routing</td><td><Pill tone="muted">PRODUCTION_TARGET</Pill></td></tr>
                <tr><td>Real Foundry runs, recorded on System Status, not replayed here</td><td><Pill tone="ok">3 RUNS</Pill></td></tr>
              </tbody>
            </table>
          </Card>
        </div>
      </div>
    </>
  );
}
