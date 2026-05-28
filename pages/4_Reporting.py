"""Reporting Agents — multi-agent flow with live visualization.

Teaching artifact: students see the pipeline as a canvas, inspect any
agent's system prompt + I/O via tabs, and watch tokens stream in.

Default Anthropic Sonnet 4.6 for Performance/Holdings/Verifier; OpenAI
gpt-5.4-mini for the Writer. Keys read from .streamlit/secrets.toml.
"""
from __future__ import annotations

import html
import json
import time

import streamlit as st

from archway.agents import holdings as holdings_agent
from archway.agents import performance as performance_agent
from archway.agents import verifier as verifier_agent
from archway.agents import writer as writer_agent
from archway.agents.base import DEFAULT_MODEL, WRITER_MODEL, missing_keys
from archway.agents.trace import (
    RunTrace,
    Step,
    list_saved_runs,
    new_reporting_trace,
)

st.set_page_config(page_title="Reporting · Archway", page_icon="🧠", layout="wide")

# --- Theme tokens -----------------------------------------------------------

PROVIDER_FOR_NODE = {
    "performance": "Anthropic",
    "holdings": "Anthropic",
    "writer": "OpenAI",
    "verifier": "Anthropic",
}

# Subtle pastel fills, saturated borders. Same hue per status so it reads at a glance.
STATUS = {
    "pending": {"fill": "#f1f5f9", "border": "#cbd5e1", "text": "#475569", "label": "Pending"},
    "running": {"fill": "#fef3c7", "border": "#f59e0b", "text": "#92400e", "label": "Running"},
    "done":    {"fill": "#dcfce7", "border": "#22c55e", "text": "#166534", "label": "Done"},
    "failed":  {"fill": "#fee2e2", "border": "#ef4444", "text": "#991b1b", "label": "Failed"},
}

PROVIDER_COLOR = {
    "Anthropic": "#7c3aed",   # violet
    "OpenAI":    "#0ea5e9",   # sky
}

# --- Global CSS -------------------------------------------------------------

