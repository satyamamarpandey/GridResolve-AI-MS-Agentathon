import { Card, Corners, ModeBanner, Pill } from "../components/ui";
import { AGENTS, MODE_LABEL, WORKFLOW_VERSION, auditPacket, projectedCost } from "../engine/investigation";
import { PRICE_USD_PER_1M } from "../tools";
import evaluationSuite from "../data/generated/evaluationSuite.json";
import redTeamPack from "../data/generated/redTeamPack.json";
import { FOUNDRY_EXECUTION_SPANS, FOUNDRY_EXECUTION_STATUS, buildLocalTrace } from "../engine/trace";
import { BILLED_STATUS, FINAL_ACCEPTANCE, FOUNDRY_RUNS, foundryTotals } from "../data/foundryRuns";

const TOTALS = foundryTotals();

interface Resource {
  readonly name: string;
  readonly state: "PROVISIONED" | "NOT_PROVISIONED" | "NOT_INVOKED";
  readonly note: string;
}

const RESOURCES: readonly Resource[] = [
  { name: "Foundry project and nine agents", state: "PROVISIONED", note: "Executed in three real runs of one synthetic case" },
  { name: `Workflow ${WORKFLOW_VERSION}`, state: "PROVISIONED", note: "Active version, executed once, the final run" },
  { name: "gpt-5-mini deployment", state: "PROVISIONED", note: "Used by the three runs, and by nothing else" },
  { name: "text-embedding-3-large", state: "NOT_INVOKED", note: "No embedding call was made" },
  { name: "Azure AI Search", state: "NOT_PROVISIONED", note: "Not created, would incur hourly charges" },
  { name: "Foundry managed memory store", state: "NOT_PROVISIONED", note: "Local browser memory used instead" },
  { name: "Application Insights", state: "PROVISIONED", note: "Created with the project. Holds 61 spans, about 2.5 MB, from the three runs" },
  { name: "API Management gateway", state: "NOT_PROVISIONED", note: "Cost could not be verified in advance" },
  { name: "Azure Speech and Voice Live", state: "NOT_PROVISIONED", note: "Browser Web Speech API used instead" },
  { name: "Storage, database, Functions, Logic Apps", state: "NOT_PROVISIONED", note: "No supporting infrastructure created" },
];

const STATE_TONE = {
  PROVISIONED: "violet",
  NOT_PROVISIONED: "muted",
  NOT_INVOKED: "muted",
} as const;

const PENDING: ReadonlyArray<{ action: string; cost: string; gate: string }> = [
  {
    action: `Foundry evaluation suite, ${evaluationSuite.meta.count} cases`,
    cost: "about $8",
    gate: "Requires explicit spend authorization",
  },
  {
    action: `Adversarial pack, ${redTeamPack.attacks.length} probes`,
    cost: "about $4",
    gate: "Requires explicit spend authorization",
  },
];

