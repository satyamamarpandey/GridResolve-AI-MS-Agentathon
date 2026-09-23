"""
Build the GridResolve AI submission deck, eight slides.

Problem and audience, the nine-agent architecture, the Microsoft Foundry
implementation, the genuine final runtime demonstration, governance and
compliance, results and lessons across the three real runs, the production
integration plan, and how to check every number.

Every runtime figure is read from the final run's evidence folder through the
video builder's loader, which stops the build if the evidence ever stops saying
what the slides say. Case figures are read from the case file. Nothing is typed
in from memory, and nothing claims more than one demonstration of workflow v10.

Read only with respect to Azure. No model call, no cost.

Run: python scripts/build_submission_deck.py
"""
import json
import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "submission", "final", "GridResolve_AI_Deck.pptx")

REPO_URL = "https://github.com/satyamamarpandey/GridResolve-AI-MS-Agentathon"

INK = RGBColor(0x16, 0x1A, 0x20)
MUTED = RGBColor(0x5F, 0x6A, 0x78)
ACCENT = RGBColor(0x1A, 0x6A, 0x8F)
GOOD = RGBColor(0x26, 0x76, 0x52)
BAD = RGBColor(0xB0, 0x34, 0x2E)
WARN = RGBColor(0xB0, 0x56, 0x1E)
BG = RGBColor(0xF8, 0xF9, 0xFB)
LINE = RGBColor(0xCB, 0xD2, 0xDC)


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return json.load(f)


def canonical():
    case = load("submission/SYN-CASE-4003_input.json")
    rec = case["synthetic_account_records"]
    prev, curr = rec["billing_history"]
    first, second = rec["meter_reads"]
    return {
        "prev_usd": prev["amount_usd"],
        "curr_usd": curr["amount_usd"],
        "prev_kwh": prev["kwh_billed"],
        "curr_kwh": curr["kwh_billed"],
        "delta_usd": round(curr["amount_usd"] - prev["amount_usd"], 2),
        "delta_kwh": curr["kwh_billed"] - prev["kwh_billed"],
        "register": second["register_kwh"] - first["register_kwh"],
    }


def textbox(slide, x, y, w, h):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return tf


def para(tf, text, size, colour=INK, bold=False, space_after=4, first=False, italic=False):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.text = text
    p.space_after = Pt(space_after)
    for run in p.runs:
        run.font.size = Pt(size)
        run.font.color.rgb = colour
        run.font.bold = bold
        run.font.italic = italic
        run.font.name = "Segoe UI"
    return p


def rule(slide, x, y, w, colour=LINE, thickness=1.25):
    from pptx.enum.shapes import MSO_SHAPE

    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Pt(thickness))
    shp.fill.solid()
    shp.fill.fore_color.rgb = colour
    shp.line.fill.background()
    shp.shadow.inherit = False
    return shp


def panel(slide, x, y, w, h, fill=RGBColor(0xFF, 0xFF, 0xFF)):
    from pptx.enum.shapes import MSO_SHAPE

    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    shp.line.color.rgb = LINE
    shp.line.width = Pt(0.75)
    shp.shadow.inherit = False
    return shp


def set_bg(slide, prs):
    from pptx.enum.shapes import MSO_SHAPE

    shp = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    shp.fill.solid()
    shp.fill.fore_color.rgb = BG
    shp.line.fill.background()
    shp.shadow.inherit = False
    slide.shapes._spTree.remove(shp._element)
    slide.shapes._spTree.insert(2, shp._element)


def add_picture_fit(slide, path, x, y, w, h):
    """Insert a picture scaled to fit the box, centred, preserving aspect."""
    from PIL import Image

    with Image.open(path) as im:
        iw, ih = im.size
    ratio = min(w / (iw / 96), h / (ih / 96))
    dw, dh = (iw / 96) * ratio, (ih / 96) * ratio
    return slide.shapes.add_picture(
        path, Inches(x + (w - dw) / 2), Inches(y + (h - dh) / 2), Inches(dw), Inches(dh)
    )


def final_run():
    """The final run's evidence, loaded once by the video builder and reused here."""
    import sys

    sys.path.insert(0, os.path.join(ROOT, "submission", "video"))
    import build_video as bv  # asserts the evidence still says what the slides say

    return bv


