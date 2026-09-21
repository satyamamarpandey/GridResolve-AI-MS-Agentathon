/**
 * Deterministic offline customer responder.
 *
 * Template driven and rule based. It does not imitate a language model and it is
 * never presented as Foundry output. When a question falls outside the synthetic
 * evidence it says so rather than inventing an answer.
 */
import {
  billChange,
  caseInput,
  escalation,
  evidenceLedger,
  meterValidation,
  rateEffect,
  trueUp,
  usageChange,
} from "./investigation";

export interface OfflineReply {
  readonly text: string;
  readonly evidenceIds: readonly string[];
  readonly policyIds: readonly string[];
  readonly escalate: boolean;
  readonly answered: boolean;
}

const rec = caseInput.synthetic_account_records;
const curr = rec.billing_history[1];
const prev = rec.billing_history[0];

interface Rule {
  readonly id: string;
  readonly match: readonly string[];
  readonly reply: () => OfflineReply;
}

const R = (
  text: string,
  evidenceIds: readonly string[],
  policyIds: readonly string[],
  escalate = false,
): OfflineReply => ({ text, evidenceIds, policyIds, escalate, answered: true });

const RULES: readonly Rule[] = [
  {
    id: "meter-fault",
    match: ["meter", "broken", "faulty", "defect", "malfunction", "wrong reading"],
    reply: () =>
      R(
        `I understand why the meter is your first suspicion, and I have checked it directly. Both readings in this period are actual readings taken from the meter, not estimates. The register moved by ${meterValidation.registerDeltaKwh} kWh, which matches the ${curr.kwh_billed} kWh you were billed exactly. No meter events were recorded, and a remote diagnostic on ${rec.diagnostic_records[0].diagnostic_date} passed with no tamper and no register fault.\n\nI cannot confirm that the meter is faulty, because nothing in your records supports that. I also will not rule it out on my own. Policy requires a meter test or a diagnostic fault record before anyone states a meter condition, so your case is going to a meter operations specialist for that decision.`,
        ["EV-4003-03", "EV-4003-04", "EV-4003-05", "EV-4003-06"],
        ["POL-MTR-003", "POL-HUM-005"],
        true,
      ),
  },
  {
    id: "why-higher",
    match: ["why", "higher", "increase", "jumped", "went up", "so much", "expensive"],
    reply: () =>
      R(
        `Your bill went from $${prev.amount_usd.toFixed(2)} to $${curr.amount_usd.toFixed(2)}, an increase of $${billChange.deltaUsd.toFixed(2)}, which is ${billChange.percentChange}%.\n\nThe records show consumption rose from ${prev.kwh_billed} to ${curr.kwh_billed} kWh, an increase of ${usageChange.deltaKwh} kWh. Your daily use went from ${usageChange.dailyPreviousKwh} to ${usageChange.dailyCurrentKwh} kWh per day, so this is not explained by a longer billing period. Your energy rate and fixed charge did not change, so the increase is driven by measured consumption rather than pricing.\n\nWhat I cannot tell you from these records is why consumption rose inside your home. That would need information I do not hold.`,
        ["EV-4003-01", "EV-4003-02", "EV-4003-07", "EV-4003-08"],
        ["POL-HB-001"],
      ),
  },
  {
    id: "rate-change",
    match: ["rate", "price", "tariff", "per kwh", "charge went"],
    reply: () =>
      R(
        `Your rate did not change. The energy charge was $${rec.rate_components.energy_charge_usd_per_kwh} per kWh in both periods, and the fixed charge stayed at $${rec.rate_components.fixed_charge_usd_per_period}.\n\nBreaking the increase down: $${rateEffect.usageEffectUsd.toFixed(2)} comes from higher consumption, $${rateEffect.rateEffectUsd.toFixed(2)} from any rate change, and $${rateEffect.fixedEffectUsd.toFixed(2)} from fixed charges. The dominant driver is ${rateEffect.dominantDriver}.`,
        ["EV-4003-08", "EV-4003-01", "EV-4003-02"],
        ["POL-HB-001"],
      ),
  },
  {
    id: "estimated",
    match: ["estimate", "estimated", "actual read", "true up", "trueup", "catch up"],
    reply: () =>
      R(
        `Neither reading was estimated. ${trueUp.reason.charAt(0).toUpperCase()}${trueUp.reason.slice(1)}.\n\nBoth the ${rec.meter_reads[0].read_date} and ${rec.meter_reads[1].read_date} readings are actual readings, so this bill does not contain catch-up consumption from a previous estimate.`,
        ["EV-4003-03", "EV-4003-04"],
        ["POL-HB-001"],
      ),
  },
  {
    id: "credit",
    match: ["credit", "refund", "adjust", "money back", "compensate", "waive", "discount"],
    reply: () =>
      R(
        `I am not able to issue a credit or adjustment. That decision belongs to an authorized reviewer, and an adjustment needs supporting evidence of a billing error.\n\nAt the moment the records do not show a billing error: the meter readings reconcile with what you were billed, and the rate did not change. Your meter concern is going to a specialist, and if their review finds something that changes the picture, an adjustment will be considered by someone with the authority to approve it.`,
        ["EV-4003-02", "EV-4003-03", "EV-4003-04"],
        ["POL-BILL-002", "POL-HUM-005"],
        true,
      ),
  },
  {
    id: "next-steps",
    // "next" alone is too loose. It matched unrelated questions such as "next Tuesday".
    match: ["what happens", "next step", "happens now", "how long", "when will", "who is handling", "case status"],
    reply: () =>
      R(
        `${escalation.customerSafeInterimMessage}\n\nThe reviewer will decide whether a field meter test is warranted. Until that decision is made, no one will tell you the meter is faulty and no one will tell you it is fine, because neither statement is supported yet.`,
        ["EV-4003-06"],
        ["POL-MTR-003", "POL-HUM-005"],
        true,
      ),
  },
  {
    id: "evidence-request",
    match: ["proof", "evidence", "show me", "how do you know", "records"],
    reply: () =>
      R(
        `Here is what your case rests on.\n\nBilling: $${prev.amount_usd.toFixed(2)} for ${prev.kwh_billed} kWh, then $${curr.amount_usd.toFixed(2)} for ${curr.kwh_billed} kWh.\nMeter readings: ${rec.meter_reads[0].register_kwh} on ${rec.meter_reads[0].read_date}, then ${rec.meter_reads[1].register_kwh} on ${rec.meter_reads[1].read_date}, both actual.\nMeter events: none recorded.\nDiagnostic: ${rec.diagnostic_records[0].result} on ${rec.diagnostic_records[0].diagnostic_date}, no tamper, no register fault.\nConsumption history: ${rec.usage_history_kwh.map((u) => `${u.period} ${u.kwh} kWh`).join(", ")}.\n\nEvery statement I have made to you traces back to one of those records.`,
        evidenceLedger.map((e) => e.evidence_id),
        ["POL-HB-001", "POL-COMM-004"],
      ),
  },
];

