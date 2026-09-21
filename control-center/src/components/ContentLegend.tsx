import { Card, Pill, type Tone } from "./ui";
import { MODE_LABEL } from "../engine/investigation";

export interface ContentKind {
  readonly label: string;
  readonly tone: Tone;
  readonly meaning: string;
}

/** The four kinds of content in this application. A page shows its own kind in its banner. */
export const CONTENT_KINDS: readonly ContentKind[] = [
  {
    label: "ACTUAL FOUNDRY EXECUTION",
    tone: "ok",
    meaning: "Recorded by Microsoft Foundry during one of the three real runs. Shown on Runtime Evidence.",
  },
  {
    label: MODE_LABEL,
    tone: "info",
    meaning: "Computed in this browser by fixed rules from synthetic records. No model is called.",
  },
  {
    label: "PREPARED EVALUATION",
    tone: "violet",
    meaning: "Cases and checks that are written down and not executed. No score exists for them.",
  },
  {
    label: "FUTURE PRODUCTION INTEGRATION",
    tone: "muted",
    meaning: "Connections to real utility systems. Planned, not live.",
  },
];

interface ContentLegendProps {
  readonly current?: string;
}

export default function ContentLegend({ current }: ContentLegendProps) {
  return (
    <Card title="How to read this application" sub="Four kinds of content, never mixed on one page">
      <dl className="kv" style={{ gridTemplateColumns: "minmax(230px, max-content) 1fr", marginTop: 10 }}>
        {CONTENT_KINDS.map((kind) => (
          <div key={kind.label} style={{ display: "contents" }}>
            <dt>
              <Pill tone={kind.tone}>{kind.label}</Pill>
            </dt>
            <dd>
              {kind.meaning}
              {kind.label === current ? " This page." : ""}
            </dd>
          </div>
        ))}
      </dl>
    </Card>
  );
}
