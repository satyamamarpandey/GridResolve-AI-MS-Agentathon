import { Card, ModeBanner, Pill, Stat } from "../components/ui";
import { RECORDS, RULES, SIMULATED_EXAMPLE, overrideRate, reviewTimeReduction } from "../engine/supervisorFeedback";

/**
 * Supervisor feedback loop view. Everything shown is an OFFLINE_SIMULATION from
 * engine/supervisorFeedback.ts. No human review has been recorded. No network, no model.
 */

export default function SupervisorFeedback() {
  const rate = overrideRate(RECORDS);
  const reduction = reviewTimeReduction(RECORDS);
  const notMeasured = "rate" in rate ? null : rate;
  const simulated = RECORDS.filter((r) => r.record_kind === "OFFLINE_SIMULATION").length;
  const actual = RECORDS.length - simulated;

  return (
    <>
      <div className="page-head">
        <h2>Supervisor Feedback</h2>
        <p>
          The record a human reviewer leaves behind after an escalation: what the agents recommended, what the
          person decided, whether the two agreed, how long the review took, and why any override happened. This
          is the loop the external review asked for. It is implemented and tested locally. It has not been used.
        </p>
      </div>

      <ModeBanner
        label="OFFLINE_SIMULATION ONLY, NO ACTUAL HUMAN REVIEW RECORDED"
        detail="Every record on this screen is a hand-written fixture. No supervisor has reviewed a GridResolve case. No override rate and no review-time reduction can be reported until actual eligible human decisions exist."
      />

      <div className="grid stats" style={{ gridTemplateColumns: "repeat(4, minmax(0, 1fr))", gap: 14 }}>
        <Stat label="Actual human reviews" value={actual} tone="muted" meta="ACTUAL_HUMAN_REVIEW records" />
        <Stat label="Simulated records" value={simulated} tone="info" meta="OFFLINE_SIMULATION records, excluded from every rate" />
        <Stat label="Supervisor override rate" value="Not measured" tone="warn" meta={notMeasured ? notMeasured.reason : "measured"} />
        <Stat label="Review-time reduction" value="Not measured" tone="warn" meta={reduction.reason} />
      </div>

      <div className="grid" style={{ gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr)", gap: 14, marginTop: 14 }}>
        <div className="stack">
          <Card title="Simulated example record" right={<Pill tone="violet">{SIMULATED_EXAMPLE.record_kind}</Pill>}>
            <dl className="kv">
              <dt>Case ID</dt>
              <dd className="mono">{SIMULATED_EXAMPLE.case_id}</dd>
              <dt>Evidence package</dt>
              <dd>{SIMULATED_EXAMPLE.evidence_package_ref}</dd>
              <dt>Agent recommendation</dt>
              <dd className="mono">{SIMULATED_EXAMPLE.agent_recommendation}</dd>
              <dt>Human decision</dt>
              <dd className="mono">{SIMULATED_EXAMPLE.human_decision}</dd>
              <dt>Agreement</dt>
              <dd><Pill tone={SIMULATED_EXAMPLE.agreement === "AGREE" ? "ok" : "bad"}>{SIMULATED_EXAMPLE.agreement}</Pill></dd>
              <dt>Review started</dt>
              <dd className="mono">{SIMULATED_EXAMPLE.review_started_at}</dd>
              <dt>Review completed</dt>
              <dd className="mono">{SIMULATED_EXAMPLE.review_completed_at}</dd>
              <dt>Duration</dt>
              <dd>{SIMULATED_EXAMPLE.review_duration_seconds} s, {SIMULATED_EXAMPLE.duration_note}</dd>
              <dt>Override reason</dt>
              <dd>{SIMULATED_EXAMPLE.override_reason || "none, the decision agreed"}</dd>
              <dt>Reviewer</dt>
              <dd className="mono">{SIMULATED_EXAMPLE.reviewer_principal_id} ({SIMULATED_EXAMPLE.reviewer_role})</dd>
              <dt>Final disposition</dt>
              <dd className="mono">{SIMULATED_EXAMPLE.final_disposition}</dd>
              <dt>Record kind</dt>
              <dd><Pill tone="violet">{SIMULATED_EXAMPLE.record_kind}</Pill></dd>
            </dl>
            <p className="footnote" style={{ marginBottom: 0 }}>Reviewer comments: {SIMULATED_EXAMPLE.reviewer_comments}</p>
          </Card>
        </div>

        <div className="stack">
          <Card title="Rules the local tests prove" sub="integration/supervisor_feedback.py, tests/test_supervisor_feedback.py">
            <ul className="bullets">
              {RULES.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </Card>

          <Card title="Metrics" sub="Reported only when the evidence to report them exists">
            <dl className="kv">
              <dt>Supervisor override rate</dt>
              <dd>
                <Pill tone="warn">Not measured</Pill> {notMeasured ? notMeasured.reason : ""}
              </dd>
              <dt>Review-time reduction</dt>
              <dd>
                <Pill tone="warn">Not measured</Pill> {reduction.reason}
              </dd>
            </dl>
            <p className="footnote" style={{ marginBottom: 0 }}>
              A rate would count overrides over actual human decisions only. A reduction would compare the measured
              mean of actual reviews with a baseline that carries its source, measurement date and sample size.
            </p>
          </Card>
        </div>
      </div>
    </>
  );
}
