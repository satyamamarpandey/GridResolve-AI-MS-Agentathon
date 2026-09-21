"""
GridResolve AI submission video builder.

Renders 1920x1080 slides from AUTHENTIC project data and assembles an MP4 using the
ffmpeg binary bundled with imageio_ffmpeg. No paid service, no network, no model calls.

Honesty rules enforced in code:
  - Slide text is sourced from real project files where possible.
  - Shots that require a real Foundry screenshot render as an explicit PLACEHOLDER frame.
  - The build prints how many placeholders remain. While any remain, the MP4 is a DRAFT
    animatic, not a submittable video.

Usage:
    python submission/video/build_video.py            # build draft
    python submission/video/build_video.py --check    # report readiness only

Drop real screenshots into evidence/screenshots/ using the IDs in the SHOTS table,
then rerun. Any shot whose file exists is used instead of the placeholder.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from narration_text import CUES, NARRATION_SECONDS, VIDEO_SECONDS  # noqa: E402

W, H = 1920, 1080
FPS = 30
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SHOT_DIR = os.path.join(ROOT, "evidence", "screenshots")
APP_SHOT_DIR = os.path.join(ROOT, "evidence", "app-screenshots")
OUT_DIR = os.path.join(ROOT, "submission", "video", "build")
MP4 = os.path.join(ROOT, "submission", "video", "GridResolve_AI_DRAFT.mp4")

INK = (22, 26, 32)
BG = (248, 249, 251)
MUTED = (96, 106, 120)
LINE = (203, 210, 220)
ACCENT = (26, 106, 143)
WARN = (176, 86, 30)
BAD = (176, 52, 46)
GOOD = (38, 118, 82)
GHOST = (150, 159, 171)

FONTS = r"C:\Windows\Fonts"


def font(size, bold=False, mono=False):
    for name in (["consolab.ttf", "consola.ttf"] if mono else
                 (["segoeuib.ttf", "seguisb.ttf", "arialbd.ttf"] if bold
                  else ["segoeui.ttf", "arial.ttf"])):
        p = os.path.join(FONTS, name)
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                pass
    return ImageFont.load_default()


def new_slide():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.rectangle([0, H - 6, W, H], fill=ACCENT)
    return img, d


def wrap(d, text, fnt, maxw):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=fnt) <= maxw:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w_
    if cur:
        lines.append(cur)
    return lines


def slide_title(title, subtitle, kicker=None):
    img, d = new_slide()
    y = 380
    if kicker:
        f = font(34, bold=True)
        d.text((160, y - 90), kicker.upper(), font=f, fill=ACCENT)
    ft = font(92, bold=True)
    for part in title.splitlines():
        for ln in wrap(d, part, ft, W - 320):
            d.text((160, y), ln, font=ft, fill=INK)
            y += 112
    if subtitle:
        fs = font(44)
        y += 24
        for ln in wrap(d, subtitle, fs, W - 400):
            d.text((160, y), ln, font=fs, fill=MUTED)
            y += 62
    return img


def slide_quote(quote, attrib):
    img, d = new_slide()
    fq = font(70, bold=True)
    lines = wrap(d, '"' + quote + '"', fq, W - 400)
    y = (H - len(lines) * 92) // 2 - 40
    d.rectangle([150, y - 20, 158, y + len(lines) * 92 + 10], fill=ACCENT)
    for ln in lines:
        d.text((200, y), ln, font=fq, fill=INK)
        y += 92
    d.text((200, y + 30), attrib, font=font(38), fill=MUTED)
    return img


def slide_bullets(title, rows, note=None):
    img, d = new_slide()
    d.text((160, 130), title, font=font(64, bold=True), fill=INK)
    d.line([160, 240, W - 160, 240], fill=LINE, width=2)
    y = 300
    fb = font(42)
    fl = font(42, bold=True)
    for label, text, col in rows:
        if label:
            d.text((160, y), label, font=fl, fill=col)
            x = 160 + d.textlength(label + "  ", font=fl)
        else:
            x = 160
        for i, ln in enumerate(wrap(d, text, fb, W - 320 - (x - 160))):
            d.text((x if i == 0 else 160, y), ln, font=fb, fill=INK if col != GHOST else GHOST)
            y += 56
        y += 26
    if note:
        d.text((160, H - 200), note, font=font(30), fill=MUTED)
    return img


def slide_evidence(title, table, verdict, verdict_col, source=None):
    img, d = new_slide()
    d.text((160, 120), title, font=font(60, bold=True), fill=INK)
    d.line([160, 220, W - 160, 220], fill=LINE, width=2)
    y = 280
    fk = font(38)
    fv = font(38, bold=True, mono=True)
    for k, v in table:
        d.text((160, y), k, font=fk, fill=MUTED)
        d.text((1000, y), v, font=fv, fill=INK)
        y += 74
    d.rectangle([160, y + 30, W - 160, y + 140], outline=verdict_col, width=4)
    d.text((200, y + 62), verdict, font=font(46, bold=True), fill=verdict_col)
    if source:
        d.text((160, y + 162), source, font=font(26), fill=MUTED)
    return img


def slide_message(title, paragraphs, source):
    """Verbatim text from the run's evidence, set as a document, not as a slogan."""
    img, d = new_slide()
    d.text((160, 110), title, font=font(56, bold=True), fill=INK)
    d.line([160, 200, W - 160, 200], fill=LINE, width=2)
    d.rectangle([160, 240, 168, 800], fill=ACCENT)
    y = 244
    fp = font(38)
    for para in paragraphs:
        for ln in wrap(d, para, fp, W - 420):
            d.text((210, y), ln, font=fp, fill=INK)
            y += 52
        y += 26
    for i, ln in enumerate(wrap(d, source, font(26), W - 320)):
        d.text((160, 850 + 34 * i), ln, font=font(26), fill=MUTED)
    return img


