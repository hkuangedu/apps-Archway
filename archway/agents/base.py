"""Base wrapper around the Anthropic SDK.

Each agent is a function that calls `call_agent` with a system prompt + user
prompt. The wrapper records prompts, response, and token counts to the trace.
"""
from __future__ import annotations

import os
from typing import Callable

from .trace import RunTrace

DEFAULT_MODEL = "claude-sonnet-4-6"


def _get_api_key() -> str | None:
    """Look in Streamlit secrets first, then env. Returns None if missing."""
    try:
        import streamlit as st  # lazy: keeps the module importable in plain Python
        key = st.secrets.get("ANTHROPIC_API_KEY")
        if key:
            return key
    except Exception:
        pass
    return os.environ.get("ANTHROPIC_API_KEY")


def api_key_available() -> bool:
    return _get_api_key() is not None


def call_agent(
    trace: RunTrace,
    step_name: str,
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    on_token: Callable[[str], None] | None = None,
) -> str:
    """Run one agent step. Streams tokens to `on_token` if provided.

    Returns the full response text. Updates the trace step in place.
    """
    from anthropic import Anthropic

    step = trace.step(step_name)
    step.model = model
    step.system_prompt = system_prompt
    step.user_prompt = user_prompt
    trace.start(step_name)

    key = _get_api_key()
    if key is None:
        trace.fail(step_name, "ANTHROPIC_API_KEY not set")
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = Anthropic(api_key=key)
    full = []
    input_tokens = 0
    output_tokens = 0
    try:
        with client.messages.stream(
            model=model,
            max_tokens=2048,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        ) as stream:
            for text in stream.text_stream:
                full.append(text)
                if on_token is not None:
                    on_token(text)
            final = stream.get_final_message()
            input_tokens = final.usage.input_tokens
            output_tokens = final.usage.output_tokens
    except Exception as e:
        trace.fail(step_name, str(e))
        raise

    response = "".join(full)
    trace.finish(step_name, response, input_tokens, output_tokens)
    return response