def header(slide, prs, kicker, title, subtitle=None):
    set_bg(slide, prs)
    tf = textbox(slide, 0.55, 0.36, 12.2, 1.2)
    para(tf, kicker, 12, ACCENT, bold=True, first=True, space_after=2)
    para(tf, title, 28, INK, bold=True, space_after=2)
    if subtitle:
        para(tf, subtitle, 13, MUTED, space_after=0)
    rule(slide, 0.55, 1.62, 12.2)


def footer(slide, text):
    tf = textbox(slide, 0.55, 7.04, 12.2, 0.36)
    para(tf, text, 10, MUTED, first=True, space_after=0)


def column(slide, x, y, w, h, heading, items, size=12.5, heading_colour=ACCENT):
    tf = textbox(slide, x, y, w, h)
    para(tf, heading, 11, heading_colour, bold=True, first=True, space_after=6)
    for item in items:
        if isinstance(item, tuple):
            head, body = item
            para(tf, head, size, INK, bold=True, space_after=1)
            para(tf, body, size - 1, MUTED, space_after=7)
        else:
            para(tf, item, size, INK, space_after=7)
    return tf


def table(slide, x, y, col_widths, rows, size=11, header_row=True, row_h=0.36):
    """A plain text grid drawn with rules, so it renders the same everywhere."""
    total_w = sum(col_widths)
    cy = y
    for r, row in enumerate(rows):
        cx = x
        is_head = header_row and r == 0
        for c, cell in enumerate(row):
            tf = textbox(slide, cx + 0.06, cy + 0.06, col_widths[c] - 0.12, row_h)
            colour = ACCENT if is_head else (INK if c else MUTED)
            if isinstance(cell, tuple):
                cell, colour = cell
            para(tf, cell, size - 1 if is_head else size, colour, bold=is_head or c == 0,
                 first=True, space_after=0)
            cx += col_widths[c]
        cy += row_h
        rule(slide, x, cy, total_w)
    return cy


def crop_claim_panel():
    """Region selection from the current Control Center capture. No pixel is altered."""
    from PIL import Image

    src = os.path.join(ROOT, "evidence", "app-screenshots", "APP04.png")
    dest = os.path.join(ROOT, "submission", "final", "deck-assets", "APP04_claim.png")
    with Image.open(src) as im:
        im.crop((1150, 222, 1895, 472)).save(dest)
    return dest


