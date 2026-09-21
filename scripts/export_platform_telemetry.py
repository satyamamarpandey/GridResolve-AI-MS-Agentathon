"""Export a redacted summary of what the Foundry platform itself recorded for the real runs.

Read only. It sends GET requests to Azure Monitor and read-only queries to the
Application Insights resource that was connected to the project when the project
was created. It calls no model, runs no workflow and creates nothing in Azure.
Log queries and platform metrics reads are not billed.

The output is a derived summary, not runtime evidence. It never replaces the
files under evidence/runtime/. It holds span names, durations, success flags,
token counts and content filter verdicts. It does not hold prompts, outputs,
resource names, subscription identifiers or the Application Insights app id.

Needs three shell variables, never written to disk:
  GRIDRESOLVE_FOUNDRY_RESOURCE, GRIDRESOLVE_FOUNDRY_PROJECT, GRIDRESOLVE_FOUNDRY_RG

  python scripts/export_platform_telemetry.py
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "evidence", "platform_telemetry")
OUT = os.path.join(OUT_DIR, "platform_telemetry_summary.json")
LEDGER = os.path.join(ROOT, "evidence", "runtime", "RUN_LEDGER.json")
WINDOW = "2026-09-17T00:00:00Z/2026-09-22T00:00:00Z"
SINCE = "datetime(2026-09-17)"
METRICS = ("InputTokens", "OutputTokens", "TotalTokens", "ModelRequests", "BlockedCalls")
MATCH_SECONDS = 60
AZ_DEFAULT = r"C:\Program Files\Microsoft SDKs\Azure\CLI2\wbin\az.cmd"

QUERIES = {
    "tables": "union withsource=SourceTable * | where timestamp > %s | summarize n=count() by SourceTable" % SINCE,
    "workflow_requests": "requests | where timestamp > %s | project timestamp, name, duration, success, resultCode, operation_Id | order by timestamp asc" % SINCE,
    "agent_spans": "dependencies | where timestamp > %s | where name startswith 'invoke_agent' | extend cf=parse_json(tostring(customDimensions['microsoft.foundry.content_filter.results'])) | project timestamp, operation_Id, name, duration, success, prompt_blocked=tobool(cf[0].blocked), completion_blocked=tobool(cf[1].blocked), jailbreak_detected=tobool(cf[0].content_filter_results.jailbreak.detected) | order by timestamp asc" % SINCE,
    "chat_usage": "dependencies | where timestamp > %s | where name startswith 'chat' | extend i=toint(customDimensions['gen_ai.usage.input_tokens']), o=toint(customDimensions['gen_ai.usage.output_tokens']), c=toint(customDimensions['gen_ai.usage.cached_tokens']) | summarize calls=count(), input_tokens=sum(i), output_tokens=sum(o), cached_tokens=sum(c), failed=countif(success == false) by operation_Id" % SINCE,
    "ingested": "union * | where timestamp > %s | summarize megabytes=sum(_BilledSize)/1e6" % SINCE,
    "content_recording": "dependencies | where timestamp > %s | extend d=tostring(customDimensions) | summarize spans_with_message_content=countif(d contains 'gen_ai.input.messages' or d contains 'gen_ai.output.messages'), spans=count()" % SINCE,
}


def az(*args):
    exe = shutil.which("az") or shutil.which("az.cmd") or AZ_DEFAULT
    if not os.path.exists(exe):
        sys.exit("Azure CLI not found. Sign in with az login first.")
    done = subprocess.run([exe, *args], capture_output=True, text=True)
    if done.returncode != 0:
        sys.exit("Azure CLI call failed. Sign in with az login, then run this again.")
    return done.stdout.strip()


def token(resource):
    return az("account", "get-access-token", "--resource", resource, "--query", "accessToken", "-o", "tsv")


def get(url, bearer):
    request = urllib.request.Request(url, headers={"Authorization": "Bearer " + bearer})
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        sys.exit("Read failed with HTTP %s. Nothing was written." % error.code)


def rows(table):
    names = [c["name"] for c in table["columns"]]
    return [dict(zip(names, r)) for r in table["rows"]]


def parse(stamp):
    return datetime.fromisoformat(stamp.replace("Z", "+00:00")[:19] + "+00:00") if "T" in stamp else None


def match_run(start, ledger):
    for entry in ledger:
        if abs((parse(start) - datetime.fromisoformat(entry["started_at"])).total_seconds()) <= MATCH_SECONDS:
            return entry["run_dir"]
    return None


def main():
    secrets = [os.environ[k] for k in ("GRIDRESOLVE_FOUNDRY_RESOURCE", "GRIDRESOLVE_FOUNDRY_PROJECT", "GRIDRESOLVE_FOUNDRY_RG")]
    resource, _, group = secrets
    subscription = az("account", "show", "--query", "id", "-o", "tsv")
    arm = token("https://management.azure.com")
    base = "https://management.azure.com/subscriptions/%s/resourceGroups/%s" % (subscription, group)
    account = base + "/providers/Microsoft.CognitiveServices/accounts/" + resource

    metrics = {}
    for name in METRICS:
        query = urllib.parse.urlencode({"api-version": "2018-01-01", "metricnames": name, "timespan": WINDOW,
                                        "interval": "PT1H", "aggregation": "Total"})
        body = get(account + "/providers/Microsoft.Insights/metrics?" + query, arm)
        buckets = [{"hour": p["timeStamp"], "total": p["total"]}
                   for series in body["value"][0]["timeseries"] for p in series["data"] if p.get("total")]
        metrics[name] = {"total": sum(b["total"] for b in buckets), "hourly": buckets}

    components = get(base + "/providers/Microsoft.Insights/components?api-version=2020-02-02", arm)["value"]
    if not components:
        sys.exit("No Application Insights component in the resource group. Nothing was written.")
    app_id = components[0]["properties"]["AppId"]
    secrets += [subscription, app_id]
    insights = token("https://api.applicationinsights.io")
    result = {}
    for label, kql in QUERIES.items():
        url = "https://api.applicationinsights.io/v1/apps/%s/query?%s" % (app_id, urllib.parse.urlencode({"query": kql}))
        result[label] = rows(get(url, insights)["tables"][0])

    with open(LEDGER, encoding="utf-8") as handle:
        ledger = json.load(handle)
    usage = {u["operation_Id"]: u for u in result["chat_usage"]}
    runs = []
    for request in result["workflow_requests"]:
        op = request["operation_Id"]
        spans = [s for s in result["agent_spans"] if s["operation_Id"] == op]
        runs.append({
            "run_dir": match_run(request["timestamp"], ledger),
            "trace_id": op,
            "workflow_span": {"name": request["name"], "started": request["timestamp"],
                              "duration_ms": round(float(request["duration"])), "success": request["success"],
                              "result_code": request["resultCode"]},
            "model_calls": {k: usage.get(op, {}).get(k) for k in ("calls", "input_tokens", "output_tokens", "cached_tokens", "failed")},
            "agent_spans": [{"name": s["name"], "duration_ms": round(float(s["duration"])), "success": s["success"],
                             "prompt_blocked": s["prompt_blocked"], "completion_blocked": s["completion_blocked"],
                             "jailbreak_detected": s["jailbreak_detected"]} for s in spans],
        })

    summary = {
        "what_this_is": "A redacted, read-only summary of what Azure Monitor and the connected Application Insights resource recorded for the real Foundry runs. Derived. Not runtime evidence, and not a substitute for evidence/runtime/.",
        "how_to_reproduce": "python scripts/export_platform_telemetry.py, signed in with az login, with the three GRIDRESOLVE_FOUNDRY variables set in the shell.",
        "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": WINDOW,
        "azure_monitor_metrics": metrics,
        "application_insights": {
            "rows_by_table": {r["SourceTable"]: r["n"] for r in result["tables"]},
            "ingested_megabytes": round(result["ingested"][0]["megabytes"], 3),
            "content_recording": result["content_recording"][0],
        },
        "runs": runs,
        "not_included": ["prompts", "model outputs", "resource, project and subscription identifiers", "the Application Insights app id"],
    }
    text = json.dumps(summary, indent=1)
    leaked = [s for s in secrets if s and s.lower() in text.lower()]
    if leaked:
        sys.exit("Refusing to write: the summary contains a tenant identifier.")
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text + "\n")
    print("wrote", os.path.relpath(OUT, ROOT))
    for run in runs:
        print(run["run_dir"], run["model_calls"])


if __name__ == "__main__":
    main()
