"""Verifier Agent — re-reads source CSVs and checks every number in the draft."""
from __future__ import annotations

from typing import Callable

from . import holdings as holdings_mod
from . import performance as performance_mod
from . import prompts
from .base import call_agent
from .trace import RunTrace


def run(
    trace: RunTrace,
    draft_report: str,
    on_token: Callable[[str], None] | None = None,
) -> tuple[str, bool, list[str]]:
    returns_df = performance_mod.load_returns()
    holdings_df = holdings_mod.load_holdings()

    user_prompt = (
        "Here is the draft report to verify:\n\n"
        "--- DRAFT ---\n"
        f"{draft_report}\n\n"
        "--- SOURCE: FUND RETURNS (decimals) ---\n"
        f"{performance_mod._format_table(returns_df)}\n\n"
        "--- SOURCE: FUND HOLDINGS ---\n"
        f"{holdings_mod._format_table(holdings_df)}\n\n"
        "Check every numeric claim in the draft against the sources. "
        "End with a single VERDICT line."
    )
    response = call_agent(
        trace,
        step_name="verifier",
        system_prompt=prompts.VERIFIER,
        user_prompt=user_prompt,
        on_token=on_token,
    )
    passed = "VERDICT: PASS" in response.upper()
    issues = [
        line.strip()
        for line in response.splitlines()
        if "FAIL" in line.upper() and "VERDICT" not in line.upper()
    ]
    return response, passed, issues
