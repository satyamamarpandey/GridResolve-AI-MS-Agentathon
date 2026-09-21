"""
GridResolve AI local static verification. No model calls, no Azure calls, no cost.

Covers:
  1. Compliance routing logic, old condition versus new condition, against mocked outputs.
  2. Synthetic case arithmetic and internal consistency.
  3. JSON and JSONL artifact validity.
  4. Manifest file-existence claims.

Run: python tests/test_routing_and_data.py
Scope note: this reproduces the INTENDED Power Fx semantics locally. It does not execute
Microsoft Foundry and is not runtime proof of the deployed workflow.

CORRECTION, 2026-09-20. Section 1 models the v4 and v5 gate expressions as if the
compliance output were a text string. It is not: `output.messages` assigns a TABLE
of message records. Evaluated with the real Power Fx engine against that table,
both the v4 and the v5 expression fail to compile ("Invalid schema, expected a
one-column table"), see tests/powerfx_gate. So the "v4 skips escalation on 5 of 11"
figure below describes a TEXT-ONLY MODEL of the expression. It was never observed
in the hosted service, where no version of this workflow has ever run, and it must
not be quoted as hosted behaviour. v6 reads Last(...).Text and is mirrored here in
Python; its authoritative test is the real-engine suite in tests/powerfx_gate.
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APPROVED_TOKEN = "ROUTE_DECISION::GRIDRESOLVE_APPROVED"
ESCALATE_TOKEN = "ROUTE_DECISION::GRIDRESOLVE_ESCALATE"

failures = []
passes = []


def check(name, got, want):
    if got == want:
        passes.append(name)
    else:
        failures.append("%s: got %r want %r" % (name, got, want))


# --- Power Fx semantics ------------------------------------------------------
# Microsoft documents the Power Fx "in" operator as matching regardless of case.
def powerfx_in(needle, haystack):
    if haystack is None:
        return False
    return needle.casefold() in str(haystack).casefold()


def route_old(compliance_output):
    """v4 under a text-only model: Not("APPROVE" in output) -> escalate.

    Under that model it skips escalation on prose containing 'approve'. Against the
    real message table the expression does not compile at all, see the module note.
    """
    return "ESCALATE" if not powerfx_in("APPROVE", compliance_output) else "NO_ESCALATION"


def route_new(compliance_output):
    """v5 under the same text-only model. Superseded by v6 on 2026-09-20."""
    if powerfx_in(APPROVED_TOKEN, compliance_output):
        return "RELEASE_APPROVED_MESSAGE"
    return "ESCALATE"


def route_v6(compliance_output):
    """Python mirror of the deployed v6 gate, tests/powerfx_gate/gate_v6.txt.

    Approve only when the text is non-blank, contains no escalate token in any
    case, contains the approved token exactly once in exact case, and the last
    non-blank line is exactly that token. Everything else escalates.
    """
    t = compliance_output
    if t is None or t == "":
        return "ESCALATE"
    if "gridresolve_escalate" in t.casefold():
        return "ESCALATE"
    if t.count(APPROVED_TOKEN) != 1:
        return "ESCALATE"
    lines = [ln.strip(" ") for ln in t.replace(chr(13), "").split(chr(10)) if ln.strip(" ")]
    if not lines or lines[-1] != APPROVED_TOKEN:
        return "ESCALATE"
    return "RELEASE_APPROVED_MESSAGE"


# --- 1. Mocked compliance outputs -------------------------------------------
def j(decision, summary, token):
    body = json.dumps({"case_id": "SYN-CASE-4003", "decision": decision,
                       "compliance_summary": summary, "correction_count": 0})
    return body + ("\n" + token if token else "")


MOCKS = [
    ("approve_clean",
     j("APPROVE", "All material claims are supported by evidence.", APPROVED_TOKEN),
     "RELEASE_APPROVED_MESSAGE"),
    ("reject_replan_prose_contains_approve",
     j("REJECT_AND_REPLAN", "Cannot approve an unsupported meter-failure claim.", ESCALATE_TOKEN),
     "ESCALATE"),
    ("reject_rewrite_prose_contains_approved",
     j("REJECT_AND_REWRITE", "The wording is not approved because it implies a defect.", ESCALATE_TOKEN),
     "ESCALATE"),
    ("human_review_required",
     j("HUMAN_REVIEW_REQUIRED", "Policy conflict requires supervisor review.", ESCALATE_TOKEN),
     "ESCALATE"),
    ("unknown_decision",
     j("SOMETHING_ELSE", "Unrecognized decision value.", ESCALATE_TOKEN),
     "ESCALATE"),
    ("missing_decision_field",
     '{"case_id": "SYN-CASE-4003", "compliance_summary": "no decision emitted"}\n' + ESCALATE_TOKEN,
     "ESCALATE"),
    ("malformed_json",
     '{"case_id": "SYN-CASE-4003", "decision": APPROVE' + "\n" + ESCALATE_TOKEN,
     "ESCALATE"),
    ("empty_output", "", "ESCALATE"),
    ("null_output", None, "ESCALATE"),
    ("token_missing_entirely",
     j("REJECT_AND_REPLAN", "Cannot approve this claim.", None),
     "ESCALATE"),
    ("lowercase_prose_only",
     "the reviewer did not approve this draft", "ESCALATE"),
]

print("=" * 72)
print("1. COMPLIANCE ROUTING: v4 and v5 under a TEXT-ONLY MODEL, and the v6 mirror")
print("=" * 72)
print("%-42s %-15s %-26s %s" % ("mock", "v4 text model", "v5 text model", "v6 mirror"))
fail_open_count = 0
for name, payload, expected_new in MOCKS:
    old = route_old(payload)
    new = route_new(payload)
    if expected_new == "ESCALATE" and old == "NO_ESCALATION":
        fail_open_count += 1
        flag = "  <-- v4 text model skips escalation"
    else:
        flag = ""
    v6 = route_v6(payload)
    print("%-42s %-15s %-26s %s%s" % (name, old, new, v6, flag))
    check("route_new[%s]" % name, new, expected_new)
    check("route_v6[%s]" % name, v6, expected_new)

print("\nUnder a text-only model, the v4 expression skips escalation on %d of %d cases."
      % (fail_open_count, len(MOCKS)))
print("Against the real message table v4 and v5 do not compile: tests/powerfx_gate.")
print("No version of this workflow has run in the hosted service.")
check("v5 releases only on the sentinel",
      sum(1 for n, p, e in MOCKS if route_new(p) == "RELEASE_APPROVED_MESSAGE"), 1)

# --- 2. Synthetic case arithmetic -------------------------------------------
print("\n" + "=" * 72)
print("2. SYN-CASE-4003 INTERNAL CONSISTENCY")
print("=" * 72)
case = json.load(open(os.path.join(ROOT, "submission", "SYN-CASE-4003_input.json"), encoding="utf-8"))
rec = case["synthetic_account_records"]
rate = rec["rate_components"]
energy, fixed = rate["energy_charge_usd_per_kwh"], rate["fixed_charge_usd_per_period"]

for bill in rec["billing_history"]:
    expected = round(bill["kwh_billed"] * energy + fixed, 2)
    check("bill math %s" % bill["record_id"], expected, bill["amount_usd"])
    print("  %s  %d kWh -> %.2f (stated %.2f)" % (bill["record_id"], bill["kwh_billed"], expected, bill["amount_usd"]))

reads = rec["meter_reads"]
delta = reads[1]["register_kwh"] - reads[0]["register_kwh"]
july = [b for b in rec["billing_history"] if b["record_id"].endswith("07")][0]["kwh_billed"]
check("register delta equals billed kWh", delta, july)
print("  register delta %d equals July billed %d" % (delta, july))

usage = {u["period"]: u["kwh"] for u in rec["usage_history_kwh"]}
check("usage history matches July bill", usage["2026-07"], july)
check("usage history matches June bill", usage["2026-06"],
      [b for b in rec["billing_history"] if b["record_id"].endswith("06")][0]["kwh_billed"])

# meter failure must be unsupported
check("no meter events", rec["meter_events"], [])
check("diagnostic passes", rec["diagnostic_records"][0]["result"], "PASS")
check("no tamper flag", rec["diagnostic_records"][0]["tamper_flag"], False)
check("no register fault", rec["diagnostic_records"][0]["register_fault_flag"], False)
check("both reads are actual", [r["read_type"] for r in reads], ["actual", "actual"])
print("  meter-failure evidence absent: no events, diagnostic PASS, both reads actual")

# expected answer must NOT be in the sent input
blob = json.dumps(case).casefold()
for leak in ("expected", "must_not", "no_supported_root_cause", "reject_unsupported"):
    check("no answer leak (%s)" % leak, leak in blob, False)
print("  no expected-outcome leakage in the sent input")

# ids unique
ids = [rec["billing_history"][0]["record_id"], rec["billing_history"][1]["record_id"],
       reads[0]["record_id"], reads[1]["record_id"], rec["diagnostic_records"][0]["record_id"]]
check("record ids unique", len(ids), len(set(ids)))

# --- 3. Artifact validity ---------------------------------------------------
print("\n" + "=" * 72)
print("3. ARTIFACT VALIDITY")
print("=" * 72)
manifest = json.load(open(os.path.join(ROOT, "gridresolve_submission_manifest.json"), encoding="utf-8"))
for fname in manifest["files"]:
    exists = os.path.isfile(os.path.join(ROOT, fname))
    check("manifest file exists: %s" % fname, exists, True)
    print("  %-45s %s" % (fname, "present" if exists else "MISSING"))

for fname, expected_rows in (("gridresolve_evaluation_suite.jsonl", 30),
                             ("gridresolve_red_team_pack.jsonl", 16)):
    path = os.path.join(ROOT, fname)
    rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
    data_rows = [r for r in rows if "_meta" not in r]
    check("%s row count" % fname, len(data_rows), expected_rows)
    key = "eval_id" if "evaluation" in fname else "attack_id"
    idents = [r[key] for r in data_rows]
    check("%s ids unique" % fname, len(idents), len(set(idents)))
    print("  %-45s %d rows, ids unique" % (fname, len(data_rows)))

pack = json.load(open(os.path.join(ROOT, "gridresolve_synthetic_pack.json"), encoding="utf-8"))
known_cases = {c["case_id"] for c in pack["cases"]}
known_policies = {p["policy_id"] for p in pack["policies"]}
evals = [json.loads(l) for l in open(os.path.join(ROOT, "gridresolve_evaluation_suite.jsonl"), encoding="utf-8") if l.strip()]
for r in evals:
    if "_meta" in r:
        continue
    check("eval %s references a real case" % r["eval_id"], r["case_id"] in known_cases, True)
print("  every evaluation case_id resolves to the synthetic pack")
print("  synthetic pack: %d cases, %d policies" % (len(known_cases), len(known_policies)))

# --- summary ----------------------------------------------------------------
print("\n" + "=" * 72)
print("RESULT: %d passed, %d failed" % (len(passes), len(failures)))
print("=" * 72)
for f in failures:
    print("  FAIL " + f)
sys.exit(1 if failures else 0)
