"""Base wrapper around LLM provider SDKs.

Each agent calls `call_agent` with a system prompt + user prompt. The
provider is inferred from the model name: anything starting with "claude"
goes to Anthropic, anything starting with "gpt" or "o" goes to OpenAI.

Showing students that one pipeline can mix providers is part of the lesson.
"""
from __future__ import annotations

import os
from typing import Callable, Literal

from .trace import RunTrace

DEFAULT_MODEL = "claude-sonnet-4-6"
WRITER_MODEL = "gpt-5.4-mini"

Provider = Literal["anthropic", "openai"]


def _provider_for(model: str) -> Provider:
    if model.startswith("claude"):
        return "anthropic"
    if model.startswith("gpt") or model.startswith("o"):
        return "openai"
    raise ValueError(f"Unknown provider for model {model!r}")


def _get_key(env_name: str) -> str | None:
    try:
        import streamlit as st  # lazy: keeps module importable in plain Python
        key = st.secrets.get(env_name)
        if key:
            return key
    except Exception:
        pass
    return os.environ.get(env_name)


def api_key_available(model: str = DEFAULT_MODEL) -> bool:
    provider = _provider_for(model)
    env_name = "ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY"
    return _get_key(env_name) is not None


def missing_keys(models: list[str]) -> list[str]:
    """Return the list of env-var names whose key is missing for these models."""
    needed = set()
    for m in models:
        provider = _provider_for(m)
        needed.add("ANTHROPIC_API_KEY" if provider == "anthropic" else "OPENAI_API_KEY")
    return sorted(n for n in needed if _get_key(n) is None)


def call_agent(
    trace: RunTrace,
    step_name: str,
    system_prompt: str,
    user_prompt: str,
    model: str = DEFAULT_MODEL,
    on_token: Callable[[str], None] | None = None,
) -> str:
    """Run one agent step. Streams tokens to `on_token` if provided.

    Returns full response text. Updates the trace step in place.
    """
    provider = _provider_for(model)
    step = trace.step(step_name)
    step.model = model
    step.system_prompt = system_prompt
    step.user_prompt = user_prompt
    trace.start(step_name)

    try:
        if provider == "anthropic":
            response, in_tok, out_tok = _call_anthropic(model, system_prompt, user_prompt, on_token)
        else:
            response, in_tok, out_tok = _call_openai(model, system_prompt, user_prompt, on_token)
    except Exception as e:
        trace.fail(step_name, str(e))
        raise

    trace.finish(step_name, response, in_tok, out_tok)
    return response


def _call_anthropic(
    model: str,
    system_prompt: str,
    user_prompt: str,
    on_token: Callable[[str], None] | None,
) -> tuple[str, int, int]:
    from anthropic import Anthropic

    key = _get_key("ANTHROPIC_API_KEY")
    if key is None:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = Anthropic(api_key=key)
    full = []
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
        return "".join(full), final.usage.input_tokens, final.usage.output_tokens


def _call_openai(
    model: str,
    system_prompt: str,
    user_prompt: str,
    on_token: Callable[[str], None] | None,
) -> tuple[str, int, int]:
    from openai import OpenAI

    key = _get_key("OPENAI_API_KEY")
    if key is None:
        raise RuntimeError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=key)
    full = []
    stream = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=2048,
        stream=True,
        stream_options={"include_usage": True},
    )
    input_tokens = 0
    output_tokens = 0
    for chunk in stream:
        if chunk.choices:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                full.append(delta.content)
                if on_token is not None:
                    on_token(delta.content)
        if getattr(chunk, "usage", None):
            input_tokens = chunk.usage.prompt_tokens
            output_tokens = chunk.usage.completion_tokens
    return "".join(full), input_tokens, output_tokens