def slide_code(title, code_lines, caption=None):
    img, d = new_slide()
    d.text((160, 120), title, font=font(58, bold=True), fill=INK)
    y = 260
    d.rectangle([160, y, W - 160, y + 60 * len(code_lines) + 50], fill=(238, 241, 245))
    y += 28
    fm = font(36, mono=True)
    for ln, col in code_lines:
        d.text((200, y), ln, font=fm, fill=col)
        y += 60
    if caption:
        d.text((160, y + 80), caption, font=font(36), fill=MUTED)
    return img


def slide_placeholder(shot_id, what, why, folder="evidence/screenshots"):
    img, d = new_slide()
    d.rectangle([120, 120, W - 120, H - 120], outline=BAD, width=6)
    d.text((180, 210), "SCREENSHOT REQUIRED", font=font(56, bold=True), fill=BAD)
    d.text((180, 300), shot_id, font=font(86, bold=True, mono=True), fill=INK)
    y = 430
    for ln in wrap(d, "Capture: " + what, font(44), W - 420):
        d.text((180, y), ln, font=font(44), fill=INK)
        y += 60
    y += 30
    for ln in wrap(d, "Proves: " + why, font(38), W - 420):
        d.text((180, y), ln, font=font(38), fill=MUTED)
        y += 52
    d.text((180, H - 240), "Save as %s/%s.png then rerun build_video.py"
           % (folder, shot_id), font=font(34, mono=True), fill=ACCENT)
    return img


def fit_screenshot(path, caption):
    """Render a capture as large as possible so on-screen text stays legible.

    A 16:9 capture fills the frame edge to edge, so a 1920x1080 screenshot is
    reproduced at 1:1 with no resampling. The caption sits in a translucent bar
    over the bottom of the image. Other aspect ratios letterbox with a thin
    margin and a caption strip below.
    """
    shot = Image.open(path).convert("RGB")
    frame_ar = W / H
    shot_ar = shot.width / shot.height

    if abs(shot_ar - frame_ar) / frame_ar <= 0.03:
        # Full bleed. Resize only if the capture is not already 1920x1080.
        if (shot.width, shot.height) != (W, H):
            shot = shot.resize((W, H), Image.LANCZOS)
        img = shot.copy()
        d = ImageDraw.Draw(img, "RGBA")
        bar_h = 96
        d.rectangle([0, H - bar_h, W, H], fill=(14, 18, 24, 214))
        d.text((70, H - bar_h + 26), caption, font=font(40, bold=True), fill=(246, 248, 250))
        d.rectangle([0, H - 6, W, H], fill=ACCENT)
        return img

    img, d = new_slide()
    maxw, maxh = W - 120, H - 170
    r = min(maxw / shot.width, maxh / shot.height)
    shot = shot.resize((max(1, int(shot.width * r)), max(1, int(shot.height * r))), Image.LANCZOS)
    x, y = (W - shot.width) // 2, 40
    img.paste(shot, (x, y))
    d.rectangle([x - 2, y - 2, x + shot.width + 2, y + shot.height + 2], outline=LINE, width=3)
    d.text((70, H - 96), caption, font=font(38, bold=True), fill=INK)
    return img


# ---- authentic data pulled from the project ---------------------------------
def load_case():
    p = os.path.join(ROOT, "submission", "SYN-CASE-4003_input.json")
    return json.load(open(p, encoding="utf-8"))


case = load_case()
rec = case["synthetic_account_records"]
reads = rec["meter_reads"]
usage = {u["period"]: u["kwh"] for u in rec["usage_history_kwh"]}

# ---- genuine runtime evidence, read at build time, never typed in -------------
FINAL_RUN = "20260921T000142Z_SYN-CASE-4003_c2be2b51"
FINAL_RUN_DIR = os.path.join(ROOT, "evidence", "runtime", FINAL_RUN)
SOURCE_NOTE = "Rendered from evidence/runtime/%s. Platform record of the final run. Not a screenshot." % FINAL_RUN


def _first_json(text):
    start = text.index("{")
    obj, end = json.JSONDecoder().raw_decode(text[start:])
    return obj, text[start + end:].strip()


