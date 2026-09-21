"""Cost estimation and post-run cost reporting.

Prices are constants, not a live lookup. They were verified against the Azure
Retail Prices API on 2026-09-18 and recorded in
docs/COST_ESTIMATE_SYN-CASE-4003.md. A re-check on 2026-09-20 returned no rows
for gpt-5-mini, so the figure could not be independently reconfirmed that day.
The runner therefore states its price source on every estimate rather than
presenting the number as if it were live.

Reasoning tokens bill as output tokens.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Final

USD_PER_1M_INPUT: Final = 0.25
USD_PER_1M_CACHED_INPUT: Final = 0.025
USD_PER_1M_OUTPUT: Final = 2.00

PRICE_SOURCE: Final = (
    "gpt-5-mini GlobalStandard, USD per 1M tokens: input 0.25, cached input "
    "0.025, output 2.00. Verified against the Azure Retail Prices API on "
    "2026-09-18. A re-check on 2026-09-20 returned no rows, so this figure is "
    "carried forward from that verification and is not a live quote.")


def cost_usd(input_tokens: int, output_tokens: int,
             cached_input_tokens: int = 0) -> float:
    """Cost of one run. Cached input is billed at the cached rate, not twice."""
    for name, value in (("input_tokens", input_tokens),
                        ("output_tokens", output_tokens),
                        ("cached_input_tokens", cached_input_tokens)):
        if not isinstance(value, int) or value < 0:
            raise ValueError("%s must be a non-negative integer, got %r"
                             % (name, value))
    if cached_input_tokens > input_tokens:
        raise ValueError("cached_input_tokens cannot exceed input_tokens")
    fresh_input = input_tokens - cached_input_tokens
    total = (fresh_input / 1e6 * USD_PER_1M_INPUT
             + cached_input_tokens / 1e6 * USD_PER_1M_CACHED_INPUT
             + output_tokens / 1e6 * USD_PER_1M_OUTPUT)
    return round(total, 6)


@dataclass(frozen=True)
class Scenario:
    """One pre-execution estimate. Assumed token counts, never measured."""

    name: str
    input_tokens: int
    output_tokens: int
    basis: str

    @property
    def usd(self) -> float:
        return cost_usd(self.input_tokens, self.output_tokens)


# Carried from docs/COST_ESTIMATE_SYN-CASE-4003.md. All nine agents share one
# conversation, so each re-reads every earlier agent's output and input grows
# roughly quadratically along the chain.
SCENARIOS: Final = (
    Scenario("expected", 105_000, 32_000,
             "2.5k visible plus 1k reasoning tokens per agent"),
    Scenario("conservative", 250_000, 100_000,
             "5k visible plus 3k reasoning tokens per agent"),
    Scenario("worst_case", 180_000, 144_000,
             "earlier flat-model maximum, retained as an upper bound"),
)


def worst_case_usd() -> float:
    """The figure a spending cap must be compared against."""
    return max(s.usd for s in SCENARIOS)


@dataclass(frozen=True)
class Usage:
    """Token usage actually reported by the API for one run."""

    input_tokens: int
    output_tokens: int
    total_tokens: int
    cached_input_tokens: int = 0
    reported: bool = True

    @property
    def usd(self) -> float:
        return cost_usd(self.input_tokens, self.output_tokens,
                        self.cached_input_tokens)


UNREPORTED: Final = Usage(0, 0, 0, 0, reported=False)


def usage_from_response(response: dict) -> Usage:
    """Read the usage block if the API returned one.

    The API reference documents input_tokens, output_tokens and total_tokens on
    the response object. Whether a workflow agent aggregates usage across its
    nine inner agent calls is not documented and has never been observed here,
    so a missing or partial block is reported as unmeasured rather than as zero.
    """
    raw = response.get("usage")
    if not isinstance(raw, dict):
        return UNREPORTED
    inp = raw.get("input_tokens")
    out = raw.get("output_tokens")
    if not isinstance(inp, int) or not isinstance(out, int):
        return UNREPORTED
    details = raw.get("input_tokens_details")
    cached = 0
    if isinstance(details, dict) and isinstance(details.get("cached_tokens"), int):
        cached = min(details["cached_tokens"], inp)
    total = raw.get("total_tokens")
    if not isinstance(total, int):
        total = inp + out
    return Usage(input_tokens=inp, output_tokens=out, total_tokens=total,
                 cached_input_tokens=cached)
