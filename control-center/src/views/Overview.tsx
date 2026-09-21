import { Card, Meter, ModeBanner, Pill, Stat, statusTone } from "../components/ui";
import ContentLegend from "../components/ContentLegend";
import {
  AGENTS,
  MODE_LABEL,
  WORKFLOW_VERSION,
  billChange,
  caseInput,
  claimAssessment,
  complianceOutcome,
  evidenceLedger,
  policyLedger,
  usageChange,
} from "../engine/investigation";

export default function Overview() {
  const supported = claimAssessment.assessments.filter((a) => a.status === "SUPPORTED").length;
  const unsupported = claimAssessment.unsupportedMaterialClaims.length;

  return (
    <>
      <div className="page-head">
        <h2>Overview</h2>
        <p>
          GridResolve AI turns a utility high-bill investigation into an evidence-backed, policy-controlled
          decision. Investigation, planning, communication, compliance, human authorization and audit are
          separate roles, so no component both produces an answer and approves it.
        </p>
      </div>

      <ModeBanner
        label={MODE_LABEL}
        detail="Every figure below is computed locally by the deterministic tools from synthetic records. No model call and no Foundry workflow execution."
      />

      <div className="grid g4" style={{ marginBottom: 14 }}>
        <Stat
          label="Active case"
          value={caseInput.case_id}
          meta="Unsupported meter-failure claim"
          mono
        />
        <Stat
          label="Bill change"
          value={`+$${billChange.deltaUsd.toFixed(2)}`}
          meta={`${billChange.percentChange}% versus previous period`}
          tone="warn"
        />
        <Stat
          label="Consumption change"
          value={`+${usageChange.deltaKwh} kWh`}
          meta={`${usageChange.percentChange}% increase`}
          tone="warn"
        />
        <Stat
          label="Compliance decision"
          value={complianceOutcome.decision === "APPROVE" ? "Approve" : "Hold"}
          meta={complianceOutcome.branch === "ESCALATE" ? "Routed to human review" : "Cleared for release"}
          tone={complianceOutcome.branch === "ESCALATE" ? "bad" : "ok"}
        />
      </div>

      <div className="grid g2">
        <Card
          title="Investigation status"
          sub="Derived from the deterministic claim ledger check"
          right={<Pill tone={statusTone(claimAssessment.overallStatus)}>{claimAssessment.overallStatus}</Pill>}
        >
          <dl className="kv">
            <dt>Customer assertion</dt>
            <dd>The meter is broken and caused the increase</dd>
            <dt>Evidence position</dt>
            <dd>Both reads actual, no meter events, diagnostic passed</dd>
            <dt>Material claims</dt>
            <dd>
              {supported} supported, {unsupported} unsupported
            </dd>
            <dt>Release state</dt>
            <dd>
              {complianceOutcome.branch === "ESCALATE"
                ? "Draft withheld, not sent to the customer"
                : "Approved for release"}
            </dd>
          </dl>
          <p className="footnote">{complianceOutcome.summary}</p>
        </Card>

        <Card title="Evidence and policy completeness" sub="Counts of resolvable ledger records">
          <div className="stack">
            <div>
              <div className="spread" style={{ marginBottom: 5 }}>
                <span>Evidence records</span>
                <span className="mono">{evidenceLedger.length}</span>
              </div>
              <Meter value={evidenceLedger.length} max={evidenceLedger.length} tone="ok" />
            </div>
            <div>
              <div className="spread" style={{ marginBottom: 5 }}>
                <span>Policies in scope</span>
                <span className="mono">{policyLedger.length}</span>
              </div>
              <Meter value={policyLedger.length} max={policyLedger.length} tone="ok" />
            </div>
            <div>
              <div className="spread" style={{ marginBottom: 5 }}>
                <span>Claims with resolvable support</span>
                <span className="mono">
                  {supported} of {claimAssessment.assessments.length}
                </span>
              </div>
              <Meter value={supported} max={claimAssessment.assessments.length} tone="warn" />
            </div>
          </div>
          <p className="footnote">
            One material claim, the customer assertion of meter failure, cites no evidence. That is what the
            compliance gate is designed to catch.
          </p>
        </Card>
      </div>

      <div className="grid g2" style={{ marginTop: 14 }}>
        <Card title="Agent team" sub={`${AGENTS.length} specialized roles, ${WORKFLOW_VERSION}`}>
          <table>
            <thead>
              <tr>
                <th>Agent</th>
                <th>Role</th>
                <th style={{ width: 62 }}>Version</th>
              </tr>
            </thead>
            <tbody>
              {AGENTS.map((a) => (
                <tr key={a.name}>
                  <td>{a.name}</td>
                  <td>
                    <Pill tone={a.role === "Control" ? "warn" : a.role === "Decide" ? "violet" : "muted"}>
                      {a.role}
                    </Pill>
                  </td>
                  <td className="mono">v{a.version}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <Card title="Honest status" sub="What has been demonstrated, and what has not">
          <table>
            <tbody>
              <tr>
                <td>Nine agents and workflow v10</td>
                <td><Pill tone="violet">CONFIGURED</Pill></td>
              </tr>
              <tr>
                <td>Routing, release control, case data</td>
                <td><Pill tone="info">STATICALLY_VALIDATED</Pill></td>
              </tr>
              <tr>
                <td>This Control Center</td>
                <td><Pill tone="info">LOCAL DETERMINISTIC</Pill></td>
              </tr>
              <tr>
                <td>30 evaluation cases, 16 red-team scenarios</td>
                <td><Pill tone="muted">PREPARED_ONLY</Pill></td>
              </tr>
              <tr>
                <td>Real Foundry runs of this case, final run 14 of 14 criteria</td>
                <td><Pill tone="ok">3 RUNS, SEE SYSTEM STATUS</Pill></td>
              </tr>
            </tbody>
          </table>
          <p className="footnote">
            This application ran none of them. In the real final run, compliance approved a message that
            asserts no meter failure, the message was released, and the open case went to human review
            separately. The offline walkthrough here models the stricter path, where the customer's meter
            claim itself is put to compliance and refused. No evaluation score or latency is presented,
            because none has been measured.
          </p>
        </Card>
      </div>

      <div style={{ marginTop: 14 }}>
        <ContentLegend current={MODE_LABEL} />
      </div>
    </>
  );
}