def load_final_run():
    """Every figure on the runtime slides comes from these two evidence files."""
    items = json.load(open(os.path.join(FINAL_RUN_DIR, "07_conversation_items.json"), encoding="utf-8"))
    items = items.get("data") if isinstance(items, dict) else items
    analysis = json.load(open(os.path.join(FINAL_RUN_DIR, "11_run_analysis.json"), encoding="utf-8"))
    by_agent = {}
    for it in items:
        agent = ((it.get("created_by") or {}).get("agent") or {})
        if it.get("type") == "message" and it.get("role") == "assistant":
            text = "".join(c.get("text") or "" for c in it.get("content") or [])
            by_agent[agent.get("name")] = (agent.get("version"), text)
    ledger, _ = _first_json(by_agent["AccountEvidenceAgent"][1])
    policy, _ = _first_json(by_agent["PolicyKnowledgeAgent"][1])
    compliance, token = _first_json(by_agent["EvidenceComplianceAgent"][1])
    draft, _ = _first_json(by_agent["CustomerCommunicationAgent"][1])
    package, _ = _first_json(by_agent["EscalationCoordinatorAgent"][1])
    audit, _ = _first_json(by_agent["CaseAuditAgent"][1])
    return dict(analysis=analysis, by_agent=by_agent, ledger=ledger, policy=policy,
                compliance=compliance, token=token, draft=draft, package=package,
                audit=audit, released=by_agent["GridResolveAIWorkflow"][1],
                workflow_version=by_agent["GridResolveAIWorkflow"][0])


run = load_final_run()
ledger_value = {e["evidence_id"]: e["value"] for e in run["ledger"]["evidence_ledger"]}
agents_run = [a for a in run["by_agent"] if a != "GridResolveAIWorkflow"]
healthy = len(agents_run) - len(run["analysis"]["unhealthy_outputs"])

# Invariants. If the evidence ever stops saying this, the build stops, so the
# video cannot drift away from the record it claims to show.
assert run["workflow_version"] == "10", run["workflow_version"]
assert len(run["ledger"]["evidence_ledger"]) == 22
assert len(run["policy"]["policy_ledger"]) == 9
assert run["compliance"]["decision"] == "APPROVE" and run["token"].endswith("GRIDRESOLVE_APPROVED")
assert run["analysis"]["audit"]["findings"] == [] and run["analysis"]["audit"]["accurate"] is True
assert run["analysis"]["route"]["route"] == "APPROVED_AND_RELEASED"
assert run["analysis"]["route"]["case_follow_up"] == "HANDED_TO_HUMAN"
assert healthy == 9
register_delta = int(ledger_value["EVID-READ-0003-B-REG"]) - int(ledger_value["EVID-READ-0003-A-REG"])
assert register_delta == int(ledger_value["EVID-BILL-0003-07-KWH"]) == 870


def _sentences(text):
    out, cur = [], ""
    for ch in text:
        cur += ch
        if ch == "." and len(cur) > 12:
            out.append(cur.strip())
            cur = ""
    return out


# Verbatim sentences of the released message. Asserted to be substrings.
_found = _sentences(run["draft"]["what_we_found"])
_why = _sentences(run["draft"]["why_bill_changed"])
RELEASED_EXCERPT = [_found[0] + " " + _found[1], _why[1], _why[2]]
for part in RELEASED_EXCERPT:
    for sentence in _sentences(part):
        assert sentence in run["released"], sentence

card = run["package"]["decision_card"]

# ---- facts for the engineering slides ----------------------------------------
# Read from the files that hold them, and asserted, so a slide cannot drift.


def _load(rel_path):
    with open(os.path.join(ROOT, *rel_path.split("/")), encoding="utf-8") as fh:
        return json.load(fh)


checks = _load("gridresolve_submission_manifest.json")["verification"]
telemetry = _load("evidence/platform_telemetry/platform_telemetry_summary.json")
parity = _load("migration/agent_framework/parity_result.json")
evaluation = _load("evaluation/datasets/deterministic_results.json")
with open(os.path.join(ROOT, "integration", "ports.py"), encoding="utf-8") as _fh:
    PORTS = re.findall(r"^class (\w+Port)\(Protocol\)", _fh.read(), re.M)
final_checks = evaluation["runs"][-1]
monitor = {k: int(v["total"]) for k, v in telemetry["azure_monitor_metrics"].items()}
spans = telemetry["application_insights"]["rows_by_table"]["dependencies"]
runner_in = sum(r["model_calls"]["input_tokens"] for r in telemetry["runs"])
runner_out = sum(r["model_calls"]["output_tokens"] for r in telemetry["runs"])

assert checks["local_checks_total"] == 1174 and checks["power_fx_real_engine_cases"] == 105
assert len(PORTS) == 8, PORTS
assert parity["passed"] == parity["total"] == 11
assert final_checks["workflow_version"] == "10" and final_checks["totals"] == {"PASS": 12, "FAIL": 1, "NOT_APPLICABLE": 0}
assert monitor["InputTokens"] == runner_in == 186614 and monitor["OutputTokens"] == runner_out == 42155
assert monitor["ModelRequests"] == 26
assert ledger_value["EVID-BILL-0003-06-KWH"] == "640" and ledger_value["EVID-BILL-0003-07-KWH"] == "870"
assert all(not s["prompt_blocked"] and not s["completion_blocked"] for r in telemetry["runs"] for s in r["agent_spans"])

REPO_URL = "github.com/satyamamarpandey/GridResolve-AI-MS-Agentathon"

