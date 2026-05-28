"""Holdings Agent — writes the holdings section from fund_holdings.csv."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd

from . import prompts
from .base import call_agent
from .trace import RunTrace

HOLDINGS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "fund_holdings.csv"


def load_holdings() -> pd.DataFrame:
    df = pd.read_csv(HOLDINGS_PATH)
    df["unrealized_pnl"] = df["shares"] * (df["current_price"] - df["cost_basis"])
    df["return_pct"] = (df["current_price"] / df["cost_basis"] - 1) * 100
    return df


def _format_table(df: pd.DataFrame) -> str:
    cols = ["ticker", "sector", "shares", "cost_basis", "current_price", "unrealized_pnl", "return_pct"]
    lines = [",".join(cols)]
    for _, row in df.iterrows():
        lines.append(
            f"{row['ticker']},{row['sector']},{row['shares']},"
            f"{row['cost_basis']:.2f},{row['current_price']:.2f},"
            f"{row['unrealized_pnl']:.2f},{row['return_pct']:.2f}"
        )
    return "\n".join(lines)


def run(trace: RunTrace, on_token: Callable[[str], None] | None = None) -> str:
    df = load_holdings()
    user_prompt = (
        "Here is the fund holdings table. unrealized_pnl is in dollars; "
        "return_pct is in percent.\n\n"
        f"{_format_table(df)}\n\n"
        "Write the Holdings section."
    )
    return call_agent(
        trace,
        step_name="holdings",
        system_prompt=prompts.HOLDINGS,
        user_prompt=user_prompt,
        on_token=on_token,
    )
