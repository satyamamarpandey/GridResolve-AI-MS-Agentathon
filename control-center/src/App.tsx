import { useState, type ReactElement } from "react";
import Overview from "./views/Overview";
import BillingInvestigation from "./views/BillingInvestigation";
import EvidenceExplorer from "./views/EvidenceExplorer";
import AgentWorkflow from "./views/AgentWorkflow";
import CustomerAssistant from "./views/CustomerAssistant";
import SupervisorReview from "./views/SupervisorReview";
import Governance from "./views/Governance";
import Evaluations from "./views/Evaluations";
import SystemStatus from "./views/SystemStatus";
import FixtureCase from "./views/FixtureCase";
import RuntimeEvidence from "./views/RuntimeEvidence";
import { WORKFLOW_VERSION, caseInput } from "./engine/investigation";

interface NavItem {
  readonly id: string;
  readonly label: string;
  readonly hint: string;
  readonly icon: ReactElement;
  readonly view: () => ReactElement;
  /** Shown beside the case id. Defaults to the offline label. */
  readonly chip?: string;
}

interface NavGroup {
  readonly group: string;
  readonly items: readonly NavItem[];
}

/** Lucide-style inline SVG on currentColor, as the design system specifies. */
const icon = (paths: ReactElement) => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {paths}
  </svg>
);

const NAV: readonly NavGroup[] = [
  {
    group: "Overview",
    items: [
      {
        id: "overview",
        label: "Dashboard",
        hint: "The case and the verdict",
        icon: icon(<><rect x="3" y="3" width="7" height="7" /><rect x="14" y="3" width="7" height="7" /><rect x="3" y="14" width="7" height="7" /><rect x="14" y="14" width="7" height="7" /></>),
        view: Overview,
      },
    ],
  },
  {
    group: "Real Foundry runs",
    items: [
      {
        id: "runtime",
        label: "Runtime Evidence",
        hint: "Three recorded executions",
        icon: icon(<><path d="M4 4h16v6H4z" /><path d="M4 14h16v6H4z" /><path d="M8 7h.01M8 17h.01" /></>),
        view: RuntimeEvidence,
        chip: "Recorded Foundry runs",
      },
    ],
  },
  {
    group: "Operations",
    items: [
      {
        id: "billing",
        label: "Billing Investigation",
        hint: "Deterministic arithmetic",
        icon: icon(<><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><path d="M14 2v6h6" /><path d="M8 13h8M8 17h5" /></>),
        view: BillingInvestigation,
      },
      {
        id: "workflow",
        label: "Agent Workflow",
        hint: "Deployed orchestration",
        icon: icon(<><circle cx="18" cy="5" r="3" /><circle cx="6" cy="12" r="3" /><circle cx="18" cy="19" r="3" /><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4" /></>),
        view: AgentWorkflow,
      },
    ],
  },
  {
    group: "Intelligence",
    items: [
      {
        id: "evidence",
        label: "Evidence Explorer",
        hint: "Claim provenance",
        icon: icon(<><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></>),
        view: EvidenceExplorer,
      },
      {
        id: "assistant",
        label: "Customer Assistant",
        hint: "Offline conversation",
        icon: icon(<><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" /></>),
        view: CustomerAssistant,
      },
    ],
  },
  {
    group: "Governance",
    items: [
      {
        id: "supervisor",
        label: "Supervisor Review",
        hint: "Human decision point",
        icon: icon(<><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M19 8v6M22 11h-6" /></>),
        view: SupervisorReview,
      },
      {
        id: "governance",
        label: "Governance",
        hint: "Twelve named controls",
        icon: icon(<><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" /></>),
        view: Governance,
      },
      {
        id: "evaluations",
        label: "Evaluations",
        hint: "Run versus prepared",
        icon: icon(<><rect x="3" y="3" width="18" height="18" rx="1" /><path d="M9 9h6M9 13h6M9 17h3" /></>),
        view: Evaluations,
      },
    ],
  },
  {
    group: "System",
    items: [
      {
        id: "status",
        label: "System Status",
        hint: "Resources and cost",
        icon: icon(<><path d="M3 12h4l3 8 4-16 3 8h4" /></>),
        view: SystemStatus,
      },
      {
        id: "fixture",
        label: "UI Test Fixture",
        hint: "Simulated, not executed",
        icon: icon(<><path d="M9 3v6l-5 9a2 2 0 0 0 2 3h12a2 2 0 0 0 2-3l-5-9V3" /><path d="M8 3h8M7 15h10" /></>),
        view: FixtureCase,
      },
    ],
  },
];

const ALL = NAV.flatMap((g) => g.items);

export default function App() {
  const [active, setActive] = useState(ALL[0].id);
  const [collapsed, setCollapsed] = useState(false);
  const current = ALL.find((n) => n.id === active) ?? ALL[0];
  const group = NAV.find((g) => g.items.some((i) => i.id === current.id))!;
  const View = current.view;

  return (
    <div className={`app${collapsed ? " collapsed" : ""}`}>
      <nav className="sidebar">
        <div className="brand">
          <svg width="26" height="26" viewBox="0 0 32 32" aria-hidden="true">
            <polygon points="16,3 28,10 28,22 16,29 4,22 4,10" fill="none" stroke="var(--color-accent)" strokeWidth="1.6" />
            <circle cx="16" cy="16" r="4" fill="none" stroke="var(--color-accent)" strokeWidth="1.6" />
          </svg>
          <div>
            <h1>GridResolve AI</h1>
            <span>Control Center</span>
          </div>
        </div>

        <div className="navscroll">
          {NAV.map((g) => (
            <div key={g.group} className="navgroup">
              <div className="navgroup-label">{g.group}</div>
              {g.items.map((item) => (
                <button
                  key={item.id}
                  className={`navbtn${item.id === active ? " on" : ""}`}
                  onClick={() => setActive(item.id)}
                  aria-current={item.id === active ? "page" : undefined}
                  title={item.label}
                >
                  <span className="ico">{item.icon}</span>
                  <span className="grow">
                    <strong>{item.label}</strong>
                    <em>{item.hint}</em>
                  </span>
                </button>
              ))}
            </div>
          ))}
        </div>

        <div className="sidefoot">
          <div className="mono">{WORKFLOW_VERSION}</div>
          <div>Synthetic data only. This application calls no model. Three real Foundry runs are recorded under Runtime Evidence.</div>
          <button className="btn btn-secondary btn-icon collapse" onClick={() => setCollapsed((c) => !c)} title="Collapse navigation">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d={collapsed ? "M9 18l6-6-6-6" : "M15 18l-6-6 6-6"} />
            </svg>
          </button>
        </div>
      </nav>

      <div className="content">
        <header className="topbar">
          <div>
            <div className="crumb">Control Center / {current.label}</div>
            <div className="topbar-title">{current.label}</div>
          </div>
          <div className="topbar-right">
            <span className="tag tag-outline casechip">
              {caseInput.case_id} &middot; {current.chip ?? "Local deterministic"}
            </span>
            <button className="btn btn-secondary btn-icon" title="Search" aria-label="Search">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                <circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" />
              </svg>
            </button>
            <button className="btn btn-secondary btn-icon bell" title="Notifications" aria-label="Notifications">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
                <path d="M18 8a6 6 0 1 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" /><path d="M13.7 21a2 2 0 0 1-3.4 0" />
              </svg>
              <span className="dotmark" />
            </button>
            <span className="buildtag">Agent-a-thon build</span>
          </div>
        </header>

        <main className="main" data-group={group.group}>
          <View />
        </main>
      </div>
    </div>
  );
}