export default function SystemStatus() {
  const trace = buildLocalTrace();

  return (
    <>
      <div className="page-head">
        <h2>System Status</h2>
        <p>
          What exists, what has run, and what it has cost. This application ran none of it. The figures
          below are recorded from the evidence of three real Foundry runs.
        </p>
      </div>

      <ModeBanner
        label={`THREE REAL FOUNDRY RUNS, ABOUT $${TOTALS.provisionalUsd.toFixed(2)} PROVISIONAL`}
        detail="Recorded from evidence/runtime, not produced by this application. No embedding, no evaluation run and no billable resource was created. The billed amount is not yet visible in Azure Cost Management."
      />

      <div className="grid g4" style={{ marginBottom: 14 }}>
        <div className="card blueprint stat">
            <Corners />
          <div className="label">Agents configured</div>
          <div className="value mono">{AGENTS.length}</div>
          <div className="meta">all gpt-5-mini, zero tools attached</div>
        </div>
        <div className="card blueprint stat">
            <Corners />
          <div className="label">Real workflow runs</div>
          <div className="value mono">{TOTALS.runs}</div>
          <div className="meta">
            final run {FINAL_ACCEPTANCE.passed} of {FINAL_ACCEPTANCE.criteria} criteria passed
          </div>
        </div>
        <div className="card blueprint stat">
            <Corners />
          <div className="label">Tokens, all three runs</div>
          <div className="value mono">{(TOTALS.inputTokens + TOTALS.outputTokens).toLocaleString("en-US")}</div>
          <div className="meta">
            {TOTALS.inputTokens.toLocaleString("en-US")} in, {TOTALS.outputTokens.toLocaleString("en-US")} out
          </div>
        </div>
        <div className="card blueprint stat">
            <Corners />
          <div className="label">Azure cost, provisional</div>
          <div className="value mono">${TOTALS.provisionalUsd.toFixed(2)}</div>
          <div className="meta">from token counts. Billed amount: {BILLED_STATUS}</div>
        </div>
      </div>

      <div className="grid g2">
        <Card title="Resource inventory" sub="What was created and what was deliberately not">
          <table>
            <thead>
              <tr>
                <th>Resource</th>
                <th style={{ width: 168 }}>State</th>
              </tr>
            </thead>
            <tbody>
              {RESOURCES.map((r) => (
                <tr key={r.name}>
                  <td>
                    {r.name}
                    <div style={{ color: "var(--ink-3)", fontSize: 12, marginTop: 2 }}>{r.note}</div>
                  </td>
                  <td><Pill tone={STATE_TONE[r.state]}>{r.state}</Pill></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <div className="stack">
          <Card title="Cost model" sub="Priced from the published Azure retail rate, not estimated">
            <dl className="kv">
              <dt>Input tokens</dt>
              <dd className="mono">${PRICE_USD_PER_1M.input.toFixed(3)} per million</dd>
              <dt>Cached input</dt>
              <dd className="mono">${PRICE_USD_PER_1M.cachedInput.toFixed(3)} per million</dd>
              <dt>Output tokens</dt>
              <dd className="mono">${PRICE_USD_PER_1M.output.toFixed(3)} per million</dd>
              <dt>Projected, one case</dt>
              <dd className="mono">${projectedCost.totalUsd.toFixed(4)}</dd>
              <dt>Measured, three runs</dt>
              <dd><Pill tone="ok">${TOTALS.provisionalUsd.toFixed(4)} provisional</Pill></dd>
            </dl>
            <p className="footnote">
              The projection exists so that the decision to spend is made with a number in front of it rather
              than after the invoice.
            </p>
          </Card>

          <Card title="Held pending authorization" sub="Prepared, priced, and not run">
            <table>
              <thead>
                <tr>
                  <th>Action</th>
                  <th style={{ width: 92 }}>Cost</th>
                </tr>
              </thead>
              <tbody>
                {PENDING.map((p) => (
                  <tr key={p.action}>
                    <td>
                      {p.action}
                      <div style={{ color: "var(--ink-3)", fontSize: 12, marginTop: 2 }}>{p.gate}</div>
                    </td>
                    <td className="mono">{p.cost}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      </div>

      <div style={{ marginTop: 14 }}>
        <Card
          title="Real Foundry runs of SYN-CASE-4003"
          sub="Recorded from evidence/runtime. This application did not run them and cannot"
        >
          <table>
            <thead>
              <tr>
                <th>Run</th>
                <th>Workflow</th>
                <th>Agents that did their work</th>
                <th>Compliance token</th>
                <th>Sent to the customer</th>
                <th>Audit findings</th>
                <th>Provisional cost</th>
              </tr>
            </thead>
            <tbody>
              {FOUNDRY_RUNS.map((r) => (
                <tr key={r.evidenceFolder}>
                  <td>
                    {r.label}
                    <div className="mono" style={{ color: "var(--ink-3)", fontSize: 11, marginTop: 2 }}>
                      {r.evidenceFolder}
                    </div>
                  </td>
                  <td className="mono">{r.workflowVersion}</td>
                  <td className="mono">{r.agentsThatDidTheirWork}</td>
                  <td><Pill tone={r.complianceToken === "APPROVED" ? "ok" : "warn"}>{r.complianceToken}</Pill></td>
                  <td>{r.sentToCustomer}</td>
                  <td className="mono">{r.auditFindings}</td>
                  <td className="mono">${r.provisionalUsd.toFixed(4)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="footnote">
            Final run: {FINAL_ACCEPTANCE.evidenceLedgerEntries} evidence entries, {FINAL_ACCEPTANCE.policiesMapped}{" "}
            policies mapped, criteria fixed beforehand in {FINAL_ACCEPTANCE.plan}, result in {FINAL_ACCEPTANCE.result}.
            One run of one synthetic case. Not production-ready.
          </p>
        </Card>
      </div>

      <div className="grid g2" style={{ marginTop: 14 }}>
        <Card title="Audit packet" sub="Assembled locally by build_audit_packet, the offline demonstration, not a Foundry audit">
          <dl className="kv">
            <dt>Case</dt>
            <dd className="mono">{auditPacket.case_id}</dd>
            <dt>Workflow version</dt>
            <dd className="mono">{auditPacket.workflow_version}</dd>
            <dt>Evidence records</dt>
            <dd className="mono">{auditPacket.evidence_ids.length}</dd>
            <dt>Policies applied</dt>
            <dd className="mono">{auditPacket.policy_ids.length}</dd>
            <dt>Compliance decision</dt>
            <dd><Pill tone="warn">{auditPacket.compliance_decision}</Pill></dd>
            <dt>Human review</dt>
            <dd><Pill tone="warn">{auditPacket.human_review_status}</Pill></dd>
            <dt>Final disposition</dt>
            <dd><Pill tone="warn">{auditPacket.final_disposition}</Pill></dd>
            <dt>Execution status</dt>
            <dd><Pill tone="muted">{auditPacket.execution_status}</Pill></dd>
          </dl>
        </Card>

        <Card title="Data classification" sub="Every record in this application">
          <dl className="kv">
            <dt>Classification</dt>
            <dd><Pill tone="ok">SYNTHETIC_ONLY</Pill></dd>
            <dt>Customer data</dt>
            <dd>None. No real account, meter, name, address or contact detail appears anywhere.</dd>
            <dt>Credentials in the browser</dt>
            <dd>None. No token, key or connection string is present in this application bundle.</dd>
            <dt>Network calls</dt>
            <dd>None at runtime. The application is fully local and works with no network.</dd>
            <dt>Mode</dt>
            <dd className="mono" style={{ fontSize: 11.5 }}>{MODE_LABEL}</dd>
          </dl>
          <p className="footnote">
            Case identifiers follow the SYN-CASE pattern, and the memory layer refuses to store anything that
            does not match it. That is a guard rather than a convention.
          </p>
        </Card>
      </div>

      <div className="grid g2" style={{ marginTop: 14 }}>
        <Card
          title="LOCAL_EXECUTION trace"
          sub="OpenTelemetry-compatible spans, timed from this page load"
          right={<Pill tone="ok">{trace.summary.span_count} spans</Pill>}
        >
          <table>
            <thead>
              <tr>
                <th style={{ width: 92 }}>Span</th>
                <th>Operation</th>
                <th style={{ width: 84 }}>Duration</th>
                <th style={{ width: 68 }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {trace.spans.map((s) => (
                <tr key={s.span_id}>
                  <td className="mono" style={{ fontSize: 11.5 }}>
                    {s.parent_span_id ? `└ ${s.span_id}` : s.span_id}
                  </td>
                  <td className="mono" style={{ fontSize: 11.5 }}>{s.operation}</td>
                  <td className="mono">{s.duration_ms.toFixed(3)} ms</td>
                  <td><Pill tone={s.status === "OK" ? "ok" : "bad"}>{s.status}</Pill></td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="footnote">
            These durations are measured, not assigned. Every span reports
            <code className="inline" style={{ margin: "0 4px" }}>gen_ai.usage.total_tokens = 0</code>
            because no model was involved in this local trace. Compliance result {trace.summary.compliance_result}, disposition{" "}
            {trace.summary.final_disposition}.
          </p>
        </Card>

        <Card
          title="FOUNDRY_EXECUTION trace"
          sub="Spans from a real workflow run"
          right={<Pill tone="muted">{FOUNDRY_EXECUTION_SPANS.length} spans</Pill>}
        >
          <div className="banner warn" style={{ marginTop: 4 }}>
            <strong>{FOUNDRY_EXECUTION_STATUS.status}</strong>
            {FOUNDRY_EXECUTION_STATUS.reason}
          </div>
          <dl className="kv" style={{ marginTop: 12 }}>
            <dt>Workflow runs</dt>
            <dd className="mono">{FOUNDRY_EXECUTION_STATUS.workflow_runs}</dd>
            <dt>Spans imported here</dt>
            <dd className="mono">{FOUNDRY_EXECUTION_STATUS.span_count}</dd>
            <dt>Spans held by the platform</dt>
            <dd className="mono">{FOUNDRY_EXECUTION_STATUS.platform_span_count}</dd>
            <dt>Collector</dt>
            <dd><Pill tone="muted">Application Insights, connected to the Foundry project</Pill></dd>
          </dl>
          <p className="footnote">
            This dataset is empty by construction. The platform holds the real spans, this app imports none,
            and there is no code path that can synthesize a Foundry span, because inventing one would be
            fabricating runtime evidence. {FOUNDRY_EXECUTION_STATUS.how_to_populate}
          </p>
        </Card>
      </div>
    </>
  );
}
