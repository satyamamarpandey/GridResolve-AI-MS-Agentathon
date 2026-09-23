"""Loading and validating the synthetic case that the runner may send.

Two rules are enforced here rather than trusted:

1. Only synthetic data is ever sent. A case that is not marked SYNTHETIC_ONLY,
   or whose identifiers do not follow the SYN- convention, is refused.
2. The expected answer is never sent. The workflow has to reach its conclusion
   from the records alone, so a payload containing anything that looks like the
   graded outcome is refused before the request is built.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Final

ROOT: Final = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

CASES: Final = {
    "SYN-CASE-4003": os.path.join("submission", "SYN-CASE-4003_input.json"),
    # Added 2026-09-23 for the post-review validation. Neither has been sent to
    # the hosted service. 4001 is the no-follow-up candidate, 4007 the
    # conflicting-records escalation candidate. See docs/SCENARIO_*_ACCEPTANCE_PLAN.md.
    "SYN-CASE-4001": os.path.join("submission", "SYN-CASE-4001_input.json"),
    "SYN-CASE-4007": os.path.join("submission", "SYN-CASE-4007_input.json"),
}

# The preflight requires the case to declare the workflow version it targets.
# The canonical SYN-CASE-4003 file is frozen at v10, so a v11 run of the same
# records uses a copy that differs only in that label. Resolved by the active
# workflow version (runner/workflow_versions.py); v10 behaviour is unchanged.
CASES_BY_VERSION: Final = {
    "SYN-CASE-4003": {
        "11": os.path.join("submission", "SYN-CASE-4003_v11_input.json"),
    },
}

# Substrings that would hand the workflow its own grading key.
LEAK_MARKERS: Final = ("expected", "must_not", "no_supported_root_cause",
                       "ground_truth", "correct_answer", "escalate_to_human")

# A blocklist alone fails open: an answer stored under a key nobody thought to
# list would be sent. So the shape of the payload is fixed instead. These are
# exactly the fields of the canonical case, and anything else is refused.
ALLOWED_TOP_LEVEL: Final = frozenset({
    "case_id", "workflow_version", "dataset_version", "policy_version",
    "data_classification", "customer_request", "synthetic_account_records"})
ALLOWED_RECORD_FIELDS: Final = frozenset({
    "account_id", "meter_id", "service_type", "rate_components",
    "billing_history", "meter_reads", "meter_events", "meter_event_note",
    "diagnostic_records", "usage_history_kwh", "adjustments", "prior_contacts"})

_CASE_ID = re.compile(r"^SYN-CASE-\d{4}$")


class CaseError(ValueError):
    """The case cannot be loaded or is not safe to send."""


@dataclass(frozen=True)
class CaseInput:
    """An immutable, validated case ready to be sent verbatim."""

    case_id: str
    path: str
    raw_text: str
    document: dict

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.raw_text.encode("utf-8")).hexdigest()

    @property
    def approx_tokens(self) -> int:
        """Rough size of the operator-supplied input, for the preflight only.

        Four characters per token is a coarse approximation and is labelled as
        such wherever it is printed. It is not used to compute a billed amount.
        """
        return max(1, len(self.raw_text) // 4)


def available_cases() -> tuple[str, ...]:
    return tuple(sorted(CASES))


def canonical_text(raw: bytes) -> str:
    """The payload as it is hashed and sent: UTF-8, no BOM, LF line endings.

    Git on Windows may check the file out with CRLF endings, and an editor may
    add a byte-order mark. Neither is part of the case. Normalising here, in one
    explicit place, means the sha256 and the transmitted text are the same on
    every machine, whatever the working copy looks like on disk.
    """
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise CaseError("Case file is not valid UTF-8: %s" % exc) from exc
    return text.replace("\r\n", "\n").replace("\r", "\n")


def load(case_id: str, root: str = ROOT) -> CaseInput:
    """Load and validate a case. Raises CaseError with a specific reason."""
    if case_id not in CASES:
        raise CaseError("Unknown case %r. Supported: %s"
                        % (case_id, ", ".join(available_cases())))
    from . import workflow_versions as wv  # local import, avoids a cycle
    relative = CASES_BY_VERSION.get(case_id, {}).get(wv.active_version(),
                                                     CASES[case_id])
    path = os.path.join(root, relative)
    if not os.path.isfile(path):
        raise CaseError("Case file not found: %s" % path)
    with open(path, "rb") as fh:
        raw_text = canonical_text(fh.read())
    try:
        document = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise CaseError("Case file is not valid JSON: %s" % exc) from exc
    if not isinstance(document, dict):
        raise CaseError("Case file must contain a JSON object")

    case = CaseInput(case_id=case_id, path=path, raw_text=raw_text,
                     document=document)
    _validate(case)
    return case


def _validate(case: CaseInput) -> None:
    doc = case.document
    declared = doc.get("case_id")
    if declared != case.case_id:
        raise CaseError("Case file declares case_id %r, expected %r"
                        % (declared, case.case_id))
    if not _CASE_ID.match(str(declared)):
        raise CaseError("case_id %r does not follow the SYN-CASE-NNNN pattern"
                        % declared)
    if doc.get("data_classification") != "SYNTHETIC_ONLY":
        raise CaseError(
            "Refusing to send: data_classification is %r, not SYNTHETIC_ONLY. "
            "The runner sends synthetic data only."
            % doc.get("data_classification"))
    records = doc.get("synthetic_account_records")
    if not isinstance(records, dict):
        raise CaseError("synthetic_account_records is missing")
    for label, present, allowed in (
            ("top level", set(doc), ALLOWED_TOP_LEVEL),
            ("synthetic_account_records", set(records), ALLOWED_RECORD_FIELDS)):
        unexpected = sorted(present - allowed)
        if unexpected:
            raise CaseError(
                "Refusing to send: unexpected %s field(s) %s. Only the fields of "
                "the canonical case may be sent, so that nothing resembling an "
                "expected answer can travel under an unlisted name."
                % (label, ", ".join(unexpected)))
    for field in ("account_id", "meter_id"):
        value = str(records.get(field, ""))
        if not value.startswith("SYN-"):
            raise CaseError("%s %r is not a SYN- synthetic identifier"
                            % (field, value))
    found = leak_markers(case.raw_text)
    if found:
        raise CaseError(
            "Refusing to send: the payload contains %s, which would give the "
            "workflow its own expected answer." % ", ".join(repr(f) for f in found))


def leak_markers(text: str) -> tuple[str, ...]:
    """Expected-answer markers present in the payload, if any."""
    folded = text.casefold()
    return tuple(m for m in LEAK_MARKERS if m in folded)


def build_input(case: CaseInput) -> str:
    """The exact text sent to the workflow.

    The canonical case file is sent verbatim. Nothing is added, reworded or
    summarised, so the sha256 above identifies precisely what was transmitted
    and the run stays reproducible.
    """
    return case.raw_text
