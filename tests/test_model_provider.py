import pytest
from agents import OpenAIChatCompletionsModel, OpenAIResponsesModel

from evidence_worker.model_provider import load_learning_model


def test_openai_is_the_default_provider() -> None:
    model = load_learning_model({"OPENAI_LEARNING_MODEL": " gpt-5-mini "})

    assert model == "gpt-5-mini"


def test_model_name_is_always_required() -> None:
    with pytest.raises(RuntimeError, match="OPENAI_LEARNING_MODEL must be set"):
        load_learning_model({})


def test_openai_compatible_defaults_to_chat_completions() -> None:
    model = load_learning_model(
        {
            "LEARNING_MODEL_PROVIDER": "openai-compatible",
            "OPENAI_LEARNING_MODEL": "provider-model",
            "OPENAI_COMPATIBLE_API_KEY": "test-key",
            "OPENAI_COMPATIBLE_BASE_URL": "https://example.test/v1",
        }
    )

    assert isinstance(model, OpenAIChatCompletionsModel)
    assert model.model == "provider-model"
    assert str(model._get_client().base_url) == "https://example.test/v1/"


def test_openai_compatible_can_use_responses_api() -> None:
    model = load_learning_model(
        {
            "LEARNING_MODEL_PROVIDER": "openai-compatible",
            "OPENAI_LEARNING_MODEL": "provider-model",
            "OPENAI_COMPATIBLE_API_KEY": "test-key",
            "OPENAI_COMPATIBLE_BASE_URL": "https://example.test/v1",
            "OPENAI_COMPATIBLE_API": "responses",
        }
    )

    assert isinstance(model, OpenAIResponsesModel)
    assert model.model == "provider-model"
    assert str(model._get_client().base_url) == "https://example.test/v1/"


def test_openai_compatible_api_key_is_required() -> None:
    with pytest.raises(RuntimeError, match="OPENAI_COMPATIBLE_API_KEY must be set"):
        load_learning_model(
            {
                "LEARNING_MODEL_PROVIDER": "openai-compatible",
                "OPENAI_LEARNING_MODEL": "provider-model",
                "OPENAI_COMPATIBLE_BASE_URL": "https://example.test/v1",
            }
        )


def test_openai_compatible_base_url_is_required() -> None:
    with pytest.raises(RuntimeError, match="OPENAI_COMPATIBLE_BASE_URL must be set"):
        load_learning_model(
            {
                "LEARNING_MODEL_PROVIDER": "openai-compatible",
                "OPENAI_LEARNING_MODEL": "provider-model",
                "OPENAI_COMPATIBLE_API_KEY": "test-key",
            }
        )


def test_unknown_openai_compatible_api_is_rejected() -> None:
    with pytest.raises(
        RuntimeError,
        match="OPENAI_COMPATIBLE_API must be either 'chat_completions' or 'responses'",
    ):
        load_learning_model(
            {
                "LEARNING_MODEL_PROVIDER": "openai-compatible",
                "OPENAI_LEARNING_MODEL": "provider-model",
                "OPENAI_COMPATIBLE_API_KEY": "test-key",
                "OPENAI_COMPATIBLE_BASE_URL": "https://example.test/v1",
                "OPENAI_COMPATIBLE_API": "unknown",
            }
        )


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="must be either 'openai' or 'openai-compatible'"):
        load_learning_model(
            {
                "LEARNING_MODEL_PROVIDER": "unknown",
                "OPENAI_LEARNING_MODEL": "some-model",
            }
        )
