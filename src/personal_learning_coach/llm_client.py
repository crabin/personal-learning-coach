"""Shared LLM client helpers and model configuration."""

from __future__ import annotations

import os
from typing import Any, cast

from openai import OpenAI

# Default model; override via OPENAI_MODEL env var.
DEFAULT_MODEL = "gpt-4.5"


def get_model() -> str:
    return os.environ.get("OPENAI_MODEL", DEFAULT_MODEL)


def get_client() -> OpenAI:
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def extract_text(response: Any) -> str:
    """Extract text from either chat completions or messages-style responses."""
    if hasattr(response, "content"):
        return cast(str, response.content[0].text)
    if hasattr(response, "choices"):
        return cast(str, response.choices[0].message.content or "")
    raise ValueError("Unsupported LLM response shape")


def generate_text(
    *,
    system: str,
    prompt: str,
    max_tokens: int,
    client: Any | None = None,
) -> str:
    """Generate text using the configured client or a compatible test double."""
    llm_client = client or get_client()
    if hasattr(llm_client, "messages"):
        response = llm_client.messages.create(
            model=get_model(),
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": prompt}],
        )
        return extract_text(response)

    response = llm_client.chat.completions.create(
        model=get_model(),
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return extract_text(response)
