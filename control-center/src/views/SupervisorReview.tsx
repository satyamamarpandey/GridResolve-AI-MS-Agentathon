import { useState } from "react";
import { Card, ModeBanner, Pill } from "../components/ui";
import {
  ALL_POLICIES,
  auditPacket,
  claimAssessment,
  claims,
  complianceOutcome,
  escalation,
  evidenceLedger,
} from "../engine/investigation";

interface Reviewer {
  readonly id: string;
  readonly role: string;
  readonly owns: string;
  readonly decides: string;
}

const REVIEWERS: readonly Reviewer[] = [
  {
    id: "REV-METER-OPS",
    role: "Meter operations specialist",
    owns: "Meter condition and field test authorization",
    decides: "Whether a field meter test is warranted and what the meter condition is",
  },
  {
    id: "REV-BILLING",
    role: "Billing adjustment authority",
    owns: "Credits, rebills and adjustment ledger entries",
    decides: "Whether any monetary adjustment is applied to the account",
  },
  {
    id: "REV-COMPLIANCE",
    role: "Regulatory compliance reviewer",
    owns: "Regulatory commitments and disclosure language",
    decides: "Whether the outbound wording meets regulatory obligations",
  },
  {
    id: "REV-SUPERVISOR",
    role: "Customer care supervisor",
    owns: "Customer relationship and commitment handling",
    decides: "Tone, timing and what the customer is told in the interim",
  },
];

type Decision = "APPROVE_RELEASE" | "REQUEST_METER_TEST" | "REQUEST_MORE_EVIDENCE" | "REJECT_DRAFT";

const DECISIONS: readonly { id: Decision; label: string; effect: string; tone: "ok" | "warn" | "bad" | "info" }[] = [
  {
    id: "APPROVE_RELEASE",
    label: "Approve release as drafted",
    effect:
      "Would release the customer message. Note that the deterministic gate did not reach this state on its own, because a material claim is unsupported.",
    tone: "ok",
  },
  {
    id: "REQUEST_METER_TEST",
    label: "Authorize a field meter test",
    effect:
      "Creates the evidence that is currently missing. Only after a test result exists can anyone state a meter condition under POL-MTR-003.",
    tone: "warn",
  },
  {
    id: "REQUEST_MORE_EVIDENCE",
    label: "Request additional evidence",
    effect: "Returns the case for further investigation without contacting the customer with a conclusion.",
    tone: "info",
  },
  {
    id: "REJECT_DRAFT",
    label: "Reject the draft wording",
    effect: "Withholds the draft and requires a rewrite before any customer contact.",
    tone: "bad",
  },
];

const unsupported = claimAssessment.assessments.filter((a) => a.status !== "SUPPORTED");

const isRecommended = (r: Reviewer): boolean =>
  r.role.toLowerCase() === escalation.recommendedReviewer.toLowerCase();

