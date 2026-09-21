import { useState } from "react";
import { Card, Corners, Pill, statusTone } from "../components/ui";
import {
  FIXTURE_BANNER,
  SNAPSHOTS,
  type SnapshotId,
  buildAssistantReply,
  buildClaimRows,
  describeFigureDivergence,
  describeVersionMismatch,
  expectations,
  meterFailureClaim,
  summarize,
} from "../fixtures";
import { WORKFLOW_VERSION, billChange, usageChange } from "../engine/investigation";

const SECTION: Record<string, string> = {
  Overview: "Shows a synthetic case without counting it as a live executed workflow.",
  Cases: "SYN-CASE-4003 can be selected and customer request is visible.",
};

export default function FixtureCase() {
  const [active, setActive] = useState<SnapshotId>("rejection");
  const [selectedClaim, setSelectedClaim] = useState<string | null>(null);
  const [assistantAsked, setAssistantAsked] = useState(false);

  const entry = SNAPSHOTS.find((s) => s.id === active)!;
  const snap = entry.snapshot;
  const summary = summarize(snap);
  const claimRows = buildClaimRows(snap);
  const meterClaim = meterFailureClaim(snap);
  const version = describeVersionMismatch(WORKFLOW_VERSION);
  const divergence = describeFigureDivergence({
    previousUsd: billChange.previousUsd,
    currentUsd: billChange.currentUsd,
    previousKwh: usageChange.previousKwh,
    currentKwh: usageChange.currentKwh,
  });
  const claimRow = claimRows.find((r) => r.claim.claim_id === selectedClaim) ?? null;
  const reply = buildAssistantReply(snap);

  return (
    <>
      <div className="page-head">
        <h2>UI Test Fixture</h2>
        <p>
          Display-only snapshots of SYN-CASE-4003 supplied for local frontend testing. Nothing here was
          produced by an agent, and nothing here is evidence that the Foundry gate works.
        </p>
      </div>

      <div className="banner warn" data-testid="fixture-banner">
        <strong>{FIXTURE_BANNER}</strong>
        Snapshot declares <code className="inline">{summary.workflowVersion}</code>. Identifiers keep their
        SYN- prefix. Canonical engine data is untouched and remains the default elsewhere in this app.
      </div>

      {version.mismatch && (
        <Card
          title="Data contract mismatch, reported not resolved"
          sub="Detected automatically by comparing the fixture against the canonical engine"
          className="card"
        >
          <table>
            <tbody>
              <tr>
                <td style={{ width: 220 }}>Fixture workflow version</td>
                <td className="mono"><Pill tone="warn">{version.fixtureVersion}</Pill></td>
              </tr>
              <tr>
                <td>Canonical engine version</td>
                <td className="mono"><Pill tone="violet">{version.canonicalVersion}</Pill></td>
              </tr>
              <tr>
                <td>Identifier scheme</td>
                <td>
                  Fixture uses <code className="inline">SYN-EV-</code> and{" "}
                  <code className="inline">SYN-CL-</code>, canonical uses{" "}
                  <code className="inline">EV-</code> and <code className="inline">CL-</code>
                </td>
              </tr>
              <tr>
                <td>Handling</td>
                <td>{version.handling}</td>
              </tr>
            </tbody>
          </table>
          <p className="footnote">
            The supplied bundle README states: do not silently relabel a v4 case state as v5. It is therefore
            shown under its own version rather than normalised into the canonical contract.
          </p>
        </Card>
      )}

      {divergence.differs && (
        <Card
          title="Figure drift against the canonical case"
          sub="These values should match the rest of the application and do not"
          right={<Pill tone="bad">FIGURE DRIFT</Pill>}
        >
          <table>
            <thead>
              <tr>
                <th style={{ width: 180 }}>Figure</th>
                <th>Canonical, used everywhere else</th>
                <th>This fixture</th>
              </tr>
            </thead>
            <tbody>
              {divergence.rows.map((row) => (
                <tr key={row.label}>
                  <td>{row.label}</td>
                  <td className="mono">{row.canonical}</td>
                  <td className="mono">
                    {row.differs ? <Pill tone="warn">{row.fixture}</Pill> : row.fixture}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="footnote">{divergence.explanation}</p>
        </Card>
      )}

      <Card
        title="Snapshot"
        sub={entry.description}
        right={
          <div className="row" style={{ flexWrap: "wrap", gap: 5 }}>
            {SNAPSHOTS.map((s) => (
              <button
                key={s.id}
                className={`seg${s.id === active ? " on" : ""}`}
                onClick={() => {
                  setActive(s.id);
                  setSelectedClaim(null);
                }}
              >
                {s.label}
              </button>
            ))}
          </div>
        }
        className="card"
      >
        {/* Assertion: Overview */}
        <div className="grid g4" style={{ marginBottom: 6 }}>
          <div className="card blueprint stat">
            <Corners />
            <div className="label">case state</div>
            <div className="value mono" style={{ fontSize: 17 }}>{summary.caseState}</div>
            <div className="meta">{SECTION.Overview}</div>
          </div>
          <div className="card blueprint stat">
            <Corners />
            <div className="label">executed workflows</div>
            <div className="value mono">0</div>
            <div className="meta">fixture is not counted as a run</div>
          </div>
          <div className="card blueprint stat">
            <Corners />
            <div className="label">model calls / tokens</div>
            <div className="value mono">{summary.modelCalls} / {summary.tokens}</div>
            <div className="meta">no runtime, no cost</div>
          </div>
          <div className="card blueprint stat">
            <Corners />
            <div className="label">unsupported claims</div>
            <div className="value mono" style={{ color: summary.unsupportedCount > 0 ? "var(--bad)" : undefined }}>
              {summary.unsupportedCount}
            </div>
            <div className="meta">declared by the fixture</div>
          </div>
        </div>
      </Card>

      <div className="grid g2" style={{ marginTop: 14 }}>
        {/* Assertion: Cases */}
        <Card title="Case" sub={SECTION.Cases}>
          <dl className="kv">
            <dt>Case ID</dt>
            <dd className="mono">{snap.case_id}</dd>
            <dt>Dataset version</dt>
            <dd className="mono">{snap.dataset_version}</dd>
            <dt>Policy version</dt>
            <dd className="mono">{snap.policy_version}</dd>
            <dt>Correction count</dt>
            <dd className="mono">{snap.correction_count}</dd>
          </dl>
          <p style={{ marginTop: 12, fontSize: 14, fontStyle: "italic", color: "var(--ink-2)" }}>
            "{snap.customer_request}"
          </p>
          {snap.triage.display_status && (
            <p className="footnote" style={{ marginTop: 8 }}>
              Triage intent {snap.triage.intent}, meter concern {String(snap.triage.meter_concern)}.{" "}
              <Pill tone="warn">{snap.triage.display_status}</Pill>
            </p>
          )}
        </Card>

        {/* Assertion: Agent Workflow */}
        <Card title="Agent Workflow" sub="Configured graph only, the snapshot does not animate as a run">
          <table>
            <tbody>
              <tr><td>Configured agent graph</td><td><Pill tone="violet">CONFIGURED</Pill></td></tr>
              <tr><td>This snapshot as a Foundry execution</td><td><Pill tone="bad">NOT EXECUTED</Pill></td></tr>
              <tr><td>Animated runtime progression</td><td><Pill tone="muted">not rendered</Pill></td></tr>
              <tr><td>Trace IDs, latency, token counts</td><td><Pill tone="muted">none invented</Pill></td></tr>
            </tbody>
          </table>
          <p className="footnote">
            The canonical Agent Workflow view is unchanged and still renders the deployed {WORKFLOW_VERSION}{" "}
            configuration. This fixture does not drive it.
          </p>
        </Card>
      </div>

      {/* Assertion: Claims + Evidence Explorer */}
      <div className="grid" style={{ gridTemplateColumns: "minmax(0, 1.1fr) minmax(0, 1fr)", gap: 14, marginTop: 14 }}>
        <Card title="Claims" sub="Select a claim to inspect its provenance">
          {claimRows.length === 0 ? (
            <p style={{ color: "var(--ink-3)", margin: "6px 0 0", fontSize: 13 }}>
              This snapshot has an empty claim ledger. Nothing has been asserted yet.
            </p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th style={{ width: 132 }}>Claim</th>
                  <th>Assertion</th>
                  <th style={{ width: 138 }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {claimRows.map((r) => (
                  <tr
                    key={r.claim.claim_id}
                    className="claim-row"
                    aria-selected={r.claim.claim_id === selectedClaim}
                    data-testid={`claim-${r.claim.claim_id}`}
                    onClick={() => setSelectedClaim(r.claim.claim_id)}
                  >
                    <td className="mono" style={{ fontSize: 11.5 }}>{r.claim.claim_id}</td>
                    <td>
                      {r.claim.claim_text}
                      <div style={{ color: "var(--ink-3)", fontSize: 11.5, marginTop: 3 }}>
                        {r.claim.claim_type}, confidence {r.claim.confidence}
                      </div>
                    </td>
                    <td><Pill tone={statusTone(r.claim.status)}>{r.claim.status}</Pill></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {meterClaim && (
            <p className="footnote" data-testid="meter-claim-note">
              The meter-failure assertion <code className="inline">{meterClaim.claim_id}</code> is{" "}
              <Pill tone={statusTone(meterClaim.status)}>{meterClaim.status}</Pill> and cites{" "}
              {meterClaim.evidence_ids.length === 0
                ? "no affirmative diagnostic evidence at all"
                : `${meterClaim.evidence_ids.length} evidence record(s)`}
              .
            </p>
          )}
        </Card>

        <Card
          title="Evidence Explorer"
          sub={claimRow ? `Provenance for ${claimRow.claim.claim_id}` : "Select a claim, or browse the ledger below"}
        >
          {claimRow ? (
            <>
              <p style={{ marginTop: 4, fontSize: 13.5 }}>{claimRow.claim.claim_text}</p>
              {claimRow.citesNoEvidence ? (
                <div className="banner warn" style={{ marginTop: 12 }} data-testid="no-evidence-warning">
                  <strong>NO SUPPORTING EVIDENCE</strong>
                  This claim links to no affirmative diagnostic evidence. It cannot be substantiated from the
                  supplied records.
                </div>
              ) : (
                <table style={{ marginTop: 10 }}>
                  <thead>
                    <tr>
                      <th style={{ width: 128 }}>Evidence</th>
                      <th>Field</th>
                      <th style={{ width: 96 }}>Value</th>
                    </tr>
                  </thead>
                  <tbody>
                    {claimRow.supporting.map((e) => (
                      <tr key={e.evidence_id}>
                        <td className="mono" style={{ fontSize: 11.5 }}>{e.evidence_id}</td>
                        <td>
                          {e.observation}
                          <div style={{ color: "var(--ink-3)", fontSize: 11.5, marginTop: 2 }}>
                            {e.source_record_id}, {e.period}
                          </div>
                        </td>
                        <td className="mono">{String(e.value)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {claimRow.governing.length > 0 && (
                <div style={{ marginTop: 12 }}>
                  {claimRow.governing.map((p) => (
                    <div key={p.policy_id} style={{ marginBottom: 8 }}>
                      <div className="row" style={{ marginBottom: 3 }}>
                        <span className="mono">{p.policy_id}</span>
                        <Pill tone="violet">v{p.policy_version}</Pill>
                      </div>
                      <div style={{ fontSize: 12.5, color: "var(--ink-2)" }}>{p.rule}</div>
                    </div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <p style={{ color: "var(--ink-3)", fontSize: 13, margin: "6px 0 0" }}>
              Synthetic meter diagnostics in this fixture are observations. None of them asserts a fault.
            </p>
          )}
        </Card>
      </div>

      {/* Assertion: Governance */}
      <div className="grid g2" style={{ marginTop: 14 }}>
        <Card
          title="Governance"
          sub="Simulated compliance decision"
          right={
            snap.compliance_result ? (
              <Pill tone="bad">{snap.compliance_result.decision}</Pill>
            ) : (
              <Pill tone="muted">NOT_REACHED</Pill>
            )
          }
        >
          {snap.compliance_result ? (
            <>
              <dl className="kv">
                <dt>Decision</dt>
                <dd data-testid="compliance-decision"><Pill tone="bad">{snap.compliance_result.decision}</Pill></dd>
                <dt>Groundedness</dt>
                <dd className="mono" style={{ fontSize: 11.5, color: "var(--bad)" }}>
                  {snap.compliance_result.groundedness}
                </dd>
                <dt>Unsupported claims</dt>
                <dd className="mono">{snap.compliance_result.unsupported_claim_ids.join(", ")}</dd>
                <dt>Policies applied</dt>
                <dd className="row" style={{ gap: 5 }}>
                  {snap.compliance_result.policy_ids.map((id) => (
                    <Pill key={id} tone={id === "POL-MTR-003" ? "warn" : "violet"}>{id}</Pill>
                  ))}
                </dd>
                <dt>Missing evidence</dt>
                <dd className="mono" style={{ fontSize: 11.5 }}>
                  {snap.compliance_result.missing_evidence.join(", ")}
                </dd>
                <dt>Customer safe</dt>
                <dd>
                  <Pill tone={snap.compliance_result.customer_safe ? "ok" : "bad"}>
                    {String(snap.compliance_result.customer_safe)}
                  </Pill>
                </dd>
                <dt>Execution status</dt>
                <dd><Pill tone="warn">{snap.compliance_result.execution_status}</Pill></dd>
              </dl>
              <p className="footnote">
                This is a supplied fixture outcome. It is not evidence that the actual Foundry gate works, and
                not evidence that a customer message was withheld at runtime.
              </p>
            </>
          ) : (
            <p style={{ color: "var(--ink-3)", fontSize: 13 }}>
              Compliance review has not been reached in this snapshot.
            </p>
          )}
        </Card>

        {/* Assertion: Supervisor Review */}
        <Card title="Supervisor Review" sub="Simulated pending specialist decision">
          {snap.escalation ? (
            <>
              <dl className="kv">
                <dt>Status</dt>
                <dd><Pill tone="warn">{snap.escalation.status}</Pill></dd>
                <dt>Reviewer role</dt>
                <dd>{snap.escalation.reviewer_role}</dd>
                <dt>Reason</dt>
                <dd>{snap.escalation.reason}</dd>
                <dt>Authorization</dt>
                <dd data-testid="authorization-status">
                  <Pill tone="bad">{snap.escalation.authorization_status}</Pill>
                </dd>
                <dt>Synthetic UI only</dt>
                <dd><Pill tone="warn">{String(snap.escalation.synthetic_ui_only)}</Pill></dd>
              </dl>
              <p className="footnote">
                No approval is recorded and no reviewer action has been taken. The decision is pending by
                construction, because this is a display snapshot rather than a workflow state.
              </p>
            </>
          ) : (
            <p style={{ color: "var(--ink-3)", fontSize: 13 }}>No escalation in this snapshot.</p>
          )}
        </Card>
      </div>

      {/* Assertion: Offline assistant */}
      <div className="grid g2" style={{ marginTop: 14 }}>
        <Card title="Offline assistant" sub="Answers only from the supplied synthetic evidence">
          <div className="chat" style={{ height: "auto" }}>
            <div className="chat-log" style={{ maxHeight: 300 }}>
              <div className="msg user">
                <div className="who">Customer</div>
                <p style={{ margin: 0 }}>{snap.customer_request}</p>
              </div>
              {assistantAsked && (
                <div className="msg system" data-testid="assistant-reply">
                  <div className="who">GridResolve AI, offline</div>
                  <p style={{ margin: "0 0 8px" }}>{reply.findings}</p>
                  <p style={{ margin: "0 0 8px" }}>{reply.limits}</p>
                  <div className="row" style={{ flexWrap: "wrap", gap: 5 }}>
                    {reply.policyIds.map((id) => (
                      <Pill key={id} tone="violet">{id}</Pill>
                    ))}
                    <Pill tone="warn">no refund promised</Pill>
                  </div>
                </div>
              )}
            </div>
            <div className="suggest">
              <button onClick={() => setAssistantAsked(true)} data-testid="assistant-ask">
                Confirm the meter caused this and fix the charge
              </button>
              <button onClick={() => setAssistantAsked(false)}>Reset</button>
            </div>
          </div>
        </Card>

        {/* Assertion: Audit / monitoring */}
        <Card title="Audit and monitoring" sub="Fixture audit record, verbatim">
          {snap.audit_record ? (
            <>
              <dl className="kv">
                <dt>Audit status</dt>
                <dd data-testid="audit-status"><Pill tone="warn">{snap.audit_record.audit_status}</Pill></dd>
                <dt>Execution status</dt>
                <dd data-testid="execution-status"><Pill tone="bad">{snap.audit_record.execution_status}</Pill></dd>
                <dt>Evidence IDs</dt>
                <dd className="mono">{snap.audit_record.evidence_ids.length}</dd>
                <dt>Claim IDs</dt>
                <dd className="mono">{snap.audit_record.claim_ids.length}</dd>
                <dt>Policy IDs</dt>
                <dd className="mono">{snap.audit_record.policy_ids.length}</dd>
                <dt>Trace IDs</dt>
                <dd><Pill tone="muted">none, not invented</Pill></dd>
                <dt>Tokens and latency</dt>
                <dd><Pill tone="muted">none, nothing ran</Pill></dd>
                <dt>Runtime charges</dt>
                <dd><Pill tone="ok">$0.00</Pill></dd>
              </dl>
              <p className="footnote">{snap.audit_record.note}</p>
            </>
          ) : (
            <p style={{ color: "var(--ink-3)", fontSize: 13 }}>
              No audit record in this snapshot. Nothing is fabricated to fill the gap.
            </p>
          )}
        </Card>
      </div>

      <Card
        title="Expected UI assertions"
        sub={`${expectations.expected_ui_assertions.length} assertions from the supplied bundle, verified by the local test suite`}
        className="card"
      >
        <table>
          <thead>
            <tr>
              <th style={{ width: 170 }}>View</th>
              <th>Check</th>
            </tr>
          </thead>
          <tbody>
            {expectations.expected_ui_assertions.map((a) => (
              <tr key={a.view}>
                <td><strong>{a.view}</strong></td>
                <td>{a.check}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="footnote">
          Expected root cause <code className="inline">{expectations.expected_root_cause}</code>, expected
          route <code className="inline">{expectations.expected_route}</code>. {expectations.note}
        </p>
      </Card>
    </>
  );
}
