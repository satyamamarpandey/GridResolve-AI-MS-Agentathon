import type { ReactNode } from "react";

export type Tone = "ok" | "warn" | "bad" | "info" | "muted" | "violet";

/** Design-system tag. Tones map onto the system's tag variants plus status tints. */
export const Pill = ({ tone = "muted", children }: { tone?: Tone; children: ReactNode }) => (
  <span className={`tag tag-${tone}`}>{children}</span>
);

/** Blueprint registration marks. The design system draws these at card corners. */
export const Corners = () => (
  <>
    <span className="corner tl" />
    <span className="corner tr" />
    <span className="corner bl" />
    <span className="corner br" />
  </>
);

/** Maps the project status vocabulary to a consistent colour everywhere. */
export const statusTone = (s: string): Tone =>
  s === "RUNTIME_PROVEN" || s === "SUPPORTED" || s === "COMPLETE"
    ? "ok"
    : s === "STATICALLY_VALIDATED"
      ? "info"
      : // Partial validation reads as warn rather than info, so a control that is
        // only half proven is not mistaken at a glance for one that is fully proven.
        s === "PARTIALLY_VALIDATED" || s === "PARTIALLY_SUPPORTED"
        ? "warn"
      : s === "UNSUPPORTED" || s === "HUMAN_REVIEW_REQUIRED" || s === "INCOMPLETE"
        ? "bad"
        : s === "CONFIGURED"
          ? "violet"
          : "muted";

export const Card = ({
  title,
  sub,
  right,
  children,
  className = "",
}: {
  title?: string;
  sub?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
}) => (
  <section className={`card blueprint elev-sm ${className}`}>
    <Corners />
    {(title || right) && (
      <div className="spread">
        <div>
          {title && <h3 className="card-title">{title}</h3>}
          {sub && <p className="sub card-body">{sub}</p>}
        </div>
        {right}
      </div>
    )}
    {children}
  </section>
);

export const Stat = ({
  label,
  value,
  meta,
  tone,
  mono,
}: {
  label: string;
  value: ReactNode;
  meta?: ReactNode;
  tone?: Tone;
  mono?: boolean;
}) => (
  <div className="card blueprint stat">
    <Corners />
    <div className="label card-kicker">{label}</div>
    <div className={`value${mono ? " mono" : ""}`} style={tone ? { color: `var(--${tone === "info" ? "accent" : tone})` } : undefined}>
      {value}
    </div>
    {meta && <div className="meta">{meta}</div>}
  </div>
);

export const ModeBanner = ({ label, detail }: { label: string; detail: string }) => (
  <div className="banner mode">
    <span className="tag tag-accent">{label}</span>
    <span>{detail}</span>
  </div>
);

/** Simple grouped bar chart, hand drawn so the app carries no chart dependency. */
export const BarChart = ({
  data,
  unit = "",
  height = 170,
  colors = ["var(--accent)", "var(--accent-2)"],
}: {
  data: ReadonlyArray<{ label: string; values: readonly number[] }>;
  unit?: string;
  height?: number;
  colors?: readonly string[];
}) => {
  const max = Math.max(...data.flatMap((d) => d.values), 1);
  const pad = 34;
  const w = 100;
  return (
    <div style={{ display: "flex", gap: 14, alignItems: "flex-end", height, paddingTop: 8 }}>
      {data.map((d) => (
        <div key={d.label} style={{ flex: 1, display: "flex", flexDirection: "column", height: "100%" }}>
          <div style={{ flex: 1, display: "flex", gap: 5, alignItems: "flex-end" }}>
            {d.values.map((v, i) => (
              <div key={i} style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "flex-end", height: "100%" }}>
                <div style={{ fontSize: 11, color: "var(--ink-2)", textAlign: "center", marginBottom: 4 }}>
                  {v}{unit}
                </div>
                <div
                  style={{
                    height: `${Math.max((v / max) * (height - pad - 18), 2)}px`,
                    background: colors[i % colors.length],
                    borderRadius: "4px 4px 0 0",
                    opacity: i === 0 ? 0.55 : 1,
                    transition: "height .3s ease",
                  }}
                  title={`${d.label}: ${v}${unit}`}
                />
              </div>
            ))}
          </div>
          <div style={{ fontSize: 11, color: "var(--ink-3)", textAlign: "center", marginTop: 7, width: `${w}%` }}>
            {d.label}
          </div>
        </div>
      ))}
    </div>
  );
};

export const Sparkline = ({
  points,
  labels,
  unit = "",
}: {
  points: readonly number[];
  labels: readonly string[];
  unit?: string;
}) => {
  const w = 520;
  const h = 150;
  const pad = 26;
  const min = Math.min(...points);
  const max = Math.max(...points);
  const span = max - min || 1;
  const x = (i: number) => pad + (i * (w - pad * 2)) / Math.max(points.length - 1, 1);
  const y = (v: number) => h - pad - ((v - min) / span) * (h - pad * 2);
  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(p)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} style={{ width: "100%", height: "auto" }} role="img" aria-label="Consumption trend">
      <path d={path} fill="none" stroke="var(--accent)" strokeWidth="2.2" />
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={x(i)} cy={y(p)} r="3.6" fill="var(--accent)" />
          <text x={x(i)} y={y(p) - 11} fontSize="11" fill="var(--ink-2)" textAnchor="middle">
            {p}{unit}
          </text>
          <text x={x(i)} y={h - 7} fontSize="10.5" fill="var(--ink-3)" textAnchor="middle">
            {labels[i]}
          </text>
        </g>
      ))}
    </svg>
  );
};

export const Meter = ({ value, max, tone = "info" }: { value: number; max: number; tone?: Tone }) => (
  <div className="bar-track">
    <div
      className="bar-fill"
      style={{
        width: `${Math.min(100, (value / Math.max(max, 1)) * 100)}%`,
        background: `var(--${tone === "info" ? "accent" : tone})`,
      }}
    />
  </div>
);
