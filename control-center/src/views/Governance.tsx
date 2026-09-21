import { Card, ModeBanner, Pill, statusTone } from "../components/ui";
import { ALL_POLICIES, WORKFLOW_VERSION, projectedCost } from "../engine/investigation";
import redTeamPack from "../data/generated/redTeamPack.json";

type Status =
  | "CONFIGURED"
  | "STATICALLY_VALIDATED"
  // One half of the control is validated locally and the other half is not.
  // Claiming the stronger label for the whole control would overstate it.
  | "PARTIALLY_VALIDATED"
  | "RUNTIME_PROVEN"
  | "PREPARED_ONLY"
  | "PRODUCTION_TARGET";

interface Control {
  readonly id: string;
  readonly name: string;
  readonly status: Status;
  readonly mechanism: string;
  readonly proof: string;
}

/**
 * Twelve named controls. The status vocabulary is deliberately narrow, and nothing
 * is labelled RUNTIME_PROVEN: one real run of one synthetic case does not prove a control.
 */
const CONTROLS: readonly Control[] = [
  {
    id: "G01",
    name: "Evidence-bound claims",
    status: "STATICALLY_VALIDATED",
    mechanism: "validate_claim_ledger resolves every claim against evidence and policy identifiers",
    proof: "37 local tool tests, including unresolvable and empty citation cases",
  },
  {
    id: "G02",
    name: "Fail-closed compliance routing",
    status: "STATICALLY_VALIDATED",
    mechanism: `ConditionGroup requires an exact route token, escalation is the default branch in ${WORKFLOW_VERSION}`,
    proof: "72 routing tests reproducing Power Fx case-insensitive substring semantics",
  },
  {
    id: "G03",
    name: "Draft withheld until approved",
    status: "STATICALLY_VALIDATED",
    mechanism: "Seven investigating agents run with autoSend false, so no intermediate output reaches the customer",
    proof: "33 live read-only configuration checks against the deployed workflow definition",
  },
  {
    id: "G04",
    name: "Mandatory human escalation",
    status: "CONFIGURED",
    mechanism: "EscalationCoordinatorAgent on the default branch, POL-HUM-005 requires a named reviewer",
    proof: "Agent and branch present in the deployed definition, never executed",
  },
  {
    id: "G05",
    name: "Terminal audit record",
    status: "CONFIGURED",
    mechanism: "CaseAuditAgent runs on both branches, build_audit_packet assembles the packet",
    proof: "Audit node present after the condition group on both paths",
  },
  {
    id: "G06",
    name: "Deterministic financial arithmetic",
    status: "STATICALLY_VALIDATED",
    mechanism: "Bill, usage and rate decomposition computed by pure functions, not by a model",
    proof: "Decomposition reconciles exactly with the observed bill difference in tests",
  },
  {
    id: "G07",
    name: "Synthetic data only",
    status: "STATICALLY_VALIDATED",
    mechanism: "Case identifiers constrained to the SYN-CASE pattern, memory refuses any other identifier",
    proof: "Memory isolation tests reject a non synthetic case id",
  },
  {
    id: "G08",
    name: "Prompt injection resistance",
    // Two different things are true here and the distinction is the point.
    // The offline responder is tested. The Foundry agents are not.
    status: "PARTIALLY_VALIDATED",
    mechanism: `POL-SEC-008, ${redTeamPack.attacks.length} adversarial probes authored covering ${new Set(redTeamPack.attacks.map((a) => a.attack_class)).size} attack classes, plus layered refusal in the offline responder`,
    proof:
      "The offline responder is validated by 11 local tests over a 14 input battery: no phrasing produces an unnegated meter fault claim, and an injection string outside the detection list still fails closed through the meter rule. The probe pack has never been executed against the Foundry agents.",
  },
  {
    id: "G09",
    name: "Cost governance",
    status: "STATICALLY_VALIDATED",
    mechanism: "POL-COST-009, token budget priced from the published Azure retail rate before any run",
    proof: `Projected cost for one synthetic case is $${projectedCost.totalUsd.toFixed(4)}, computed locally`,
  },
  {
    id: "G10",
    name: "Case memory isolation",
    status: "STATICALLY_VALIDATED",
    mechanism: "Per case namespaced browser storage with a key to payload consistency guard",
    proof: "Cross case leakage test asserts neither record contains the other's text",
  },
  {
    id: "G11",
    name: "Model-graded evaluation",
    status: "PREPARED_ONLY",
    mechanism: "Thirty case suite with a weighted rubric, awaiting explicit spend authorization",
    proof: "Suite authored and validated for structure. No evaluator has been run.",
  },
  {
    id: "G12",
    name: "Runtime telemetry and tracing",
    status: "PRODUCTION_TARGET",
    mechanism: "Foundry sends spans to the Application Insights resource created with the project. No alerting, dashboard or content policy is built on it",
    proof: "61 platform spans for the three real runs, read back on 2026-09-21. Token totals match my runner exactly. Summary in evidence/platform_telemetry",
  },
];

