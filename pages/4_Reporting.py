"""Reporting Agents — multi-agent flow with live visualization.

Teaching artifact: students see the agent pipeline as a canvas, click any
node to inspect its system prompt + I/O, and watch tokens stream in.

Default model: claude-sonnet-4-6. Requires ANTHROPIC_API_KEY in
.streamlit/secrets.toml (or env). If missing, the page shows a friendly
message and still allows replaying saved runs.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import streamlit as st

from archway.agents import holdings as holdings_agent
from archway.agents import performance as performance_agent
from archway.agents import verifier as verifier_agent
from archway.agents import writer as writer_agent
from archway.agents.base import api_key_available
from archway.agents.trace import (
    RunTrace,
    Step,
    list_saved_runs,
    new_reporting_trace,
)

# --- Page config ------------------------------------------------------------

st.set_page_config(page_title="Reporting · Archway", page_icon="🧠", layout="wide")
st.title("🧠 Reporting Agents")
st.caption(
    "A small multi-agent flow that drafts the monthly fund report. "
    "Specialists write the sections, a Writer stitches them together, "
    "a Verifier re-reads the source data and checks every number."
)

# --- Canvas helpers ---------------------------------------------------------

STATUS_COLOR = {
    "pending": "#cbd5e1",   # slate-300
    "running": "#fbbf24",   # amber-400
    "done":    "#22c55e",   # green-500
    "failed":  "#ef4444",   # red-500
}

STATUS_ICON = {
    "pending": "⚪",
    "running": "🟡",
    "done":    "🟢",
    "failed":  "🔴",
}


def _try_streamlit_flow():
    """Import streamlit-flow-component if installed; else return None."""
    try:
        from streamlit_flow import streamlit_flow  # type: ignore
        from streamlit_flow.elements import (  # type: ignore
            StreamlitFlowEdge,
            StreamlitFlowNode,
        )
        from streamlit_flow.layouts import TreeLayout  # type: ignore
        from streamlit_flow.state import StreamlitFlowState  # type: ignore
        return {
            "streamlit_flow": streamlit_flow,
            "Node": StreamlitFlowNode,
            "Edge": StreamlitFlowEdge,
            "Layout": TreeLayout,
            "State": StreamlitFlowState,
        }
    except Exception:
        return None


def render_canvas(trace: RunTrace, key: str = "canvas") -> None:
    """n8n-style canvas if streamlit-flow is installed, else graphviz fallback."""
    flow = _try_streamlit_flow()
    if flow is None:
        _render_graphviz(trace)
        return

    nodes = []
    for s in trace.steps:
        color = STATUS_COLOR[s.status]
        nodes.append(
            flow["Node"](
                id=s.name,
                pos=(0, 0),
                data={"content": f"**{s.label}**\n\n{STATUS_ICON[s.status]} {s.status}"},
                node_type="default",
                source_position="right",
                target_position="left",
                style={"backgroundColor": color, "color": "#0f172a", "padding": "8px"},
            )
        )
    edges = [
        flow["Edge"](
            id=f"{e.source}->{e.target}",
            source=e.source,
            target=e.target,
            animated=e.animated,
        )
        for e in trace.edges
    ]
    state = flow["State"](nodes=nodes, edges=edges, selected_id=None)
    flow["streamlit_flow"](
        key=key,
        state=state,
        layout=flow["Layout"](direction="right"),
        fit_view=True,
        height=320,
        get_edge_on_click=False,
        get_node_on_click=False,
        show_minimap=False,
        show_controls=True,
        allow_new_edges=False,
        animate_new_edges=True,
        hide_watermark=True,
    )


def _render_graphviz(trace: RunTrace) -> None:
    """Fallback canvas using graphviz (always available)."""
    lines = ['digraph G { rankdir=LR; node [shape=box, style="rounded,filled", fontname="Helvetica"];']
    for s in trace.steps:
        color = STATUS_COLOR[s.status]
        label = f"{s.label}\\n{STATUS_ICON[s.status]} {s.status}"
        lines.append(f'  {s.name} [label="{label}", fillcolor="{color}"];')
    for e in trace.edges:
        style = "bold,dashed" if e.animated else "solid"
        lines.append(f'  {e.source} -> {e.target} [style="{style}"];')
    lines.append("}")
    st.graphviz_chart("\n".join(lines), use_container_width=True)


# --- Metric cards row -------------------------------------------------------

def render_cards(trace: RunTrace) -> None:
    cols = st.columns(len(trace.steps))
    for col, s in zip(cols, trace.steps):
        with col:
            st.markdown(f"**{s.label}** {STATUS_ICON[s.status]}")
            st.caption(s.model or "—")
            mc1, mc2 = st.columns(2)
            mc1.metric("Elapsed", f"{s.elapsed_s:.1f}s")
            mc2.metric("Cost", f"${s.cost_usd:.4f}")
            st.caption(
                f"in: {s.input_tokens:,} tok · out: {s.output_tokens:,} tok"
            )


# --- Step inspector ---------------------------------------------------------

def render_inspector(trace: RunTrace) -> None:
    st.subheader("Agent inspector")
    names = [s.label for s in trace.steps]
    choice = st.selectbox("Select an agent to inspect", names, key="inspector_select")
    step = next(s for s in trace.steps if s.label == choice)

    st.info(f"**Why this agent exists:** {step.why}")

    if step.error:
        st.error(f"Error: {step.error}")

    with st.expander("System prompt", expanded=True):
        st.code(step.system_prompt or "(not run yet)", language="markdown")
    with st.expander("User prompt (input)", expanded=False):
        st.code(step.user_prompt or "(not run yet)", language="markdown")
    with st.expander("Response (output)", expanded=True):
        st.markdown(step.response or "_not run yet_")


# --- Run orchestration ------------------------------------------------------

def execute_run(trace: RunTrace, slow_mo: bool) -> None:
    """Run all four agents in order, refreshing the page state between each."""
    placeholder_canvas = st.empty()
    placeholder_cards = st.empty()
    placeholder_stream = st.empty()

    def repaint():
        with placeholder_canvas.container():
            render_canvas(trace, key=f"canvas_{int(time.time()*1000)}")
        with placeholder_cards.container():
            render_cards(trace)

    streaming_text = {"buf": ""}

    def on_token(text: str):
        streaming_text["buf"] += text
        placeholder_stream.markdown(
            f"**Streaming output:**\n\n{streaming_text['buf']}"
        )

    def before(step_name: str):
        streaming_text["buf"] = ""
        trace.start(step_name)
        repaint()
        if slow_mo:
            time.sleep(0.8)

    def after():
        repaint()
        if slow_mo:
            time.sleep(0.6)

    try:
        # 1. Performance
        before("performance")
        perf = performance_agent.run(trace, on_token=on_token)
        after()

        # 2. Holdings
        before("holdings")
        hold = holdings_agent.run(trace, on_token=on_token)
        after()

        # 3. Writer
        before("writer")
        draft = writer_agent.run(trace, perf, hold, on_token=on_token)
        trace.final_report = draft
        after()

        # 4. Verifier
        before("verifier")
        _, passed, issues = verifier_agent.run(trace, draft, on_token=on_token)
        trace.verifier_passed = passed
        trace.verifier_issues = issues
        after()

        path = trace.save()
        st.session_state["last_saved_run"] = str(path)
    except Exception as e:
        st.error(f"Run failed: {e}")
        repaint()


# --- Sidebar: replay --------------------------------------------------------

with st.sidebar:
    st.header("Saved runs")
    saved = list_saved_runs()
    if saved:
        labels = [p.stem for p in saved]
        pick = st.selectbox("Load a previous run", ["(none)"] + labels, key="replay_pick")
        if pick != "(none)":
            path = next(p for p in saved if p.stem == pick)
            st.session_state["loaded_trace"] = RunTrace.load(path)
            st.success(f"Loaded {pick}")
    else:
        st.caption("No saved runs yet. Generate one to see it here.")

    st.divider()
    st.header("Pipeline controls")
    slow_mo = st.toggle(
        "Slow-mo (teaching mode)",
        value=True,
        help="Pauses briefly between agents so the canvas animation is visible.",
    )

# --- Main: header bar + controls -------------------------------------------

key_ok = api_key_available()

if "trace" not in st.session_state:
    st.session_state["trace"] = new_reporting_trace()

if "loaded_trace" in st.session_state:
    st.session_state["trace"] = st.session_state.pop("loaded_trace")

trace: RunTrace = st.session_state["trace"]

top1, top2, top3, top4 = st.columns([1.5, 1, 1, 1])
with top1:
    if not key_ok:
        st.warning(
            "🔑 No `ANTHROPIC_API_KEY` found. Add it to "
            "`.streamlit/secrets.toml` to generate new runs. You can still "
            "replay saved runs from the sidebar.",
            icon="⚠️",
        )
    run_clicked = st.button(
        "▶ Generate report",
        type="primary",
        disabled=not key_ok,
        use_container_width=True,
    )
    if st.button("Reset", use_container_width=True):
        st.session_state["trace"] = new_reporting_trace()
        st.rerun()
with top2:
    st.metric("Total cost", f"${trace.total_cost_usd:.4f}")
with top3:
    st.metric("Total tokens", f"{trace.total_input_tokens + trace.total_output_tokens:,}")
with top4:
    st.metric("Wall time", f"{trace.total_elapsed_s:.1f}s")

st.divider()

# --- Main: canvas + cards ---------------------------------------------------

st.subheader("Pipeline")
if run_clicked:
    trace = new_reporting_trace()
    st.session_state["trace"] = trace
    execute_run(trace, slow_mo=slow_mo)
else:
    render_canvas(trace, key="canvas_idle")
    render_cards(trace)

st.divider()

# --- Inspector --------------------------------------------------------------

render_inspector(trace)

st.divider()

# --- Final report -----------------------------------------------------------

st.subheader("Final report")
if trace.final_report:
    if trace.verifier_passed is True:
        st.success("Verifier: PASS — every number ties to source.")
    elif trace.verifier_passed is False:
        st.error("Verifier: FAIL — issues below.")
        for issue in trace.verifier_issues:
            st.write(f"- {issue}")

    st.markdown(trace.final_report)

    dl1, dl2 = st.columns(2)
    dl1.download_button(
        "⬇ Download report (.md)",
        trace.final_report,
        file_name=f"archway_report_{trace.run_id}.md",
    )
    dl2.download_button(
        "⬇ Download full trace (.json)",
        json.dumps(trace.to_dict(), indent=2),
        file_name=f"archway_trace_{trace.run_id}.json",
        mime="application/json",
    )
else:
    st.caption("No report yet. Click **Generate report** above.")