export default function SupervisorReview() {
  const [reviewer, setReviewer] = useState(REVIEWERS[0].id);
  const [decision, setDecision] = useState<Decision | null>(null);
  const [note, setNote] = useState("");
  const chosen = DECISIONS.find((d) => d.id === decision);
  const person = REVIEWERS.find((r) => r.id === reviewer)!;

  return (
    <>
      <div className="page-head">
        <h2>Supervisor Review</h2>
        <p>
          What a human reviewer actually receives when the case is escalated. The purpose of this screen is to
          make a decision fast and defensibly, so it separates what is known from what is not.
        </p>
      </div>

      <ModeBanner
        label="SIMULATED REVIEWER DECISION, NOT A REAL APPROVAL"
        detail="Any decision recorded here is a local user interface simulation on synthetic data. No approval is transmitted, no workflow resumes, and nothing is sent to a customer."
      />

      <div className="grid" style={{ gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: 14 }}>
        <div className="stack">
          <Card
            title="Escalation package"
            right={<Pill tone="warn">{complianceOutcome.branch}</Pill>}
          >
            <dl className="kv">
              <dt>Case ID</dt>
              <dd className="mono">{auditPacket.case_id}</dd>
              <dt>Risk class</dt>
              <dd><Pill tone="warn">{escalation.riskClass}</Pill></dd>
              <dt>Escalation reason</dt>
              <dd>{escalation.reason}</dd>
              <dt>Recommended reviewer</dt>
              <dd className="mono">{escalation.recommendedReviewer}</dd>
              <dt>Decision required</dt>
              <dd>{escalation.requiredDecision}</dd>
              <dt>Customer contacted</dt>
              <dd><Pill tone="muted">interim message only, no conclusion</Pill></dd>
            </dl>
            <p className="footnote" style={{ marginBottom: 0 }}>
              Interim wording sent to the customer: {escalation.customerSafeInterimMessage}
            </p>
          </Card>

          <Card title="Open questions" sub="Stated explicitly so the reviewer is not asked to guess">
            <ul className="bullets">
              {escalation.unknowns.map((u) => (
                <li key={u}>{u}</li>
              ))}
            </ul>
          </Card>

          <Card title="What is established" sub={`${claims.length - unsupported.length} of ${claims.length} claims fully supported`}>
            <ul className="bullets">
              {claimAssessment.assessments
                .filter((a) => a.status === "SUPPORTED")
                .map((a) => {
                  const c = claims.find((x) => x.claim_id === a.claim_id)!;
                  return (
                    <li key={a.claim_id}>
                      {c.statement}{" "}
                      <span className="mono" style={{ color: "var(--ink-3)", fontSize: 11.5 }}>
                        [{c.evidence_ids.join(", ")}]
                      </span>
                    </li>
                  );
                })}
            </ul>
          </Card>

          <Card title="What is not established" sub="The reason a human is needed at all">
            {unsupported.map((a) => {
              const c = claims.find((x) => x.claim_id === a.claim_id)!;
              return (
                <div key={a.claim_id} style={{ marginBottom: 12 }}>
                  <div className="row" style={{ marginBottom: 4 }}>
                    <span className="mono">{a.claim_id}</span>
                    <Pill tone={a.status === "UNSUPPORTED" ? "bad" : "warn"}>{a.status}</Pill>
                  </div>
                  <div style={{ fontSize: 13 }}>{c.statement}</div>
                  <div style={{ color: "var(--ink-3)", fontSize: 12.5, marginTop: 3 }}>{a.reason}</div>
                </div>
              );
            })}
            <p className="footnote">
              The system is not saying the customer is wrong. It is saying no available record supports the
              claim, and policy does not permit anyone to assert a meter condition without a test or a
              diagnostic fault record.
            </p>
          </Card>
        </div>

        <div className="stack">
          <Card title="Evidence attached" sub={`${evidenceLedger.length} records, ${ALL_POLICIES.length} policies in the library`}>
            <table>
              <thead>
                <tr>
                  <th style={{ width: 104 }}>Evidence</th>
                  <th>Observation</th>
                </tr>
              </thead>
              <tbody>
                {evidenceLedger.map((e) => (
                  <tr key={e.evidence_id}>
                    <td className="mono">{e.evidence_id}</td>
                    <td>{e.observation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          <Card title="Route to a reviewer" sub="Four roles, because one queue is not an accountability model">
            <div className="row" style={{ flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
              {REVIEWERS.map((r) => (
                <button
                  key={r.id}
                  className={`seg${r.id === reviewer ? " on" : ""}`}
                  onClick={() => setReviewer(r.id)}
                >
                  {r.role}
                </button>
              ))}
            </div>
            <dl className="kv" style={{ gridTemplateColumns: "120px 1fr" }}>
              <dt>Owns</dt>
              <dd>{person.owns}</dd>
              <dt>Decides</dt>
              <dd>{person.decides}</dd>
              <dt>Recommended</dt>
              <dd>
                <Pill tone={isRecommended(person) ? "ok" : "muted"}>
                  {isRecommended(person) ? "matches routing recommendation" : "not the recommended route"}
                </Pill>
              </dd>
            </dl>
          </Card>

          <Card title="Record a decision" sub="Simulated, stored nowhere beyond this screen">
            <div className="stack" style={{ gap: 7 }}>
              {DECISIONS.map((d) => (
                <button
                  key={d.id}
                  className={`node${d.id === decision ? " control" : ""}`}
                  style={{ textAlign: "left", cursor: "pointer", font: "inherit", color: "inherit", width: "100%" }}
                  onClick={() => setDecision(d.id)}
                >
                  <span className="grow">
                    <span className="nm">{d.label}</span>
                  </span>
                  <Pill tone={d.tone}>{d.id}</Pill>
                </button>
              ))}
            </div>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Reviewer note, synthetic"
              rows={3}
              style={{
                width: "100%",
                marginTop: 12,
                background: "var(--surface-2)",
                border: "1px solid var(--line)",
                color: "var(--ink)",
                borderRadius: 8,
                padding: "9px 12px",
                font: "inherit",
                fontSize: 13,
                resize: "vertical",
              }}
            />
            {chosen && (
              <div className="banner warn" style={{ marginTop: 12 }}>
                <strong>SIMULATED DECISION, NOT APPLIED</strong>
                {chosen.effect} Recorded against {person.role} with note {note.trim() ? `"${note.trim()}"` : "(empty)"}.
                Nothing was sent, no workflow resumed, and no customer was contacted.
              </div>
            )}
          </Card>
        </div>
      </div>
    </>
  );
}