const TONE: Record<Status, "ok" | "warn" | "bad" | "info" | "muted" | "violet"> = {
  CONFIGURED: "violet",
  STATICALLY_VALIDATED: "info",
  PARTIALLY_VALIDATED: "warn",
  RUNTIME_PROVEN: "ok",
  PREPARED_ONLY: "warn",
  PRODUCTION_TARGET: "muted",
};

const counts = CONTROLS.reduce<Record<string, number>>((acc, c) => {
  acc[c.status] = (acc[c.status] ?? 0) + 1;
  return acc;
}, {});

export default function Governance() {
  return (
    <>
      <div className="page-head">
        <h2>Governance</h2>
        <p>
          Twelve named controls with honest status labels. The workflow has now run for real three times, and
          the final run passed 14 of 14 acceptance criteria. Nothing on this page is marked RUNTIME_PROVEN
          all the same, because one run of one synthetic case demonstrates a control once. It does not prove
          it.
        </p>
      </div>

      <ModeBanner
        label="STATUS VOCABULARY IS ENFORCED"
        detail="CONFIGURED means deployed and readable. STATICALLY_VALIDATED means proven by local tests without a model call. PREPARED_ONLY means authored and awaiting authorization. PRODUCTION_TARGET means designed but deliberately not built."
      />

      <div className="grid g4" style={{ marginBottom: 14 }}>
        {(["STATICALLY_VALIDATED", "CONFIGURED", "PREPARED_ONLY", "PRODUCTION_TARGET"] as const).map((s) => (
          <div key={s} className="card stat">
            <div className="label">{s.replace(/_/g, " ").toLowerCase()}</div>
            <div className="value mono">{counts[s] ?? 0}</div>
            <div className="meta">of {CONTROLS.length} controls</div>
          </div>
        ))}
      </div>

      <Card title="Control register" sub="Mechanism and the evidence behind each status">
        <table>
          <thead>
            <tr>
              <th style={{ width: 44 }}>ID</th>
              <th style={{ width: 210 }}>Control</th>
              <th style={{ width: 176 }}>Status</th>
              <th>Mechanism</th>
              <th style={{ width: 300 }}>Proof</th>
            </tr>
          </thead>
          <tbody>
            {CONTROLS.map((c) => (
              <tr key={c.id}>
                <td className="mono">{c.id}</td>
                <td><strong>{c.name}</strong></td>
                <td><Pill tone={TONE[c.status]}>{c.status}</Pill></td>
                <td>{c.mechanism}</td>
                <td style={{ color: "var(--ink-3)", fontSize: 12.5 }}>{c.proof}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <div className="grid g2" style={{ marginTop: 14 }}>
        <Card title="Policy library" sub={`${ALL_POLICIES.length} synthetic policies, versioned`}>
          <table>
            <thead>
              <tr>
                <th style={{ width: 132 }}>Policy</th>
                <th>Title</th>
                <th style={{ width: 132 }}>Human approval</th>
              </tr>
            </thead>
            <tbody>
              {ALL_POLICIES.map((p) => (
                <tr key={p.policy_id}>
                  <td className="mono">{p.policy_id}</td>
                  <td>
                    {p.title}
                    <div style={{ color: "var(--ink-3)", fontSize: 12, marginTop: 2 }}>{p.purpose}</div>
                  </td>
                  <td>
                    <Pill tone={p.human_approval_requirement ? "warn" : "muted"}>
                      {p.human_approval_requirement ? "required" : "not required"}
                    </Pill>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>

        <div className="stack">
          <Card title="Adversarial pack" sub={`${redTeamPack.attacks.length} probes, ${redTeamPack.meta.status.replace(/_/g, " ").toLowerCase()}`}>
            <table>
              <thead>
                <tr>
                  <th style={{ width: 62 }}>ID</th>
                  <th>Attack class</th>
                  <th style={{ width: 160 }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {redTeamPack.attacks.map((a) => (
                  <tr key={a.attack_id}>
                    <td className="mono">{a.attack_id}</td>
                    <td>{a.attack_class}</td>
                    <td><Pill tone={statusTone(a.status)}>{a.status}</Pill></td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="footnote">
              Every probe is written against a fail condition, so a run would produce a pass or fail rather
              than an impression. Executing the pack requires explicit authorization because it spends tokens.
            </p>
          </Card>

          <Card title="Deliberate non-actions" sub="Recorded because restraint is part of the design">
            <ul className="bullets">
              <li>I added no telemetry resource. The Application Insights resource that came with the project holds about 2.5 MB from the three runs.</li>
              <li>No API Management gateway was created, because the cost could not be verified in advance.</li>
              <li>No Azure AI Search or managed memory store was provisioned.</li>
              <li>The model was called in three approved runs only, 26 requests, about $0.13 provisional. Nothing in this application calls a model.</li>
              <li>Correction and replan loops were left unwired rather than described as working.</li>
            </ul>
          </Card>
        </div>
      </div>
    </>
  );
}