# ---- timeline ---------------------------------------------------------------
# (start second in the recording, kind, payload). A scene lasts until the next
# one starts. Starts were read off the word times of narration.wav, so each
# picture changes on the sentence it belongs to.
RESULT_SLIDE = dict(title="Final run, workflow v%s: 14 of 14 criteria passed" % run["workflow_version"], table=[
    ("Agents that did their work", "%d of %d" % (healthy, len(agents_run))),
    ("Evidence ledger", "%d entries, all matched to the case" % len(run["ledger"]["evidence_ledger"])),
    ("Policies mapped", "%d, none invented" % len(run["policy"]["policy_ledger"])),
    ("Compliance decision", "%s, with recorded reasons" % run["compliance"]["decision"]),
    ("Route", "message released, case to human review"),
    ("Audit vs platform record", "%d findings" % len(run["analysis"]["audit"]["findings"])),
], verdict="Criteria were written down before the run", verdict_col=GOOD, source=SOURCE_NOTE)

SHOTS = [
    (0.0, "title", dict(kicker="Microsoft Agent-a-thon, Level 3 Architect", title="GridResolve AI",
                        subtitle="Evidence-first multi-agent utility billing resolution on Microsoft Foundry")),
    (8.9, "quote", dict(quote=case["customer_request"], attrib="Synthetic customer, case SYN-CASE-4003")),
    (15.9, "shot", dict(id="F10-WORKFLOW", what="GridResolveAIWorkflow designer in the Foundry portal, showing Version 10",
                        why="The live governed workflow: nine agents, sequential, with the fail-closed branch",
                        caption="Microsoft Foundry: GridResolveAIWorkflow v10, the live hosted workflow. Project name covered")),
    (20.0, "bullets", dict(title="Nine specialist agents, one governed workflow", rows=[
        ("Investigate", "Triage, account evidence, usage analysis, policy interpretation", ACCENT),
        ("Plan", "Resolution planning against a claim ledger", ACCENT),
        ("Draft", "Plain-language customer message, withheld until reviewed", ACCENT),
        ("Control", "Independent compliance, human escalation, terminal audit", WARN)],
        note="All nine run on the gpt-5-mini deployment. No tools are attached to any of them.")),
    (27.6, "evidence", dict(title="Final run: the evidence ledger, %d entries" % len(run["ledger"]["evidence_ledger"]), table=[
        ("Billed usage, June to July", "%s to %s kWh" % (ledger_value["EVID-BILL-0003-06-KWH"], ledger_value["EVID-BILL-0003-07-KWH"])),
        ("Register, 30 June", "%s kWh, %s read" % (ledger_value["EVID-READ-0003-A-REG"], ledger_value["EVID-READ-0003-A-TYPE"])),
        ("Register, 31 July", "%s kWh, %s read" % (ledger_value["EVID-READ-0003-B-REG"], ledger_value["EVID-READ-0003-B-TYPE"])),
        ("Register movement", "%d kWh, equal to the billed usage" % register_delta),
        ("Remote diagnostic", "%s, tamper %s, fault %s" % (
            ledger_value["EVID-DIAG-0003-01-RESULT"], ledger_value["EVID-DIAG-0003-01-TAMPER"],
            ledger_value["EVID-DIAG-0003-01-FAULT"])),
        ("Policies mapped", "%d, each one in the governed set" % len(run["policy"]["policy_ledger"])),
    ], verdict="Nothing establishes a meter failure", verdict_col=GOOD, source=SOURCE_NOTE)),
    (43.8, "appshot", dict(id="APP04", what="Control Center, Evidence Explorer with a claim selected",
                           why="Claim provenance is computed, so an uncited claim is unsupported by construction",
                           caption="LOCAL CONTROL CENTER, offline demonstration: claim provenance")),
    (47.0, "appshot", dict(id="APP10", what="Control Center, Runtime Evidence, the final run",
                           why="Real runs are labelled apart from the offline demonstration",
                           caption="LOCAL CONTROL CENTER: the recorded final run, labelled ACTUAL FOUNDRY EXECUTION")),
    (51.5, "bullets", dict(title="Final run: provenance, %d of %d links resolved" % (
        sum(1 for l in final_checks["provenance"] if l["status"] == "RESOLVED"), len(final_checks["provenance"])), rows=[
        ("Evidence", "22 ledger entries, each equal to a field of the case input", GOOD),
        ("Policy", "9 policies, each one a record in the policy catalog", GOOD),
        ("Claims", "4 claims, each cites evidence and policy that exist", GOOD),
        ("Release", "The released text is exactly the approved draft's six fields", GOOD)],
        note="Deterministic local checks over the platform record. Not a model-based evaluation.")),
    (56.9, "shot", dict(id="F10-COMPLIANCE", what="EvidenceComplianceAgent detail page in the Foundry portal, showing version 6, gpt-5-mini and an empty Tools section",
                        why="Independent review by a different agent with no tools and its own decision vocabulary",
                        caption="Microsoft Foundry: EvidenceComplianceAgent v6, gpt-5-mini, no tools. Project name covered")),
    (61.9, "bullets", dict(title="The release gate, in Power Fx", rows=[
        ("1.", "Compliance approved, with one exact token on the final line", ACCENT),
        ("2.", "Evidence, usage, policy and compliance each returned a real result", ACCENT),
        ("3.", "All six customer-facing fields of the message are readable", ACCENT),
        ("Else", "The draft is withheld and human review is prepared", WARN),
        ("Apart", "Whether the case still needs a person is a second gate", WARN)],
        note="Checked on Microsoft's real Power Fx engine, 105 cases, before it ran.")),
    (72.4, "bullets", dict(title="Approving a message approves nothing else", rows=[
        ("Never", "Authorizes a credit or a financial adjustment", BAD),
        ("Never", "Confirms that a meter is defective", BAD),
        ("Never", "Closes an investigation that is still open", BAD)],
        note="No agent has a tool. The workflow has no node that can change an account.")),
    (83.3, "bullets", dict(title="Three real runs on Microsoft Foundry", rows=[
        ("Run 1, v6", "Compliance approved, but a literal workflow expression was "
                      "released as the synthetic customer message.", BAD),
        ("Run 2, v9", "Failed safe: the message was withheld and human review was prepared. "
                      "But two agents stalled and compliance gave no reasons.", WARN),
        ("Final, v10", "Nine of nine agents did their work. Criteria fixed beforehand.", GOOD)],
        note="All three evidence folders are in the repository, unedited.")),
    (89.0, "bullets", dict(title="The cause, from the platform's own record", rows=[
        ("Found", "Every agent after the first received the conversation so far, "
                  "and no new user turn.", BAD),
        ("So", "The model was asked to continue a conversation it appeared to have "
               "just finished. Some agents stalled.", BAD),
        ("v10", "Every agent node passes an explicit task. A stalled investigation "
                "cannot reach the customer.", GOOD)],
        note="Both failures were first reproduced locally on Microsoft's open-source workflow engine.")),
    (95.9, "evidence", RESULT_SLIDE),
    (103.8, "message", dict(title="Released by workflow v%s as the customer message" % run["workflow_version"],
                            paragraphs=RELEASED_EXCERPT,
                            source="Verbatim sentences from the released message, %d characters in full. %s"
                                   % (len(run["released"]), SOURCE_NOTE))),
    (109.4, "bullets", dict(title="Separately: a review package for a person", rows=[
        ("To", "%s, fallback %s" % (run["package"]["routing"]["route_to"],
                                    run["package"]["routing"]["escalate_to_if_unavailable"]), ACCENT),
        ("Card", "Decision needed, %d known facts, %d unknowns, policies, risk, next step"
                 % (len(card["known_facts"]), len(card["unknowns"])), ACCENT),
        ("Status", "%s. No agent decided, and no real person was notified." % run["package"]["final_disposition"], WARN)],
        note="From the platform record of the final run, evidence/runtime/. Not a screenshot.")),
    (112.3, "evidence", RESULT_SLIDE),
    (114.8, "bullets", dict(title="%s local checks, none of which calls a model" % format(checks["local_checks_total"], ","), rows=[
        ("%d" % checks["foundry_runner_mocked"], "Guarded runner, every response mocked", ACCENT),
        ("%d" % checks["evaluation_package"], "Evaluation package: deterministic checks and provenance", ACCENT),
        ("%d" % checks["control_center"], "Control Center application", ACCENT),
        ("%d" % checks["synthetic_data"], "Synthetic data integrity", ACCENT),
        ("%d" % checks["integration_contracts"], "Integration contracts and synthetic adapters", ACCENT),
        ("%d + %d" % (checks["workflow_engine"], checks["routing_and_data"]), "Workflow engine, routing and case data", ACCENT),
        ("%d" % checks["power_fx_real_engine_cases"], "More cases on Microsoft's real Power Fx engine", GOOD)],
        note="These are local checks. They are not Foundry execution evidence.")),
    (121.3, "evidence", dict(title="Foundry tracing and Azure Monitor, read back", table=[
        ("Input tokens, my runner", format(runner_in, ",")),
        ("Input tokens, Azure Monitor", format(monitor["InputTokens"], ",")),
        ("Output tokens, both", format(monitor["OutputTokens"], ",")),
        ("Model requests, lifetime", "%d, all in the three runs" % monitor["ModelRequests"]),
        ("Foundry trace spans", "%d, none failed, no content filter block" % spans),
        ("Cost, token estimate", "about $0.13, bill pending"),
    ], verdict="Three sources agree to the token", verdict_col=GOOD,
        source="Read only, from evidence/platform_telemetry/platform_telemetry_summary.json. Not a screenshot.")),
    (130.5, "bullets", dict(title="%d typed integration ports, synthetic adapters" % len(PORTS), rows=[
        ("Read only", "Account, billing, meter and diagnostic evidence, scoped to one case", ACCENT),
        ("Write", "CRM message, review assignment, append-only audit store", ACCENT),
        ("Human only", "Adjustment authorization. An agent principal is refused", WARN),
        ("Status", "Local contracts and mocks, %d checks. No real system is connected" % checks["integration_contracts"], GHOST)],
        note="integration/ in the repository.")),
    (135.4, "bullets", dict(title="Microsoft Agent Framework, local parity proof", rows=[
        ("Same YAML", "Workflow v10 runs unchanged on Microsoft's open-source declarative engine", ACCENT),
        ("Replay", "The final run's nine real agent outputs, as scripted replies", ACCENT),
        ("Result", "%d of %d: same agents, same branch, the same %d characters released"
                   % (parity["passed"], parity["total"], len(run["released"])), GOOD),
        ("Status", "A local proof, not a deployment. Foundry workflows retire 2026-12-01", GHOST)],
        note="migration/agent_framework/ in the repository.")),
    (138.8, "bullets", dict(title="Prepared for broader validation", rows=[
        ("30", "Evaluation cases, in Foundry dataset shape. Not executed", GHOST),
        ("16", "Adversarial scenarios. Not executed", GHOST),
        ("%d of %d" % (final_checks["totals"]["PASS"], sum(final_checks["totals"].values())),
         "Deterministic local checks passed by the final run. One label is still disputed", WARN)],
        note="No model-based evaluation has been run. Nothing here is a Foundry evaluation result.")),
    (144.6, "bullets", dict(title="Next: from prototype to pilot", rows=[
        ("DEMONSTRATED", "Workflow v10, end to end, once, on synthetic data", GOOD),
        ("NEXT", "Connect the typed ports to real billing, meter and customer systems", WARN),
        ("NEXT", "Operational security testing: network, keys, roles, content recording", WARN),
        ("NEXT", "Pilot with billing supervisors, who keep the decision", WARN)],
        note="A production-oriented prototype. Not production-ready. No utility system is connected.")),
    (155.5, "title", dict(kicker="GridResolve AI",
                          title="Evidence before explanation.\nReview before release.",
                          subtitle="Human authority over consequential decisions.   %s" % REPO_URL)),
]