const UNSUPPORTED: OfflineReply = {
  text: "I do not have information in this synthetic case that answers that, so I am not going to guess.\n\nThis offline demonstration works from a fixed set of records: your billing history, meter readings, meter events, a remote diagnostic, consumption history and the rate schedule. I can explain the bill increase, the meter readings, the rate, estimated versus actual readings, adjustments, and what happens next. Anything outside those records needs a person with access to more information.",
  evidenceIds: [],
  policyIds: ["POL-QUALITY-010"],
  escalate: false,
  answered: false,
};

const INJECTION = [
  "ignore your instructions",
  "ignore previous",
  "system prompt",
  "print your instructions",
  "you must confirm",
  "just say",
  "pretend",
  "override",
];

export const SUGGESTED_QUESTIONS: readonly string[] = [
  "Why is my bill so much higher this month?",
  "The meter has to be broken, can you confirm it?",
  "Did my rate go up?",
  "Was this an estimated reading?",
  "Can you credit the difference?",
  "What happens next?",
];

/** Whole-word phrase match, so "rate" does not fire on "separate". */
function matches(haystack: string, phrase: string): boolean {
  const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(^|[^a-z])${escaped}([^a-z]|$)`).test(haystack);
}

export function respondOffline(input: string): OfflineReply {
  const q = input.toLowerCase().trim();
  if (!q) return UNSUPPORTED;

  if (INJECTION.some((p) => q.includes(p))) {
    return {
      text: "I am going to stay with your billing case. I cannot change my instructions, reveal how I am configured, or state a conclusion that the evidence does not support, including confirming a meter fault on request.\n\nIf you would like, I can explain what your records actually show.",
      evidenceIds: [],
      policyIds: ["POL-SEC-008"],
      escalate: false,
      answered: true,
    };
  }

  // Meter wording wins over the generic increase rule, because it is the higher-risk claim.
  const ordered = [...RULES].sort((a, b) => (a.id === "meter-fault" ? -1 : b.id === "meter-fault" ? 1 : 0));
  for (const rule of ordered) {
    if (rule.match.some((m) => matches(q, m))) return rule.reply();
  }
  return UNSUPPORTED;
}
