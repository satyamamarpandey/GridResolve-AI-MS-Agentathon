import { BarChart, Card, ModeBanner, Pill, Sparkline, Stat } from "../components/ui";
import {
  MODE_LABEL,
  billChange,
  caseInput,
  meterValidation,
  rateEffect,
  trueUp,
  usageChange,
} from "../engine/investigation";

export default function BillingInvestigation() {
  const rec = caseInput.synthetic_account_records;
  const [prev, curr] = rec.billing_history;
  const rate = rec.rate_components;

  return (
    <>
      <div className="page-head">
        <h2>Billing Investigation</h2>
        <p>
          Every value on this page is computed by the deterministic tools from the synthetic records. No
          figure is produced by a language model, because financial arithmetic should not be probabilistic.
        </p>
      </div>

      <ModeBanner
        label={MODE_LABEL}
        detail={`Case ${caseInput.case_id}, account ${rec.account_id}, meter ${rec.meter_id}. Synthetic data only.`}
      />

      <div className="grid g4" style={{ marginBottom: 14 }}>
        <Stat label="Previous bill" value={`$${prev.amount_usd.toFixed(2)}`} meta={`${prev.kwh_billed} kWh over ${prev.billing_days} days`} />
        <Stat label="Current bill" value={`$${curr.amount_usd.toFixed(2)}`} meta={`${curr.kwh_billed} kWh over ${curr.billing_days} days`} />
        <Stat label="Difference" value={`+$${billChange.deltaUsd.toFixed(2)}`} meta={`${billChange.percentChange}% ${billChange.direction}`} tone="warn" />
        <Stat label="Consumption" value={`+${usageChange.deltaKwh} kWh`} meta={`${usageChange.percentChange}% increase`} tone="warn" />
      </div>

      <div className="grid g2">
        <Card title="Bill comparison" sub="Amount billed per period, USD">
          <BarChart
            data={[
              { label: prev.period_start.slice(0, 7), values: [prev.amount_usd] },
              { label: curr.period_start.slice(0, 7), values: [curr.amount_usd] },
            ]}
            unit=""
          />
        </Card>
        <Card title="Consumption trend" sub="Billed kWh across four periods">
          <Sparkline
            points={rec.usage_history_kwh.map((u) => u.kwh)}
            labels={rec.usage_history_kwh.map((u) => u.period)}
          />
        </Card>
      </div>

      <div className="grid g2" style={{ marginTop: 14 }}>
        <Card
          title="What actually drove the change"
          sub="Decomposition by calculate_rate_effect, usage priced at the previous rate so effects do not double count"
        >
          <table>
            <thead>
              <tr>
                <th>Driver</th>
                <th>Effect</th>
                <th>Share</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Consumption</td>
                <td className="mono">${rateEffect.usageEffectUsd.toFixed(2)}</td>
                <td><Pill tone={rateEffect.dominantDriver === "usage" ? "warn" : "muted"}>dominant</Pill></td>
              </tr>
              <tr>
                <td>Energy rate</td>
                <td className="mono">${rateEffect.rateEffectUsd.toFixed(2)}</td>
                <td><Pill tone="muted">no change</Pill></td>
              </tr>
              <tr>
                <td>Fixed charge</td>
                <td className="mono">${rateEffect.fixedEffectUsd.toFixed(2)}</td>
                <td><Pill tone="muted">no change</Pill></td>
              </tr>
              <tr>
                <td><strong>Total explained</strong></td>
                <td className="mono"><strong>${rateEffect.totalExplainedUsd.toFixed(2)}</strong></td>
                <td>
                  <Pill tone={Math.abs(rateEffect.totalExplainedUsd - billChange.deltaUsd) < 0.01 ? "ok" : "bad"}>
                    reconciles
                  </Pill>
                </td>
              </tr>
            </tbody>
          </table>
          <p className="footnote">
            The decomposition reconciles exactly with the observed bill difference of $
            {billChange.deltaUsd.toFixed(2)}, so the increase is fully explained by consumption at an
            unchanged rate of ${rate.energy_charge_usd_per_kwh} per kWh.
          </p>
        </Card>

        <Card title="Meter read validation" sub="validate_meter_reads and detect_estimated_trueup">
          <table>
            <tbody>
              <tr>
                <td>Reads in window</td>
                <td className="mono">{meterValidation.readCount}</td>
              </tr>
              <tr>
                <td>All actual, none estimated</td>
                <td><Pill tone={meterValidation.allActual ? "ok" : "warn"}>{meterValidation.allActual ? "yes" : "no"}</Pill></td>
              </tr>
              <tr>
                <td>Register difference</td>
                <td className="mono">{meterValidation.registerDeltaKwh} kWh</td>
              </tr>
              <tr>
                <td>Reconciles with billed kWh</td>
                <td>
                  <Pill tone={meterValidation.registerDeltaKwh === curr.kwh_billed ? "ok" : "bad"}>
                    {meterValidation.registerDeltaKwh === curr.kwh_billed ? "exact match" : "mismatch"}
                  </Pill>
                </td>
              </tr>
              <tr>
                <td>Register rollback</td>
                <td><Pill tone={meterValidation.rollback ? "bad" : "ok"}>{meterValidation.rollback ? "detected" : "none"}</Pill></td>
              </tr>
              <tr>
                <td>Meter events</td>
                <td className="mono">{rec.meter_events.length}</td>
              </tr>
              <tr>
                <td>Remote diagnostic</td>
                <td>
                  <Pill tone={rec.diagnostic_records[0].result === "PASS" ? "ok" : "bad"}>
                    {rec.diagnostic_records[0].result}
                  </Pill>
                </td>
              </tr>
              <tr>
                <td>Estimated to actual true-up</td>
                <td><Pill tone={trueUp.detected ? "warn" : "muted"}>{trueUp.detected ? "possible" : "not applicable"}</Pill></td>
              </tr>
            </tbody>
          </table>
          <p className="footnote">{trueUp.reason}</p>
        </Card>
      </div>

      <Card
        title="Why a customer might reasonably suspect the meter"
        sub="The investigation has to take the concern seriously before it can rule it out"
        className="card"
      >
        <div style={{ marginTop: 10 }}>
          <p style={{ marginTop: 0 }}>
            A {usageChange.percentChange}% jump in a single month is large enough that a meter fault is a
            reasonable customer hypothesis. The daily rate rose from{" "}
            <code className="inline">{usageChange.dailyPreviousKwh} kWh/day</code> to{" "}
            <code className="inline">{usageChange.dailyCurrentKwh} kWh/day</code>, so the change is not an
            artifact of a longer billing period.
          </p>
          <p>
            What rules the hypothesis out is not confidence, it is records. The register difference matches
            billed consumption exactly, both reads are actual rather than estimated, no meter events were
            logged, and the remote diagnostic passed with no tamper and no register fault. None of that
            proves the meter is healthy in a laboratory sense. It means no available evidence supports a
            defect, which is a different and more honest statement.
          </p>
          <p style={{ marginBottom: 0 }}>
            Under policy POL-MTR-003 a meter defect claim requires a meter test or a diagnostic fault
            record. Neither exists here, so the system is not permitted to confirm the customer hypothesis,
            and the case routes to a meter operations specialist instead.
          </p>
        </div>
      </Card>
    </>
  );
}