st.markdown(
    """
    <style>
    /* Tighter, consistent metric labels */
    div[data-testid="stMetric"] { padding: 4px 0; }
    div[data-testid="stMetricLabel"] { font-size: 12px; color: #64748b; }
    div[data-testid="stMetricValue"] { font-size: 22px; }

    /* Agent cards */
    .agent-card {
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 14px 14px 12px 14px;
        background: #ffffff;
        height: 100%;
        box-shadow: 0 1px 2px rgba(15,23,42,0.04);
    }
    .agent-card .row {
        display: flex; justify-content: space-between; align-items: center;
        margin-bottom: 4px;
    }
    .agent-card .name { font-weight: 600; font-size: 14px; color: #0f172a; }
    .agent-card .pill {
        font-size: 11px; font-weight: 600; padding: 2px 8px;
        border-radius: 999px; border: 1px solid;
    }
    .agent-card .meta { font-size: 12px; color: #64748b; margin-bottom: 10px; }
    .agent-card .provider-chip {
        display: inline-block; padding: 1px 7px; border-radius: 4px;
        font-size: 10px; font-weight: 600; color: white; margin-right: 6px;
        vertical-align: middle;
    }
    .agent-card .stats {
        display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px;
        padding-top: 8px; border-top: 1px solid #f1f5f9;
    }
    .agent-card .stat-label { font-size: 10px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.04em; }
    .agent-card .stat-value { font-size: 14px; font-weight: 600; color: #0f172a; margin-top: 2px; }

    /* Stream box */
    .stream-box {
        background: #0f172a; color: #e2e8f0;
        border-radius: 10px; padding: 14px 16px;
        font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 13px; line-height: 1.5;
        max-height: 280px; overflow-y: auto;
        white-space: pre-wrap;
    }
    .stream-box .label { color: #94a3b8; font-size: 11px; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 6px; }

    /* Section headings */
    .section-h {
        font-size: 13px; font-weight: 600; color: #64748b;
        text-transform: uppercase; letter-spacing: 0.06em;
        margin-bottom: 8px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# --- Header -----------------------------------------------------------------

st.title("🧠 Reporting Agents")
st.caption(
    "Four agents draft the monthly fund report. Specialists write the "
    "sections, a Writer stitches them together, a Verifier re-reads the "
    "source data and checks every number. Mixed providers on purpose: "
    "Anthropic for analysis, OpenAI for prose."
)

# --- State ------------------------------------------------------------------

if "trace" not in st.session_state:
    st.session_state["trace"] = new_reporting_trace()

if "loaded_trace" in st.session_state:
    st.session_state["trace"] = st.session_state.pop("loaded_trace")

trace: RunTrace = st.session_state["trace"]

missing = missing_keys([DEFAULT_MODEL, WRITER_MODEL])
key_ok = len(missing) == 0

# --- Key warning banner (full width) ---------------------------------------

if not key_ok:
    st.warning(
        f"🔑 Missing key(s): {', '.join('`' + k + '`' for k in missing)}. "
        "Add to `.streamlit/secrets.toml` (or the Streamlit Cloud Secrets "
        "panel) to generate new runs. You can still replay saved runs below.",
        icon="⚠️",
    )

# --- Sidebar: replay + controls --------------------------------------------

with st.sidebar:
    st.subheader("Saved runs")
    saved = list_saved_runs()
    if saved:
        labels = [p.stem for p in saved]
        pick = st.selectbox("Replay", ["(none)"] + labels, key="replay_pick")
        if pick != "(none)":
            path = next(p for p in saved if p.stem == pick)
            st.session_state["loaded_trace"] = RunTrace.load(path)
            st.rerun()
    else:
        st.caption("No saved runs yet. Generate one to see it here.")

    st.divider()
    st.subheader("Settings")
    slow_mo = st.toggle(
        "Slow-mo (teaching mode)",
        value=True,
        help="Briefly pauses between agents so the canvas animation is visible.",
    )

# --- Action bar -------------------------------------------------------------

ctrl_l, ctrl_r = st.columns([1, 4])
with ctrl_l:
    run_clicked = st.button(
        "▶ Generate report",
        type="primary",
        disabled=not key_ok,
        use_container_width=True,
    )
    reset_clicked = st.button("↺ Reset", use_container_width=True)
    if reset_clicked:
        st.session_state["trace"] = new_reporting_trace()
        st.rerun()
with ctrl_r:
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total cost", f"${trace.total_cost_usd:.4f}")
    m2.metric("Input tokens", f"{trace.total_input_tokens:,}")
    m3.metric("Output tokens", f"{trace.total_output_tokens:,}")
    m4.metric("Wall time", f"{trace.total_elapsed_s:.1f}s")

st.divider()

# --- Canvas (graphviz) ------------------------------------------------------

def render_canvas(trace: RunTrace) -> None:
    """Polished graphviz pipeline. Ships with Streamlit, no extra deps."""
    lines = [
        "digraph G {",
        '  rankdir=LR;',
        '  bgcolor="transparent";',
        '  graph [pad="0.4", ranksep="0.9", nodesep="0.5"];',
        '  node [shape=box, style="rounded,filled,bold", '
        'fontname="Helvetica", fontsize=12, margin="0.25,0.15", '
        'penwidth=2];',
        '  edge [color="#94a3b8", penwidth=2, arrowsize=0.7];',
    ]
    for s in trace.steps:
        st_def = STATUS[s.status]
        provider = PROVIDER_FOR_NODE.get(s.name, "")
        meta = f"{provider} · {st_def['label']}"
        # Use HTML-like label for two lines + color hints.
        label = (
            f'<<FONT POINT-SIZE="13"><B>{html.escape(s.label)}</B></FONT>'
            f'<BR/><FONT POINT-SIZE="10" COLOR="{st_def["text"]}">{meta}</FONT>>'
        )
        lines.append(
            f'  {s.name} [label={label}, '
            f'fillcolor="{st_def["fill"]}", color="{st_def["border"]}"];'
        )
    for e in trace.edges:
        style = "bold" if e.animated else "solid"
        color = "#f59e0b" if e.animated else "#94a3b8"
        lines.append(f'  {e.source} -> {e.target} [style="{style}", color="{color}"];')
    lines.append("}")
    st.graphviz_chart("\n".join(lines), use_container_width=True)


# --- Agent cards ------------------------------------------------------------

def _card_html(step: Step) -> str:
    st_def = STATUS[step.status]
    provider = PROVIDER_FOR_NODE.get(step.name, "")
    provider_color = PROVIDER_COLOR.get(provider, "#64748b")
    model = step.model or "—"
    return f"""
    <div class="agent-card">
      <div class="row">
        <div class="name">{html.escape(step.label)}</div>
        <div class="pill" style="background:{st_def['fill']}; color:{st_def['text']}; border-color:{st_def['border']};">
          {st_def['label']}
        </div>
      </div>
      <div class="meta">
        <span class="provider-chip" style="background:{provider_color};">{provider}</span>
        <span>{html.escape(model)}</span>
      </div>
      <div class="stats">
        <div>
          <div class="stat-label">Elapsed</div>
          <div class="stat-value">{step.elapsed_s:.1f}s</div>
        </div>
        <div>
          <div class="stat-label">Cost</div>
          <div class="stat-value">${step.cost_usd:.4f}</div>
        </div>
        <div>
          <div class="stat-label">Tokens</div>
          <div class="stat-value">{step.input_tokens + step.output_tokens:,}</div>
        </div>
      </div>
    </div>
    """


def render_cards(trace: RunTrace) -> None:
    cols = st.columns(len(trace.steps))
    for col, s in zip(cols, trace.steps):
        with col:
            st.markdown(_card_html(s), unsafe_allow_html=True)


# --- Inspector --------------------------------------------------------------

def render_inspector(trace: RunTrace) -> None:
    st.markdown('<div class="section-h">Agent inspector</div>', unsafe_allow_html=True)
    names = [s.label for s in trace.steps]
    choice = st.selectbox(
        "Select an agent",
        names,
        key="inspector_select",
        label_visibility="collapsed",
    )
    step = next(s for s in trace.steps if s.label == choice)
    st_def = STATUS[step.status]
    provider = PROVIDER_FOR_NODE.get(step.name, "")
    provider_color = PROVIDER_COLOR.get(provider, "#64748b")

    st.markdown(
        f"""
        <div style="display:flex; gap:8px; align-items:center; margin-bottom:8px;">
            <span class="pill" style="background:{st_def['fill']}; color:{st_def['text']}; border:1px solid {st_def['border']}; padding:3px 10px; border-radius:999px; font-size:12px; font-weight:600;">
                {st_def['label']}
            </span>
            <span style="background:{provider_color}; color:white; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:600;">
                {provider}
            </span>
            <span style="color:#64748b; font-size:13px;">{html.escape(step.model or '—')}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if step.error:
        st.error(f"Error: {step.error}")

    st.info(f"**Why this agent exists.** {step.why}")

    tab_p, tab_i, tab_o = st.tabs(["📋 System prompt", "📨 Input", "📤 Output"])
    with tab_p:
        st.code(step.system_prompt or "(not run yet)", language="markdown")
    with tab_i:
        st.code(step.user_prompt or "(not run yet)", language="markdown")
    with tab_o:
        if step.response:
            st.markdown(step.response)
        else:
            st.caption("Not run yet.")


# --- Run orchestration ------------------------------------------------------

def execute_run(trace: RunTrace, slow_mo: bool) -> None:
    """Run all four agents in order, refreshing visible state between each."""
    canvas_slot = st.empty()
    cards_slot = st.empty()
    stream_slot = st.empty()

    def repaint():
        with canvas_slot.container():
            render_canvas(trace)
        with cards_slot.container():
            render_cards(trace)

    streaming = {"buf": "", "label": ""}

    def on_token(text: str):
        streaming["buf"] += text
        stream_slot.markdown(
            f'<div class="stream-box"><div class="label">{streaming["label"]} · streaming</div>{html.escape(streaming["buf"])}</div>',
            unsafe_allow_html=True,
        )

    def before(step_name: str, label: str):
        streaming["buf"] = ""
        streaming["label"] = label
        trace.start(step_name)
        repaint()
        if slow_mo:
            time.sleep(0.6)

    def after():
        repaint()
        if slow_mo:
            time.sleep(0.4)

    try:
        before("performance", "Performance Agent")
        perf = performance_agent.run(trace, on_token=on_token)
        after()

        before("holdings", "Holdings Agent")
        hold = holdings_agent.run(trace, on_token=on_token)
        after()

        before("writer", "Writer Agent")
        draft = writer_agent.run(trace, perf, hold, on_token=on_token)
        trace.final_report = draft
        after()

        before("verifier", "Verifier Agent")
        _, passed, issues = verifier_agent.run(trace, draft, on_token=on_token)
        trace.verifier_passed = passed
        trace.verifier_issues = issues
        after()

        stream_slot.empty()
        path = trace.save()
        st.session_state["last_saved_run"] = str(path)
    except Exception as e:
        st.error(f"Run failed: {e}")
        repaint()


# --- Render: pipeline + cards ----------------------------------------------

st.markdown('<div class="section-h">Pipeline</div>', unsafe_allow_html=True)

if run_clicked:
    trace = new_reporting_trace()
    st.session_state["trace"] = trace
    execute_run(trace, slow_mo=slow_mo)
else:
    render_canvas(trace)
    render_cards(trace)

st.divider()
render_inspector(trace)

st.divider()

# --- Final report -----------------------------------------------------------

st.markdown('<div class="section-h">Final report</div>', unsafe_allow_html=True)

if trace.final_report:
    if trace.verifier_passed is True:
        st.success("✅ Verifier: PASS — every number ties to source.")
    elif trace.verifier_passed is False:
        st.error("❌ Verifier: FAIL — issues below.")
        for issue in trace.verifier_issues:
            st.write(f"- {issue}")

    with st.container(border=True):
        st.markdown(trace.final_report)

    dl1, dl2, _ = st.columns([1, 1, 3])
    dl1.download_button(
        "⬇ Report (.md)",
        trace.final_report,
        file_name=f"archway_report_{trace.run_id}.md",
        use_container_width=True,
    )
    dl2.download_button(
        "⬇ Trace (.json)",
        json.dumps(trace.to_dict(), indent=2),
        file_name=f"archway_trace_{trace.run_id}.json",
        mime="application/json",
        use_container_width=True,
    )
else:
    st.caption("No report yet. Click **▶ Generate report** above.")
