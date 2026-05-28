"""Writer Agent — stitches specialist sections into a single report."""
from __future__ import annotations

from typing import Callable

from . import prompts
from .base import call_agent
from .trace import RunTrace


def run(
    trace: RunTrace,
    performance_section: str,
    holdings_section: str,
    on_token: Callable[[str], None] | None = None,
) -> str:
    user_prompt = (
        "Combine these two sections into the monthly report. Use the "
        "month from the Performance section in the title.\n\n"
        "--- PERFORMANCE SECTION ---\n"
        f"{performance_section}\n\n"
        "--- HOLDINGS SECTION ---\n"
        f"{holdings_section}\n"
    )
    return call_agent(
        trace,
        step_name="writer",
        system_prompt=prompts.WRITER,
        user_prompt=user_prompt,
        on_token=on_token,
    )
