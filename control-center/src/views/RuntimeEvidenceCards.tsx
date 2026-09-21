import { Card, Pill, type Tone } from "../components/ui";
import type { RuntimeAcceptance, RuntimeLedger, RuntimeRun } from "../data/runtimeEvidence";

export interface RunCardProps {
  readonly run: RuntimeRun;
}

const yesNo = (value: boolean | null): string => (value === null ? "not stated" : value ? "yes" : "no");

const tokenTone = (token: string): Tone => (token === "APPROVED" ? "ok" : token === "ESCALATE" ? "warn" : "bad");

interface FindingListProps {
  readonly items: readonly string[];
}

function FindingList({ items }: FindingListProps) {
  return (
    <ul style={{ margin: "10px 0 0", paddingLeft: 18, fontSize: 13, lineHeight: 1.5 }}>
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

interface LedgerRowProps {
  readonly name: string;
  readonly unit: string;
  readonly ledger: RuntimeLedger;
}

function LedgerRow({ name, unit, ledger }: LedgerRowProps) {
  return (
    <>
      <dt>{name}</dt>
      <dd>
        <Pill tone={ledger.status === "PRODUCED" ? "ok" : "bad"}>{ledger.status}</Pill>{" "}
        <span className="mono">
          {ledger.count} {unit}
        </span>
        {ledger.problems.length > 0 && (
          <div className="mono" style={{ color: "var(--ink-3)", marginTop: 4 }}>
            {ledger.problems.join(", ")}
          </div>
        )}
      </dd>
    </>
  );
}

export function LedgerCard({ run }: RunCardProps) {
  return (
    <Card title="Evidence ledger and policy mapping" sub="Whether the two investigation records were produced">
      <dl className="kv" style={{ marginTop: 10 }}>
        <LedgerRow name="Evidence ledger" unit="entries" ledger={run.evidence_ledger} />
        <LedgerRow name="Policy mapping" unit="policies" ledger={run.policy_mapping} />
        <dt>Investigation complete</dt>
        <dd>{yesNo(run.investigation_complete)}</dd>
      </dl>
      <p className="footnote">
        Counts are taken from the agents' recorded outputs. A record that was not produced shows the
        reasons the runner found in that output.
      </p>
    </Card>
  );
}

export function ComplianceCard({ run }: RunCardProps) {
  const c = run.compliance;
  return (
    <Card
      title="Compliance decision and route"
      sub="The decision is the model's. The route is what the platform then did"
      right={<Pill tone={tokenTone(c.token)}>{c.token}</Pill>}
    >
      <dl className="kv" style={{ marginTop: 10 }}>
        <dt>Decision object</dt>
        <dd>{c.decision ? <Pill tone="info">{c.decision}</Pill> : <Pill tone="bad">NONE RETURNED</Pill>}</dd>
        <dt>Route token line</dt>
        <dd className="mono">{c.final_line}</dd>
        <dt>Failed checks</dt>
        <dd className="mono">{c.failed_checks === null ? "not stated" : c.failed_checks}</dd>
        <dt>Human review required</dt>
        <dd>{yesNo(c.human_review_required)}</dd>
        <dt>Route observed</dt>
        <dd>
          <Pill tone={run.route.observed === "APPROVED_AND_RELEASED" ? "ok" : "warn"}>{run.route.observed}</Pill>
        </dd>
        <dt>Release gate evaluated</dt>
        <dd>{yesNo(run.route.gate_evaluated)}</dd>
      </dl>
      {c.reasons_given ? (
        <>
          <FindingList items={c.summary_sentences} />
          {c.summary_sentences_omitted > 0 && (
            <p className="footnote">
              Verbatim sentences from the model's summary. Sentences left out because they contain a
              typographic dash: {c.summary_sentences_omitted}. The full text is in 07_conversation_items.json.
            </p>
          )}
          {c.evidence_ids_cited.length > 0 && (
            <p className="footnote mono">
              Cites {c.evidence_ids_cited.length} evidence ids and {c.policy_ids_cited.length} policy ids:{" "}
              {[...c.evidence_ids_cited, ...c.policy_ids_cited].join(", ")}
            </p>
          )}
        </>
      ) : (
        <p className="footnote">
          Compliance returned only its route token and gave no reasons, so why it chose this route is
          not established.
        </p>
      )}
    </Card>
  );
}

export function ReleaseCard({ run }: RunCardProps) {
  const r = run.release;
  const delivered = r.outcome === "DELIVERED_CUSTOMER_MESSAGE";
  const defect = r.outcome === "UNEVALUATED_EXPRESSION";
  return (
    <Card
      title="Sent to the customer"
      sub="The workflow-authored message, exactly as the platform recorded it"
      right={<Pill tone={delivered ? "ok" : defect ? "bad" : "warn"}>{defect ? "DEFECT" : r.outcome}</Pill>}
    >
      {r.text ? (
        <div
          style={{
            whiteSpace: "pre-wrap",
            marginTop: 10,
            padding: "12px 14px",
            border: "1px solid var(--color-divider)",
            fontFamily: defect ? "var(--mono)" : undefined,
            fontSize: 13,
            lineHeight: 1.55,
            maxHeight: 420,
            overflowY: "auto",
          }}
        >
          {r.text}
        </div>
      ) : (
        <p className="card-body" style={{ marginTop: 10 }}>
          Nothing was sent to the customer. The workflow withheld the draft and handed the case to a person.
        </p>
      )}
      <p className="footnote">
        {delivered &&
          `${r.released_chars} characters. ${
            r.equals_composed_draft
              ? "Identical to the six readable parts of the communication agent's draft, joined by the release template."
              : "It differs from the communication agent's draft."
          }`}
        {defect &&
          `${r.released_chars} characters. The release step sent the workflow expression itself, not the message it should have produced. Release outcome: ${r.outcome}.`}
        {!r.text && "The fail-closed route, observed on the hosted platform."}
      </p>
    </Card>
  );
}

export function HumanReviewCard({ run }: RunCardProps) {
  const h = run.human_review;
  const card = h.decision_card;
  return (
    <Card
      title="Human review disposition"
      sub="Whether the open case reached a person, separately from the message"
      right={<Pill tone={h.follow_up_observed === "HANDED_TO_HUMAN" ? "ok" : "bad"}>{h.follow_up_observed}</Pill>}
    >
      <dl className="kv" style={{ marginTop: 10 }}>
        <dt>Planner follow-up token</dt>
        <dd className="mono">{h.planner_token}</dd>
        <dt>Follow-up gate evaluated</dt>
        <dd>{yesNo(h.follow_up_gate_evaluated)}</dd>
        <dt>Escalation package</dt>
        <dd>{h.package_produced ? "produced" : "not produced, the escalation agent was not invoked"}</dd>
        {h.package_produced && (
          <>
            <dt>Recommended reviewer</dt>
            <dd>{h.recommended_reviewer ?? "not stated"}</dd>
            <dt>Routed to</dt>
            <dd>
              {h.routing_target ?? "not stated"}
              {h.routing_fallback ? `, fallback ${h.routing_fallback}` : ""}
            </dd>
            <dt>Disposition</dt>
            <dd className="mono">{h.disposition ?? "not stated"}</dd>
            <dt>Case state</dt>
            <dd className="mono">{h.case_state ?? "not stated"}</dd>
          </>
        )}
        {card && (
          <>
            <dt>Decision card</dt>
            <dd>
              {card.parts} parts, {card.known_facts} known facts, {card.unknowns} unknowns,{" "}
              {card.applicable_policies} applicable policies
            </dd>
          </>
        )}
      </dl>
      {h.findings.length > 0 && <FindingList items={h.findings} />}
      <p className="footnote">
        Reviewers are roles, not people. No notification system is connected, so no person was contacted.
        The card's prose is in the evidence file.
      </p>
    </Card>
  );
}

export function AuditCard({ run }: RunCardProps) {
  const a = run.audit;
  return (
    <Card
      title="Audit findings"
      sub="The audit agent's record, checked against the platform record by the runner"
      right={<Pill tone={a.accurate ? "ok" : "bad"}>{a.accurate ? "AUDIT ACCURATE" : "AUDIT INACCURATE"}</Pill>}
    >
      <p className="card-body mono" style={{ marginTop: 10 }}>
        {a.findings.length} findings
      </p>
      {a.findings.length > 0 && <FindingList items={a.findings} />}
      <p className="footnote">
        A finding is a place where the model's audit disagrees with what the platform recorded. A model's
        audit of its own run is a claim, so it is checked.
      </p>
    </Card>
  );
}

interface AcceptanceCardProps {
  readonly acceptance: RuntimeAcceptance;
}

export function AcceptanceCard({ acceptance }: AcceptanceCardProps) {
  return (
    <Card
      title="Acceptance result"
      sub="Criteria written down before the run, graded afterwards from the raw evidence"
      right={
        <Pill tone={acceptance.passed === acceptance.criteria ? "ok" : "bad"}>
          {acceptance.passed} of {acceptance.criteria} PASS
        </Pill>
      }
    >
      <div className="tablewrap" style={{ marginTop: 10 }}>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Criterion</th>
              <th>Verdict</th>
            </tr>
          </thead>
          <tbody>
            {acceptance.items.map((item) => (
              <tr key={item.number}>
                <td className="mono">{item.number}</td>
                <td>{item.title}</td>
                <td>
                  <Pill tone={item.verdict === "PASS" ? "ok" : item.verdict === "FAIL" ? "bad" : "muted"}>
                    {item.verdict}
                  </Pill>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="footnote">
        {acceptance.failed} failed, {acceptance.not_observable} not observable. Plan: {acceptance.plan}.
        Result: {acceptance.result}. One run of one synthetic case is one sample. The escalate branch
        was not taken in this run, so it was not graded here.
      </p>
    </Card>
  );
}
