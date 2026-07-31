"""Resolve the explicitly configured model used by the learning exercises."""

from __future__ import annotations

import os
from collections.abc import Mapping

from agents import Model, OpenAIChatCompletionsModel, OpenAIResponsesModel
from openai import AsyncOpenAI

DEFAULT_COMPATIBLE_API = "chat_completions"


def load_learning_model(env: Mapping[str, str] | None = None) -> str | Model:
    """Build the configured OpenAI or OpenAI-compatible model without a request."""
    values = os.environ if env is None else env
    model_name = _required(values, "OPENAI_LEARNING_MODEL")
    provider = values.get("LEARNING_MODEL_PROVIDER", "openai").strip().lower()

    if provider == "openai":
        return model_name

    if provider == "openai-compatible":
        api_key = _required(values, "OPENAI_COMPATIBLE_API_KEY")
        base_url = _required(values, "OPENAI_COMPATIBLE_BASE_URL")
        api = values.get("OPENAI_COMPATIBLE_API", DEFAULT_COMPATIBLE_API).strip().lower()
        client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        if api == "chat_completions":
            return OpenAIChatCompletionsModel(model=model_name, openai_client=client)
        if api == "responses":
            return OpenAIResponsesModel(model=model_name, openai_client=client)

        raise RuntimeError(
            "OPENAI_COMPATIBLE_API must be either 'chat_completions' or 'responses'; "
            f"received {api!r}"
        )

    raise RuntimeError(
        "LEARNING_MODEL_PROVIDER must be either 'openai' or 'openai-compatible'; "
        f"received {provider!r}"
    )


def _required(env: Mapping[str, str], name: str) -> str:
    value = env.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} must be set")
    return value
