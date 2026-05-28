"""Performance Agent — writes the performance section from fund_returns.csv."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd

from . import prompts
from .base import call_agent
from .trace import RunTrace

RETURNS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "fund_returns.csv"


def load_returns() -> pd.DataFrame:
    return pd.read_csv(RETURNS_PATH)


def _format_table(df: pd.DataFrame) -> str:
    lines = ["month,fund_return,benchmark_return"]
    for _, row in df.iterrows():
        lines.append(f"{row['month']},{row['fund_return']:.4f},{row['benchmark_return']:.4f}")
    return "\n".join(lines)


def run(trace: RunTrace, on_token: Callable[[str], None] | None = None) -> str:
    df = load_returns()
    user_prompt = (
        "Here is the fund returns table (decimals, not percentages):\n\n"
        f"{_format_table(df)}\n\n"
        f"The latest month is {df.iloc[-1]['month']}. "
        "Write the Performance section."
    )
    return call_agent(
        trace,
        step_name="performance",
        system_prompt=prompts.PERFORMANCE,
        user_prompt=user_prompt,
        on_token=on_token,
    )