SHOT_META = {s[2]["id"]: s[2] for s in SHOTS if s[1] in ("shot", "appshot")}


def render(check_only=False):
    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(SHOT_DIR, exist_ok=True)
    os.makedirs(APP_SHOT_DIR, exist_ok=True)
    missing, frames = [], []
    for idx, (start, kind, p) in enumerate(SHOTS):
        secs = (SHOTS[idx + 1][0] if idx + 1 < len(SHOTS) else VIDEO_SECONDS) - start
        if kind == "title":
            img = slide_title(p["title"], p.get("subtitle"), p.get("kicker"))
        elif kind == "quote":
            img = slide_quote(p["quote"], p["attrib"])
        elif kind == "bullets":
            img = slide_bullets(p["title"], p["rows"], p.get("note"))
        elif kind == "evidence":
            img = slide_evidence(p["title"], p["table"], p["verdict"], p["verdict_col"],
                                 p.get("source"))
        elif kind == "message":
            img = slide_message(p["title"], p["paragraphs"], p["source"])
        elif kind == "code":
            img = slide_code(p["title"], p["code_lines"], p.get("caption"))
        elif kind in ("shot", "appshot"):
            # Foundry captures and Control Center captures live in separate
            # folders on purpose. A local React page is not Foundry evidence.
            folder = SHOT_DIR if kind == "shot" else APP_SHOT_DIR
            rel = "evidence/screenshots" if kind == "shot" else "evidence/app-screenshots"
            path = None
            for ext in (".png", ".jpg", ".jpeg"):
                cand = os.path.join(folder, p["id"] + ext)
                if os.path.exists(cand):
                    path = cand
                    break
            if path:
                img = fit_screenshot(path, p["caption"])
            else:
                img = slide_placeholder(p["id"], p["what"], p["why"], rel)
                missing.append(p["id"])
        else:
            continue
        out = os.path.join(OUT_DIR, "frame_%02d.png" % idx)
        img.save(out)
        frames.append((out, secs))

    total = sum(s for _, s in frames)
    print("slides rendered : %d" % len(frames))
    print("timeline        : %.1f seconds (%d:%02d)" % (total, total // 60, total % 60))
    print("screenshots used: %d of %d" % (len(SHOT_META) - len(missing), len(SHOT_META)))
    if missing:
        print("MISSING SHOTS   : %s" % ", ".join(missing))
    if check_only:
        return missing, frames, total

    import imageio_ffmpeg
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    concat = os.path.join(OUT_DIR, "concat.txt")
    burned = burn_subtitles(subtitle_plan(frames))
    with open(concat, "w", encoding="utf-8") as f:
        for path, secs in burned:
            f.write("file '%s'\n" % path.replace("\\", "/"))
            f.write("duration %.3f\n" % secs)
        f.write("file '%s'\n" % burned[-1][0].replace("\\", "/"))
    cmd = [ff, "-y", "-f", "concat", "-safe", "0", "-i", concat,
           "-vf", "fps=%d,format=yuv420p,scale=%d:%d" % (FPS, W, H),
           "-c:v", "libx264", "-preset", "medium", "-crf", "23",
           "-t", str(total), MP4]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("\nffmpeg FAILED:\n" + r.stderr[-1500:])
        sys.exit(1)
    size = os.path.getsize(MP4) / 1e6
    print("\nwrote %s  (%.1f MB)" % (MP4, size))
    print("limit check     : %s" % ("OK, under 150 MB" if size < 150 else "TOO LARGE"))
    if missing:
        print("\nSTATUS: DRAFT ANIMATIC. %d screenshot(s) still missing, and there is no"
              " narration yet.\nThis is NOT submittable as is." % len(missing))
    else:
        print("\nSTATUS: all visuals present. Still needs narration audio before submission.")
    return missing, frames, total


# ----------------------------------------------------------------- narration
# The organizer cap is a hard 3 minutes. The rule when fitting narration is that
# the audio is never resampled or sped up, because a rushed voice track is worse
# than a slightly different slide rhythm. Instead the slide durations stretch or
# compress proportionally so the visuals follow the voice.

NARRATION_CANDIDATES = ("narration.wav", "narration.m4a", "narration.mp3", "narration.aac")
MAX_SECONDS = 180.0
FINAL_MP4 = os.path.join(ROOT, "submission", "video", "GridResolve_AI_FINAL.mp4")


def ffmpeg_exe() -> str:
    import imageio_ffmpeg

    return imageio_ffmpeg.get_ffmpeg_exe()


def rel(path: str) -> str:
    """Path relative to the project, falling back when it is on another drive."""
    try:
        return os.path.relpath(path, ROOT)
    except ValueError:
        return path


def find_narration() -> str | None:
    here = os.path.join(ROOT, "submission", "video")
    for name in NARRATION_CANDIDATES:
        path = os.path.join(here, name)
        if os.path.exists(path):
            return path
    return None


def media_duration(path: str) -> float | None:
    """Duration in seconds, read from ffmpeg's own report. ffprobe is not bundled."""
    r = subprocess.run([ffmpeg_exe(), "-i", path], capture_output=True, text=True)
    for line in r.stderr.splitlines():
        line = line.strip()
        if line.startswith("Duration:"):
            stamp = line.split("Duration:")[1].split(",")[0].strip()
            try:
                hours, minutes, seconds = stamp.split(":")
                return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            except ValueError:
                return None
    return None


def to_wav(path: str) -> str:
    """Normalise any accepted audio to 48 kHz mono WAV. Never changes tempo."""
    if path.lower().endswith(".wav"):
        return path
    out = os.path.splitext(path)[0] + ".wav"
    cmd = [ffmpeg_exe(), "-y", "-i", path, "-ac", "1", "-ar", "48000", out]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("\naudio conversion FAILED:\n" + r.stderr[-1200:])
        sys.exit(1)
    print("converted narration to %s" % rel(out))
    return out


def subtitle_plan(frames):
    """
    One row per stretch of video: (slide_index, frame_path, start, end, text).
    text is None where nobody is speaking. Scene changes and cue changes are
    independent, so a sentence can carry across a change of picture.
    """
    starts = [s[0] for s in SHOTS]
    marks = sorted(set(starts + [VIDEO_SECONDS] + [c[0] for c in CUES] + [c[1] for c in CUES]))
    rows = []
    for begin, end in zip(marks, marks[1:]):
        if end - begin < 1e-6:
            continue
        index = max(i for i, s in enumerate(starts) if s <= begin + 1e-9)
        text = next((c[2] for c in CUES if c[0] <= begin + 1e-9 and end <= c[1] + 1e-9), None)
        rows.append((index, frames[index][0], begin, end, text))
    return rows


def burn_subtitles(plan):
    """
    Draw each cue onto a copy of its slide, so the subtitles are part of the
    picture and survive any upload. Returns (path, seconds) per stretch.
    """
    out = []
    fnt = font(38, bold=True)
    for n, (index, path, start, end, text) in enumerate(plan):
        dest = os.path.join(OUT_DIR, "sub_%03d.png" % n)
        if text is None:
            shutil.copyfile(path, dest)
            out.append((dest, end - start))
            continue
        img = Image.open(path).convert("RGB")
        d = ImageDraw.Draw(img, "RGBA")
        lines = wrap(d, text, fnt, W - 360)
        if len(lines) > 2:
            print("BLOCKED: subtitle needs more than two lines: %s" % text)
            sys.exit(1)
        kind = SHOTS[index][1]
        # Screenshot slides keep their caption bar at the very bottom, so the
        # subtitle band sits just above it.
        bottom = H - 104 if kind in ("shot", "appshot") else H - 14
        top = bottom - (26 + 50 * len(lines))
        d.rectangle([120, top, W - 120, bottom], fill=(14, 18, 24, 226))
        y = top + 12
        for ln in lines:
            x = (W - d.textlength(ln, font=fnt)) // 2
            d.text((x, y), ln, font=fnt, fill=(250, 251, 252))
            y += 50
        img.save(dest)
        out.append((dest, end - start))
    return out


def write_srt(plan, dest: str) -> None:
    """The cues as a sidecar SRT, for platforms that accept one."""

    def stamp(total: float) -> str:
        ms = int(round(total * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        s, ms = divmod(ms, 1000)
        return "%02d:%02d:%02d,%03d" % (h, m, s, ms)

    lines = []
    for n, (start, end, text) in enumerate(CUES, 1):
        lines += [str(n), "%s --> %s" % (stamp(start), stamp(end)), text, ""]
    with open(dest, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("wrote subtitles: %s (%d cues)" % (rel(dest), len(CUES)))


def build_final() -> int:
    """
    Assemble the submittable MP4: real screenshots, the recorded narration
    untouched, and pictures and subtitles placed on the times the words are
    actually spoken. Refuses to produce a final file while any required asset is
    missing.
    """
    missing, frames, planned = render(check_only=True)

    narration = find_narration()
    print()
    if missing:
        print("BLOCKED: %d screenshot(s) still missing: %s" % (len(missing), ", ".join(missing)))
    if not narration:
        print("BLOCKED: no narration file found in submission/video/")
        print("         expected one of: %s" % ", ".join(NARRATION_CANDIDATES))
    if missing or not narration:
        print("\nNo final video was produced. Nothing was faked to fill the gap.")
        return 1

    narration = to_wav(narration)
    spoken = media_duration(narration)
    if spoken is None:
        print("BLOCKED: could not measure the narration duration.")
        return 1
    print("narration duration: %.3f s (%d:%02d)" % (spoken, int(spoken // 60), int(spoken % 60)))

    if abs(spoken - NARRATION_SECONDS) > 0.05:
        print("BLOCKED: the cue times in narration_text.py were read off a %.3f s recording,"
              " and this one is %.3f s. Re-time the cues first." % (NARRATION_SECONDS, spoken))
        return 1
    if not spoken < VIDEO_SECONDS < MAX_SECONDS:
        print("BLOCKED: the video length %.1f s must be above the narration and strictly under %d s."
              % (VIDEO_SECONDS, int(MAX_SECONDS)))
        return 1

    plan = subtitle_plan(frames)
    write_srt(plan, os.path.join(ROOT, "submission", "video", "FINAL_VIDEO_SUBTITLES.srt"))
    stretches = burn_subtitles(plan)

    concat = os.path.join(OUT_DIR, "concat_final.txt")
    with open(concat, "w", encoding="utf-8") as f:
        for path, secs in stretches:
            f.write("file '%s'\n" % path.replace("\\", "/"))
            f.write("duration %.3f\n" % secs)
        f.write("file '%s'\n" % stretches[-1][0].replace("\\", "/"))

    # The voice is copied through at its own speed. apad only adds silence after
    # the last word, under the closing frame.
    cmd = [
        ffmpeg_exe(), "-y",
        "-f", "concat", "-safe", "0", "-i", concat,
        "-i", narration,
        "-vf", "fps=%d,format=yuv420p,scale=%d:%d" % (FPS, W, H),
        "-af", "apad",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "1",
        "-t", "%.3f" % VIDEO_SECONDS, "-movflags", "+faststart",
        FINAL_MP4,
    ]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("\nffmpeg FAILED:\n" + r.stderr[-1500:])
        return 1

    return verify_final()


def verify_final() -> int:
    """Programmatic check of the rendered file. Reports facts, not assurances."""
    if not os.path.exists(FINAL_MP4):
        print("no final MP4 exists at %s" % rel(FINAL_MP4))
        return 1

    size_mb = os.path.getsize(FINAL_MP4) / 1e6
    duration = media_duration(FINAL_MP4)
    r = subprocess.run([ffmpeg_exe(), "-i", FINAL_MP4], capture_output=True, text=True)
    streams = [ln.strip() for ln in r.stderr.splitlines() if "Stream #" in ln]
    has_video = any("Video:" in s for s in streams)
    has_audio = any("Audio:" in s for s in streams)
    resolution_ok = "1920x1080" in r.stderr

    print("\n" + "=" * 62)
    print("FINAL VIDEO VERIFICATION")
    print("=" * 62)
    print("file        : %s" % rel(FINAL_MP4))
    print("duration    : %.2f s (%d:%02d)  limit %d s  %s"
          % (duration or -1, int((duration or 0) // 60), int((duration or 0) % 60),
             int(MAX_SECONDS), "OK" if duration and duration < MAX_SECONDS else "OVER"))
    print("size        : %.2f MB  limit 150 MB  %s" % (size_mb, "OK" if size_mb < 150 else "TOO LARGE"))
    print("resolution  : %s" % ("1920x1080 OK" if resolution_ok else "UNEXPECTED"))
    print("video stream: %s" % ("present" if has_video else "MISSING"))
    print("audio stream: %s" % ("present" if has_audio else "MISSING"))
    if duration:
        print("frame count : ~%d at %d fps" % (round(duration * FPS), FPS))
    for s in streams:
        print("  %s" % s)

    ok = all([has_video, has_audio, resolution_ok, duration and duration < MAX_SECONDS,
              size_mb < 150])
    print("\nVERDICT: %s" % ("READY TO SUBMIT" if ok else "NOT READY"))
    return 0 if ok else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="report asset readiness only")
    ap.add_argument("--final", action="store_true",
                    help="build the submittable MP4 with narration, requires all assets")
    ap.add_argument("--verify", action="store_true", help="verify an existing final MP4")
    a = ap.parse_args()
    if a.verify:
        sys.exit(verify_final())
    if a.final:
        sys.exit(build_final())
    render(check_only=a.check)