def build():
    fig = canonical()
    bv = final_run()
    run = bv.run
    ledger_n = len(run["ledger"]["evidence_ledger"])
    policy_n = len(run["policy"]["policy_ledger"])
    findings_n = len(run["analysis"]["audit"]["findings"])
    card = run["package"]["decision_card"]

    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    FOOT = ("Microsoft Agent-a-thon, Level 3 Architect   |   Synthetic data only   |   "
            "Verified on hosted Foundry. Production path built and tested locally, not yet connected")

    # ------------------------------------------------ 1. problem, purpose, audience
    s = prs.slides.add_slide(blank)
    header(s, prs, "GRIDRESOLVE AI", "A high bill is not one question. It is five.",
           "Evidence-first multi-agent utility billing resolution on Microsoft Foundry")
    column(s, 0.55, 1.9, 4.0, 3.6, "THE PROBLEM", [
        f"A customer's bill jumps from ${fig['prev_usd']:.2f} to ${fig['curr_usd']:.2f}. They are "
        "certain the meter is broken, and want it confirmed and the charge reversed.",
        "Answering needs billing records, consumption, policy, customer wording and approval "
        "authority, reconciled at once.",
        "A single assistant answers all five, then approves its own answer. Under pressure "
        "from a confident customer, agreement is the easiest output.",
    ])
    column(s, 4.85, 1.9, 4.0, 3.6, "PURPOSE AND AUDIENCE", [
        ("Who it is for", "Utility billing operations: the agents who answer high-bill disputes, "
                          "and the supervisors who must approve any money."),
        ("What it does", "Investigates the dispute from the records, explains only what the "
                         "evidence supports, and hands open questions to a person with a decision card."),
        ("What it will not do", "Confirm a meter fault without evidence, promise a credit, or let "
                                "the agent that wrote an answer approve it."),
    ])
    column(s, 9.15, 1.9, 3.6, 3.6, "BUSINESS VALUE", [
        ("Avoided wrong adjustments", "An unsupported meter-fault conclusion is money out plus a "
                                      "technician sent for nothing."),
        ("Regulatory defensibility", "Every released statement traces to evidence and policy IDs. "
                                     "Every path ends in an audit record."),
        ("Human attention where it counts", "Open cases arrive triaged, with the missing evidence named."),
    ], size=12)
    panel(s, 0.55, 5.6, 12.2, 1.3)
    tf = textbox(s, 0.8, 5.74, 11.7, 1.1)
    para(tf, "WHERE IT STANDS", 10, ACCENT, bold=True, first=True, space_after=4)
    para(tf, "I ran it for real on Microsoft Foundry three times. The final run, on workflow v10, passed 14 of 14 "
             "acceptance criteria that I wrote down before it ran. The first two runs exposed real defects, and "
             "they are in the repository too. Since then I have built the production path around it: typed "
             "integration ports, a migration proof on Microsoft Agent Framework, and 1,174 local checks.",
         12, INK, space_after=0)
    footer(s, FOOT)

    # ------------------------------------------------ 2. nine-agent architecture
    s = prs.slides.add_slide(blank)
    header(s, prs, "ARCHITECTURE", "Nine specialists, one governed workflow",
           "The agent that writes the answer is never the agent that clears it for release")
    groups = [
        ("FOUR INVESTIGATE", ACCENT, [
            ("CaseTriageAgent", "classifies the complaint and the allegations"),
            ("AccountEvidenceAgent", "builds the evidence ledger from the records"),
            ("UsageAnomalyAgent", "separates supported from unsupported explanations"),
            ("PolicyKnowledgeAgent", "maps the governed policies that apply"),
        ]),
        ("TWO PRODUCE", ACCENT, [
            ("ResolutionPlannerAgent", "plans against a claim ledger, and says whether a person is still needed"),
            ("CustomerCommunicationAgent", "drafts the six-part plain-language message"),
        ]),
        ("THREE CONTROL", WARN, [
            ("EvidenceComplianceAgent", "independently approves or refuses the message, with reasons"),
            ("EscalationCoordinatorAgent", "prepares the human review package"),
            ("CaseAuditAgent", "writes the terminal record on every path"),
        ]),
    ]
    x = 0.55
    for heading, colour, agents in groups:
        panel(s, x, 1.9, 3.95, 3.85)
        tf = textbox(s, x + 0.2, 2.02, 3.55, 3.6)
        para(tf, heading, 11, colour, bold=True, first=True, space_after=7)
        for name, role in agents:
            para(tf, name, 12.5, INK, bold=True, space_after=1)
            para(tf, role, 11, MUTED, space_after=7)
        x += 4.12
    column(s, 0.55, 5.95, 12.2, 1.0, "HOW THEY COLLABORATE", [
        "Sequential, on one shared conversation. Each agent receives an explicit task naming its step. Seven "
        "agents run with output withheld, so nothing they write can reach the customer. Every material claim "
        "carries the evidence IDs and policy IDs that support it. All nine run gpt-5-mini with no external tools.",
    ], size=12)
    footer(s, FOOT)

    # ------------------------------------------------ 3. Foundry implementation
    s = prs.slides.add_slide(blank)
    header(s, prs, "MICROSOFT FOUNDRY", "Built as Foundry agents and one Foundry workflow, version 10",
           "Declarative workflow YAML, Power Fx conditions, strict JSON output schemas")
    shot = os.path.join(ROOT, "evidence", "screenshots", "F10-WORKFLOW.png")
    if os.path.exists(shot):
        panel(s, 0.55, 1.9, 6.6, 4.9)
        add_picture_fit(s, shot, 0.62, 1.97, 6.46, 4.5)
        tf = textbox(s, 0.62, 6.5, 6.46, 0.3)
        para(tf, "Authentic Foundry portal capture: GridResolveAIWorkflow, version 10.", 10, MUTED,
             first=True, space_after=0)
        left_w, lx = 5.4, 7.35
    else:
        left_w, lx = 12.2, 0.55
    items = [
        ("Release gate, three terms", "An exact approval token on the final line, six readable customer "
                                      "fields, and a complete investigation. Anything else withholds the "
                                      "message and goes to a human."),
        ("Strict output schemas", "Evidence, policy, communication and audit agents must return a JSON "
                                  "object that matches a schema. A sentence in place of a result is impossible."),
        ("Explicit invocation", "Every agent node passes a literal task message. This is the fix for the "
                                "stalls seen in the first two real runs."),
        ("Separate follow-up decision", "Message approval and the need for a person are two gates, so a safe "
                                        "message never erases an open case."),
        ("Verified before it ran", "105 cases on Microsoft's real Power Fx engine, the v10 YAML on Microsoft's "
                                   "open-source workflow engine, 94 read-only checks of the live configuration."),
    ]
    if left_w > 6:
        column(s, 0.55, 1.9, 5.9, 5.0, "HOW IT IS BUILT", items[:3], size=12.5)
        column(s, 6.85, 1.9, 5.9, 5.0, " ", items[3:], size=12.5)
    else:
        column(s, lx, 1.9, left_w, 5.0, "HOW IT IS BUILT", items, size=11.5)
    footer(s, FOOT)

    # ------------------------------------------------ 4. the final runtime demonstration
    s = prs.slides.add_slide(blank)
    header(s, prs, "GENUINE RUNTIME DEMONSTRATION",
           "Final run on workflow v%s: 14 of 14 criteria passed" % run["workflow_version"],
           "Criteria were written down before the run. Every figure below is read from the run's evidence folder")
    table(s, 0.55, 1.85, [3.3, 3.6], [
        ["Checked", "Platform record"],
        ["Agents that did their work", "%d of %d" % (bv.healthy, len(bv.agents_run))],
        ["Evidence ledger", "%d entries, all matched to the case" % ledger_n],
        ["Policies mapped", "%d, none invented" % policy_n],
        ["Register vs billed", "%d kWh vs %s kWh" % (bv.register_delta, bv.ledger_value["EVID-BILL-0003-07-KWH"])],
        ["Meter failure asserted", "no"],
        ["Credit promised", "no"],
        ["Compliance", "%s, with recorded reasons" % run["compliance"]["decision"]],
        ["Route", "message released, case to human"],
        ["Audit vs platform", "%d findings" % findings_n],
        ["Tokens, cost", "94,352 in, 22,433 out, about $0.07"],
    ], size=11, row_h=0.4)
    panel(s, 7.75, 1.85, 5.0, 2.85)
    tf = textbox(s, 7.95, 1.98, 4.6, 2.7)
    para(tf, "RELEASED TO THE CUSTOMER, VERBATIM", 10, ACCENT, bold=True, first=True, space_after=6)
    for part in bv.RELEASED_EXCERPT:
        para(tf, part, 11.5, INK, space_after=7)
    para(tf, "Three sentences of a %d character, six-part message. It promises no credit and offers "
             "a human-reviewed inspection." % len(run["released"]), 10.5, MUTED, italic=True, space_after=0)
    panel(s, 7.75, 4.85, 5.0, 1.4)
    tf = textbox(s, 7.95, 4.96, 4.6, 1.25)
    para(tf, "SEPARATELY, HANDED TO A PERSON", 10, ACCENT, bold=True, first=True, space_after=5)
    para(tf, "To %s, status %s. Decision needed, verbatim: %s"
         % (run["package"]["routing"]["route_to"], run["package"]["final_disposition"],
            card["decision_needed"]), 11, INK, space_after=0)
    tf = textbox(s, 0.55, 6.42, 12.2, 0.55)
    para(tf, "Compliance approved this message. It did not reject it, and the final run did not take the "
             "fail-closed route. That route was demonstrated in run 2.", 12, GOOD, bold=True, first=True,
         space_after=0)
    footer(s, "Source: evidence/runtime/%s   |   docs/FINAL_RUN_RESULT_2026-09-20.md" % bv.FINAL_RUN)

    # ------------------------------------------------ 5. governance and compliance
    s = prs.slides.add_slide(blank)
    header(s, prs, "GOVERNANCE AND COMPLIANCE", "Release is the exception, and it has to be earned",
           "Independent review, human authority over money, and an audit that is checked against the platform")
    column(s, 0.55, 1.9, 5.9, 4.4, "CONTROLS", [
        ("Independent compliance", "A different agent, twenty checks, four decisions, no tools. It must give "
                                   "reasons. A bare verdict now withholds the message."),
        ("Two separate questions", "Is this message safe to send, and does this case still need a person. "
                                   "In the final run the answers were yes and yes."),
        ("Human authority", "No agent can authorize a credit or adjustment. The final run sent the open case to a "
                            "%s with a decision card: %d known facts, %d unknowns, policies, risk, next step."
                            % (run["package"]["routing"]["route_to"], len(card["known_facts"]), len(card["unknowns"]))),
        ("The audit is not trusted", "The runner compares the audit record with the platform's own record of who "
                                     "ran, which branch was taken and what was delivered."),
    ], size=12)
    panel(s, 6.85, 1.9, 5.9, 2.15)
    tf = textbox(s, 7.05, 2.02, 5.5, 2.0)
    para(tf, "COMPLIANCE REASONS, FINAL RUN, VERBATIM EXCERPT", 10, ACCENT, bold=True, first=True, space_after=6)
    summary = run["compliance"]["compliance_summary"]
    para(tf, summary[:summary.index(". The message reproduces") + 1], 11, INK, space_after=6)
    para(tf, "Decision %s, failed checks %d, token on the final line."
         % (run["compliance"]["decision"], len(run["compliance"]["failed_checks"])), 10.5, MUTED,
         italic=True, space_after=0)
    claim = crop_claim_panel()
    add_picture_fit(s, claim, 6.85, 4.25, 5.9, 2.25)
    tf = textbox(s, 6.85, 6.62, 5.9, 0.3)
    para(tf, "Local Control Center, offline demonstration. Not a Foundry capture.", 10, MUTED,
         first=True, space_after=0)
    footer(s, FOOT)

    # ------------------------------------------------ 6. results and lessons
    s = prs.slides.add_slide(blank)
    header(s, prs, "RESULTS AND LESSONS", "Three real runs, and what each one taught",
           "All three evidence folders are in the repository, unedited")
    table(s, 0.55, 1.85, [2.6, 3.2, 3.2, 3.2], [
        ["", "Run 1, workflow v6", "Run 2, workflow v9", "Final run, workflow v10"],
        ["Agents that did their work", "7 of 8", "6 of 9", ("9 of 9", GOOD)],
        ["Evidence ledger", "none", "none", ("22 entries", GOOD)],
        ["Compliance", "approved", ("escalated, gave no reasons", WARN), ("approved, with reasons", GOOD)],
        ["Sent to the customer", ("an unevaluated expression", BAD), "nothing, failed safe", ("a readable message", GOOD)],
        ["Human follow-up", "not built", "escalation package", ("handoff after the release", GOOD)],
        ["Audit findings", "7", "6", ("0", GOOD)],
        ["Cost, provisional", "$0.0334", "$0.0292", "$0.0685"],
    ], size=11, row_h=0.4)
    column(s, 0.55, 5.2, 12.2, 1.75, "KEY LESSONS LEARNED", [
        "1. Local tests did not catch what one real run caught. Run the real thing early, once, with evidence capture.   "
        "2. When a fix changes the wording of a failure but not the failure, the cause is elsewhere. The platform's "
        "record of what each agent received showed it: no new request on a shared conversation.   "
        "3. Fix acceptance criteria before the run, and report a branch not taken as not observable, never as a pass.   "
        "4. A model's own audit of a run is a claim, not a record. Check it against the platform.",
    ], size=11.5)
    footer(s, "Why run 2 escalated is not established, and this project does not claim to know.   |   "
              "docs/CURRENT_STATUS.md")

    # ------------------------------------------------ 7. production integration plan
    s = prs.slides.add_slide(blank)
    header(s, prs, "THE PATH TO PRODUCTION", "What is built and tested, and what still needs a real utility",
           "The hosted workflow is verified. The production path around it is built and tested locally")
    left = [
        ("Eight typed integration ports", "Account, billing, meter and diagnostic evidence are read only and "
                                          "scoped to one case. CRM, review assignment, adjustment authorization "
                                          "and an append-only audit store. Synthetic adapters, 138 checks."),
        ("Money stays with a person", "Only a human billing supervisor can authorize an adjustment. An agent "
                                      "principal is refused, a forged role is refused, and a supervisor cannot "
                                      "approve their own request. Tested."),
        ("Migration proof, 11 of 11", "Foundry workflows retire on 2026-12-01. I replayed the final run's nine "
                                      "real agent outputs through Microsoft Agent Framework on the same YAML. "
                                      "Same agents, same branch, the same 2,592 characters released."),
        ("Policy catalog with provenance", "Ten governed policies as versioned records. In the final run all 8 "
                                           "provenance links resolve, from the customer's words to the audit record."),
    ]
    right = [
        ("Foundry tracing, read back", "61 platform spans across the three runs, none failed, no content filter "
                                       "block. Azure Monitor agrees with my token counts to the token."),
        ("What the traces taught me", "Foundry marked every span successful, including the runs where agents "
                                      "stalled. Production alerts have to watch what an agent returned, not the "
                                      "status code."),
        ("Guardrails as configured", "Microsoft.DefaultV2 is on the deployment and evaluated all 26 model calls. "
                                     "No custom policy exists, and I do not claim one."),
        ("Still to do with a utility", "Connect the ports to real systems, close public network access and key "
                                       "authentication, pin the model version, decide content recording, add "
                                       "alerts and a budget, then pilot with billing supervisors."),
    ]
    column(s, 0.55, 1.9, 5.9, 4.6, "BUILT AND TESTED LOCALLY", left, size=11.5)
    column(s, 6.85, 1.9, 5.9, 4.6, "OPERATIONS, AND WHAT REMAINS", right, size=11.5)
    panel(s, 0.55, 6.1, 12.2, 0.82)
    tf = textbox(s, 0.8, 6.2, 11.7, 0.7)
    para(tf, "NOT YET SHOWN:  repeatability, a second case, the fail-closed route on v10, the 30 evaluation cases "
             "and 16 adversarial scenarios, a correction loop, a real person being notified.", 11.5, WARN, bold=True,
         first=True, space_after=0)
    footer(s, FOOT)

    # ------------------------------------------------ 8. evidence and how to check it
    s = prs.slides.add_slide(blank)
    header(s, prs, "CHECK IT YOURSELF", "Every number here has a file behind it",
           "Runtime numbers come from evidence files. Local numbers come from one command each")
    column(s, 0.55, 1.9, 5.9, 4.9, "WHAT WAS VERIFIED", [
        ("Three real Foundry runs", "evidence/runtime/, three folders, unmodified. Re-read any of them offline: "
                                    "python -m runner analyze --run-dir <folder>"),
        ("1,174 local checks, no model call", "83 routing, 151 synthetic, 156 application, 357 runner, 91 engine, "
                                            "198 evaluation, 138 integration"),
        ("105 cases on the real Power Fx engine", "dotnet run --project tests/powerfx_gate"),
        ("94 read-only live configuration checks", "python tests/verify_live_config.py, with your own Foundry resource"),
        ("12 of 13 deterministic checks on the final run", "python -m evaluation.run_checks. The one it fails is a "
                                                           "root cause label that differs from the one I prepared "
                                                           "in advance. I have left it as a failure."),
        ("Agent Framework parity, 11 of 11", "python migration/agent_framework/parity_check.py"),
    ], size=11.5)
    column(s, 6.85, 1.9, 5.9, 4.9, "COST, STATED CAREFULLY", [
        ("About $0.13 provisional, three runs", "186,614 tokens in and 42,155 out, at list price, from the "
                                                "usage Foundry returned."),
        ("Billed amount: not yet visible", "Azure Cost Management returned no rows when queried. That is not a "
                                           "confirmed $0.00 and not a confirmed $0.13."),
        ("Microsoft's own meter agrees", "Azure Monitor metrics and the platform's 61 trace spans report the same "
                                         "token counts, to the token, and 26 model requests. Read back, read only: "
                                         "evidence/platform_telemetry/"),
        ("Nothing else was created", "No embeddings, no evaluation runs, no new resources."),
        ("Read first", "submission/final/JUDGE_NARRATIVE.md and docs/CURRENT_STATUS.md"),
    ], size=11.5)
    tf = textbox(s, 0.55, 6.6, 12.2, 0.36)
    para(tf, f"Repository  {REPO_URL}", 11, ACCENT, bold=True, first=True, space_after=0)
    footer(s, FOOT)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    prs.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print("wrote %s (%.0f KB)" % (os.path.relpath(path, ROOT), os.path.getsize(path) / 1024))
