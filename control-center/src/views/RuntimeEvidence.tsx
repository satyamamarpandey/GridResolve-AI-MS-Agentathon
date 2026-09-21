import { useState } from "react";
import { Card, ModeBanner, Pill, Stat } from "../components/ui";
import ContentLegend, { CONTENT_KINDS } from "../components/ContentLegend";
import { BILLED_STATUS } from "../data/foundryRuns";
import { RUNTIME_EVIDENCE, runLabel, type RuntimeRun } from "../data/runtimeEvidence";
import {
  AcceptanceCard,
  AuditCard,
  ComplianceCard,
  HumanReviewCard,
  LedgerCard,
  ReleaseCard,
  type RunCardProps,
} from "./RuntimeEvidenceCards";

const RUNS = RUNTIME_EVIDENCE.runs;
const KIND = CONTENT_KINDS[0].label;

const usd = (value: number): string => `$${value.toFixed(4)}`;
const count = (value: number): string => value.toLocaleString("en-US");

function IdentityCard({ run }: RunCardProps) {
  return (
    <Card title="Identity and timing" sub="From the response record and the evidence folder">
      <dl className="kv" style={{ marginTop: 10 }}>
        <dt>Response id</dt>
        <dd className="mono">{run.response_id}</dd>
        <dt>Evidence folder</dt>
        <dd className="mono">evidence/runtime/{run.evidence_folder}</dd>
        <dt>Case</dt>
        <dd className="mono">{run.case_id}, synthetic</dd>
        <dt>Workflow version</dt>
        <dd className="mono">v{run.workflow_version}, as the platform recorded it</dd>
        <dt>Started</dt>
        <dd className="mono">{run.started_at}</dd>
        <dt>Duration</dt>
        <dd className="mono">{run.elapsed_seconds.toFixed(1)} s</dd>
        <dt>Final status</dt>
        <dd className="mono">{run.final_status}</dd>
        <dt>Platform records</dt>
        <dd className="mono">
          {count(run.stream_events)} stream events, {run.conversation_items} conversation items
        </dd>
      </dl>
      <p className="footnote">
        "completed" means the HTTP execution finished. It says nothing about whether the agents did
        their work. That is what the other cards are for.
      </p>
    </Card>
  );
}

