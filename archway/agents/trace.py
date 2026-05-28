"""RunTrace — single source of truth for an agent run.

Every agent appends one Step. The Streamlit page reads this to render the
canvas, cards, and replay view. Saved as JSON under data/runs/ for replay.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal

RUNS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "runs"

# Published rates ($ per 1M tokens). Update as providers change pricing.
PRICE_PER_MTOK = {
    # Anthropic
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    # OpenAI
    "gpt-5.4": {"input": 2.50, "output": 15.00},
    "gpt-5.4-mini": {"input": 0.75, "output": 4.50},
    "gpt-5.4-nano": {"input": 0.20, "output": 1.25},
    "gpt-5.5": {"input": 5.00, "output": 30.00},
}

StepStatus = Literal["pending", "running", "done", "failed"]


@dataclass
class Step:
    name: str
    label: str
    why: str  # pedagogical "why this agent exists"
    model: str = ""
    status: StepStatus = "pending"
    system_prompt: str = ""
    user_prompt: str = ""
    response: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    started_at: float | None = None
    ended_at: float | None = None
    error: str | None = None

    @property
    def elapsed_s(self) -> float:
        if self.started_at is None:
            return 0.0
        end = self.ended_at if self.ended_at is not None else time.time()
        return end - self.started_at


@dataclass
class Edge:
    source: str
    target: str
    animated: bool = False  # True while data is flowing


@dataclass
class RunTrace:
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    created_at: float = field(default_factory=time.time)
    steps: list[Step] = field(default_factory=list)
    edges: list[Edge] = field(default_factory=list)
    final_report: str = ""
    verifier_passed: bool | None = None
    verifier_issues: list[str] = field(default_factory=list)

    def step(self, name: str) -> Step:
        for s in self.steps:
            if s.name == name:
                return s
        raise KeyError(name)

    def start(self, name: str) -> Step:
        s = self.step(name)
        s.status = "running"
        s.started_at = time.time()
        for e in self.edges:
            if e.target == name:
                e.animated = True
        return s

    def finish(self, name: str, response: str, input_tokens: int, output_tokens: int) -> Step:
        s = self.step(name)
        s.status = "done"
        s.ended_at = time.time()
        s.response = response
        s.input_tokens = input_tokens
        s.output_tokens = output_tokens
        rates = PRICE_PER_MTOK.get(s.model, {"input": 0.0, "output": 0.0})
        s.cost_usd = (
            input_tokens * rates["input"] / 1_000_000
            + output_tokens * rates["output"] / 1_000_000
        )
        for e in self.edges:
            if e.target == name:
                e.animated = False
        return s

    def fail(self, name: str, error: str) -> Step:
        s = self.step(name)
        s.status = "failed"
        s.ended_at = time.time()
        s.error = error
        for e in self.edges:
            if e.target == name:
                e.animated = False
        return s

    @property
    def total_cost_usd(self) -> float:
        return sum(s.cost_usd for s in self.steps)

    @property
    def total_input_tokens(self) -> int:
        return sum(s.input_tokens for s in self.steps)

    @property
    def total_output_tokens(self) -> int:
        return sum(s.output_tokens for s in self.steps)

    @property
    def total_elapsed_s(self) -> float:
        return sum(s.elapsed_s for s in self.steps)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "created_at": self.created_at,
            "steps": [asdict(s) for s in self.steps],
            "edges": [asdict(e) for e in self.edges],
            "final_report": self.final_report,
            "verifier_passed": self.verifier_passed,
            "verifier_issues": self.verifier_issues,
        }

    def save(self) -> Path:
        RUNS_DIR.mkdir(parents=True, exist_ok=True)
        path = RUNS_DIR / f"{int(self.created_at)}_{self.run_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2))
        return path

    @classmethod
    def load(cls, path: Path) -> "RunTrace":
        data = json.loads(Path(path).read_text())
        trace = cls(
            run_id=data["run_id"],
            created_at=data["created_at"],
            steps=[Step(**s) for s in data["steps"]],
            edges=[Edge(**e) for e in data["edges"]],
            final_report=data.get("final_report", ""),
            verifier_passed=data.get("verifier_passed"),
            verifier_issues=data.get("verifier_issues", []),
        )
        return trace


def new_reporting_trace() -> RunTrace:
    """Build an empty trace for the 4-node reporting pipeline."""
    trace = RunTrace()
    trace.steps = [
        Step(
            name="performance",
            label="Performance Agent",
            why="Reads the fund returns CSV and writes the performance section. Specialist agents keep prompts focused and outputs auditable.",
        ),
        Step(
            name="holdings",
            label="Holdings Agent",
            why="Reads the holdings CSV and writes top contributors / detractors. Splitting from Performance teaches division of labor across agents.",
        ),
        Step(
            name="writer",
            label="Writer Agent",
            why="Stitches the specialist sections into a narrative. A separate writer keeps the specialists factual and the prose consistent in one voice.",
        ),
        Step(
            name="verifier",
            label="Verifier Agent",
            why="LLMs hallucinate numbers. This agent re-reads the source CSVs and checks every figure in the draft. This is the same pattern Anthropic productized as the Managed Agents rubric grader.",
        ),
    ]
    trace.edges = [
        Edge("performance", "writer"),
        Edge("holdings", "writer"),
        Edge("writer", "verifier"),
    ]
    return trace


def list_saved_runs() -> list[Path]:
    if not RUNS_DIR.exists():
        return []
    return sorted(RUNS_DIR.glob("*.json"), reverse=True)
