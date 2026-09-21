import { useState } from "react";
import { Card, ModeBanner, Pill, statusTone } from "../components/ui";
import {
  ALL_POLICIES,
  MODE_LABEL,
  claimAssessment,
  claims,
  evidenceLedger,
  policyLedger,
} from "../engine/investigation";

export default function EvidenceExplorer() {
  const [selected, setSelected] = useState(claims[claims.length - 1].claim_id);
  const claim = claims.find((c) => c.claim_id === selected)!;
  const assessment = claimAssessment.assessments.find((a) => a.claim_id === selected)!;
  const supporting = evidenceLedger.filter((e) => claim.evidence_ids.includes(e.evidence_id));
  const governing = ALL_POLICIES.filter((p) => claim.policy_ids.includes(p.policy_id));

  return (
    <>
      <div className="page-head">
        <h2>Evidence Explorer</h2>
        <p>
          Claim-level provenance. Select any claim to see exactly which evidence records and which policies
          support it. A claim whose citations do not resolve is unsupported by construction, not by opinion.
        </p>
      </div>

      <ModeBanner
        label={MODE_LABEL}
        detail="Support status is computed by validate_claim_ledger against the evidence and policy ledgers."
      />

      <div className="grid" style={{ gridTemplateColumns: "minmax(0, 1.15fr) minmax(0, 1fr)", gap: 14 }}>
        <Card title="Claim ledger" sub="Select a claim to inspect its provenance">
          <table>
            <thead>
              <tr>
                <th style={{ width: 96 }}>Claim</th>
                <th>Statement</th>
                <th style={{ width: 150 }}>Status</th>
              </tr>
            </thead>
            <tbody>
              {claims.map((c) => {
                const a = claimAssessment.assessments.find((x) => x.claim_id === c.claim_id)!;
                return (
                  <tr
                    key={c.claim_id}
                    className="claim-row"
                    aria-selected={c.claim_id === selected}
                    onClick={() => setSelected(c.claim_id)}
                  >
                    <td className="mono">{c.claim_id.replace("CL-4003-", "CL-")}</td>
                    <td>{c.statement}</td>
                    <td>
                      <Pill tone={statusTone(a.status)}>{a.status}</Pill>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="footnote">
            Overall ledger status: <Pill tone={statusTone(claimAssessment.overallStatus)}>{claimAssessment.overallStatus}</Pill>{" "}
            because {claimAssessment.unsupportedMaterialClaims.length} material claim cites no resolvable evidence.
          </p>
        </Card>

        <div className="stack">
          <Card
            title="Selected claim"
            right={<Pill tone={statusTone(assessment.status)}>{assessment.status}</Pill>}
          >
            <p style={{ marginTop: 4, fontSize: 14 }}>{claim.statement}</p>
            <dl className="kv" style={{ gridTemplateColumns: "150px 1fr", marginTop: 12 }}>
              <dt>Claim ID</dt>
              <dd className="mono">{claim.claim_id}</dd>
              <dt>Material</dt>
              <dd>{claim.material ? "yes, affects the customer outcome" : "no"}</dd>
              <dt>Decision reason</dt>
              <dd>{assessment.reason}</dd>
              {assessment.missingEvidenceIds.length > 0 && (
                <>
                  <dt>Missing evidence</dt>
                  <dd className="mono" style={{ color: "var(--bad)" }}>
                    {assessment.missingEvidenceIds.join(", ")}
                  </dd>
                </>
              )}
              {assessment.status === "UNSUPPORTED" && (
                <>
                  <dt>Consequence</dt>
                  <dd style={{ color: "var(--bad)" }}>
                    A message asserting this claim cannot be approved. In the real final run the message did not assert it, so it was approved, and the open case went to human review.
                  </dd>
                </>
              )}
            </dl>
          </Card>

          <Card title="Supporting evidence" sub={`${supporting.length} record(s) cited by this claim`}>
            {supporting.length === 0 ? (
              <p style={{ color: "var(--bad)", margin: "6px 0 0" }}>
                This claim cites no evidence at all. It is the customer assertion, carried into the ledger so
                that it can be evaluated rather than quietly accepted.
              </p>
            ) : (
              <table>
                <thead>
                  <tr>
                    <th style={{ width: 106 }}>Evidence</th>
                    <th>Observation</th>
                    <th style={{ width: 96 }}>Period</th>
                  </tr>
                </thead>
                <tbody>
                  {supporting.map((e) => (
                    <tr key={e.evidence_id}>
                      <td className="mono">{e.evidence_id}</td>
                      <td>
                        {e.observation}
                        <div style={{ color: "var(--ink-3)", fontSize: 11.5, marginTop: 3 }}>
                          source {e.source_record_id}
                        </div>
                      </td>
                      <td className="mono">{e.period}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>

          <Card title="Governing policy" sub={`${governing.length} policy reference(s)`}>
            {governing.map((p) => (
              <div key={p.policy_id} style={{ marginBottom: 12 }}>
                <div className="row" style={{ marginBottom: 4 }}>
                  <span className="mono">{p.policy_id}</span>
                  <Pill tone="violet">v{p.version}</Pill>
                  <strong style={{ fontSize: 13 }}>{p.title}</strong>
                </div>
                <div style={{ color: "var(--ink-2)", fontSize: 12.5 }}>{p.purpose}</div>
                {p.prohibited_actions && (
                  <div style={{ color: "var(--bad)", fontSize: 12.5, marginTop: 4 }}>
                    Prohibited: {p.prohibited_actions.join("; ")}
                  </div>
                )}
                {p.human_approval_requirement && (
                  <div style={{ color: "var(--warn)", fontSize: 12.5, marginTop: 3 }}>
                    Human approval: {p.human_approval_requirement}
                  </div>
                )}
              </div>
            ))}
          </Card>
        </div>
      </div>

      <Card
        title="Full evidence ledger"
        sub={`${evidenceLedger.length} records derived from synthetic source documents, ${policyLedger.length} policies in scope`}
        className="card"
      >
        <table>
          <thead>
            <tr>
              <th style={{ width: 106 }}>Evidence ID</th>
              <th style={{ width: 132 }}>Source type</th>
              <th style={{ width: 172 }}>Source record</th>
              <th>Observation</th>
              <th style={{ width: 96 }}>Cited by</th>
            </tr>
          </thead>
          <tbody>
            {evidenceLedger.map((e) => {
              const citedBy = claims.filter((c) => c.evidence_ids.includes(e.evidence_id)).length;
              return (
                <tr key={e.evidence_id}>
                  <td className="mono">{e.evidence_id}</td>
                  <td>{e.source_type}</td>
                  <td className="mono" style={{ fontSize: 11.5 }}>{e.source_record_id}</td>
                  <td>{e.observation}</td>
                  <td>
                    <Pill tone={citedBy > 0 ? "ok" : "muted"}>{citedBy} claim{citedBy === 1 ? "" : "s"}</Pill>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
    </>
  );
}