function AgentsCard({ run }: RunCardProps) {
  return (
    <Card
      title="Agents invoked"
      sub="In the order the platform ran them, with the version it recorded"
      right={
        <Pill tone={run.agents_healthy === run.agents_invoked ? "ok" : "bad"}>
          {run.agents_healthy} of {run.agents_invoked} did their work
        </Pill>
      }
    >
      <div className="tablewrap" style={{ marginTop: 10 }}>
        <table>
          <thead>
            <tr>
              <th>Agent</th>
              <th>Version</th>
              <th>Output</th>
              <th>Output health</th>
            </tr>
          </thead>
          <tbody>
            {run.agents.map((agent) => (
              <tr key={agent.agent}>
                <td>{agent.agent}</td>
                <td className="mono">{agent.version}</td>
                <td className="mono">{count(agent.output_chars)} chars</td>
                <td>
                  {agent.healthy ? (
                    <Pill tone="ok">USABLE</Pill>
                  ) : (
                    <>
                      <Pill tone="bad">NOT USABLE</Pill>
                      <div className="mono" style={{ color: "var(--ink-3)", marginTop: 3 }}>
                        {agent.problems.join(", ")}
                      </div>
                    </>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {run.agents_not_observed.length > 0 && (
        <p className="footnote">Not invoked in this run: {run.agents_not_observed.join(", ")}.</p>
      )}
    </Card>
  );
}

function TokensCard({ run }: RunCardProps) {
  const { usage } = run;
  const { pricing, totals } = RUNTIME_EVIDENCE;
  return (
    <Card title="Tokens and provisional cost" sub="From the usage block the platform returned">
      <dl className="kv" style={{ marginTop: 10 }}>
        <dt>Input tokens</dt>
        <dd className="mono">{count(usage.input_tokens)}</dd>
        <dt>Cached input tokens</dt>
        <dd className="mono">{count(usage.cached_input_tokens)}</dd>
        <dt>Output tokens</dt>
        <dd className="mono">
          {count(usage.output_tokens)}, of which {count(usage.reasoning_tokens)} reasoning
        </dd>
        <dt>Provisional cost</dt>
        <dd className="mono">{usd(run.provisional_usd)}</dd>
        <dt>All {totals.runs} runs</dt>
        <dd className="mono">
          {count(totals.input_tokens)} in, {count(totals.output_tokens)} out, {usd(totals.provisional_usd)}
        </dd>
        <dt>Billed amount</dt>
        <dd className="mono">{BILLED_STATUS}</dd>
      </dl>
      <p className="footnote">
        {pricing.basis} ${pricing.input_usd_per_million.toFixed(2)} per million input tokens and $
        {pricing.output_usd_per_million.toFixed(2)} per million output tokens. Azure Cost Management
        returned no rows when last queried, which is not a confirmed zero.
      </p>
    </Card>
  );
}

interface RunSelectorProps {
  readonly runs: readonly RuntimeRun[];
  readonly selected: number;
  readonly onSelect: (index: number) => void;
}

function RunSelector({ runs, selected, onSelect }: RunSelectorProps) {
  return (
    <div role="group" aria-label="Select a recorded run" style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
      {runs.map((run, index) => (
        <button
          key={run.evidence_folder}
          className={`btn ${index === selected ? "btn-primary" : "btn-secondary"}`}
          aria-pressed={index === selected}
          onClick={() => onSelect(index)}
        >
          {runLabel(run, runs)}, workflow v{run.workflow_version}
        </button>
      ))}
    </div>
  );
}

interface RuntimeEvidenceProps {
  /** Index of the run to open on. Defaults to the final run. */
  readonly initialRun?: number;
}

export default function RuntimeEvidence({ initialRun }: RuntimeEvidenceProps = {}) {
  const last = RUNS.length - 1;
  const start = initialRun !== undefined && initialRun >= 0 && initialRun <= last ? initialRun : last;
  const [selected, setSelected] = useState(start);
  const run = RUNS[selected];
  const isFinal = run.evidence_folder === RUNTIME_EVIDENCE.final_acceptance.evidence_folder;

  return (
    <>
      <div className="page-head">
        <h2>Runtime Evidence</h2>
        <p>
          The three times the hosted workflow really ran, read from the records Microsoft Foundry
          returned. Two runs show defects and one passed. All three are kept, because the defects are
          how the final version came about.
        </p>
      </div>

      <ModeBanner label={KIND} detail="Recorded platform evidence, this application did not run it. Nothing on this page is computed by the offline engine." />

      <RunSelector runs={RUNS} selected={selected} onSelect={setSelected} />

      <div className="grid g4" style={{ marginBottom: 14 }}>
        <Stat label={runLabel(run)} value={`v${run.workflow_version}`} meta={run.started_at} mono />
        <Stat
          label="Agents that did their work"
          value={`${run.agents_healthy} of ${run.agents_invoked}`}
          tone={run.agents_healthy === run.agents_invoked ? "ok" : "bad"}
          mono
        />
        <Stat
          label="Compliance token"
          value={run.compliance.token}
          tone={run.compliance.token === "APPROVED" ? "ok" : "warn"}
          meta={run.route.observed}
          mono
        />
        <Stat label="Provisional cost" value={usd(run.provisional_usd)} meta={`Billed amount: ${BILLED_STATUS}`} mono />
      </div>

      <div className="grid g2">
        <IdentityCard run={run} />
        <TokensCard run={run} />
      </div>

      <div style={{ marginTop: 14 }}>
        <AgentsCard run={run} />
      </div>

      <div className="grid g2" style={{ marginTop: 14 }}>
        <LedgerCard run={run} />
        <ComplianceCard run={run} />
      </div>

      <div className="grid g2" style={{ marginTop: 14 }}>
        <ReleaseCard run={run} />
        <HumanReviewCard run={run} />
      </div>

      <div className="grid g2" style={{ marginTop: 14 }}>
        <AuditCard run={run} />
        {isFinal ? <AcceptanceCard acceptance={RUNTIME_EVIDENCE.final_acceptance} /> : <ContentLegend current={KIND} />}
      </div>

      {isFinal && (
        <div style={{ marginTop: 14 }}>
          <ContentLegend current={KIND} />
        </div>
      )}

      <p className="footnote">
        Built from evidence/runtime by {RUNTIME_EVIDENCE.generated_by}. One synthetic case. These runs
        show what the hosted workflow did on that case, not how it would behave in operation.
      </p>
    </>
  );
}
