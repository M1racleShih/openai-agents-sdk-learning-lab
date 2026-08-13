from importlib.metadata import version
from inspect import signature

from agents import (
    Agent,
    RawResponsesStreamEvent,
    RunConfig,
    RunItemStreamEvent,
    Runner,
    RunResultStreaming,
    SQLiteSession,
    function_tool,
)
from openai.types.responses import ResponseTextDeltaEvent
from prompt_toolkit import PromptSession
from pydantic import BaseModel
from rich.console import Console


class _ProbeOutput(BaseModel):
    answer: str


@function_tool(timeout=0.5, timeout_behavior="raise_exception")
async def _probe_tool(value: str) -> str:
    """Return one value for SDK surface checks."""
    return value


def test_course_dependencies_are_locked_to_the_reviewed_versions() -> None:
    assert version("mlflow") == "3.13.0"
    assert version("openai-agents") == "0.20.0"
    assert version("prompt-toolkit") == "3.0.53"
    assert version("rich") == "15.0.0"
    assert PromptSession is not None
    assert Console is not None


def test_reviewed_sdk_surfaces_remain_available() -> None:
    agent = Agent(
        name="compatibility probe",
        instructions="Return a structured probe.",
        model="explicit-test-model",
        output_type=_ProbeOutput,
        tools=[_probe_tool],
    )
    assert agent.model == "explicit-test-model"
    assert agent.output_type is _ProbeOutput
    assert _probe_tool.timeout_seconds == 0.5
    assert _probe_tool.timeout_behavior == "raise_exception"
    assert callable(Runner.run)
    assert callable(Runner.run_streamed)
    assert callable(function_tool)
    assert RawResponsesStreamEvent is not None
    assert RunItemStreamEvent is not None
    assert ResponseTextDeltaEvent is not None

    for runner_method in (Runner.run, Runner.run_streamed):
        runner_parameters = signature(runner_method).parameters
        assert "context" in runner_parameters
        assert "session" in runner_parameters
        assert "max_turns" in runner_parameters
        assert "run_config" in runner_parameters

    run_config_parameters = signature(RunConfig).parameters
    assert "workflow_name" in run_config_parameters
    assert "trace_id" in run_config_parameters
    assert "group_id" in run_config_parameters
    assert "trace_include_sensitive_data" in run_config_parameters


def test_reviewed_session_and_cancellation_signatures_remain_available() -> None:
    session_parameters = signature(SQLiteSession).parameters
    assert session_parameters["db_path"].default == ":memory:"

    cancel_parameters = signature(RunResultStreaming.cancel).parameters
    assert "mode" in cancel_parameters
    assert "after_turn" in str(cancel_parameters["mode"].annotation)
    assert hasattr(RunResultStreaming, "stream_events")
