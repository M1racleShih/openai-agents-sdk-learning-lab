---
title: M04 · Redacted tracing and deterministic tests
description: Use stable trace identifiers, minimal local records, and a replaceable runner boundary to inspect run paths while preventing default tests from calling a real model.
---

<p class="lesson-kicker">M04 · 60 minutes · concepts + lab</p>

# Redacted tracing and deterministic tests

<p class="lesson-deck">Keep enough evidence to explain a run without copying raw private content into traces, test output, or local records.</p>

<div class="lesson-meta" aria-label="Lesson information">
  <span>SDK v0.20.0</span>
  <span>10 review questions</span>
  <span>3 test layers</span>
  <span>1 real smoke run</span>
</div>

## Learning outcomes

After this chapter, you should be able to:

- distinguish a complete run, model calls, and function-tool calls in a default trace;
- correlate a run with a stable `workflow_name`, a unique `trace_id`, and a `group_id` that
  contains no domain content;
- explain the default behavior and risk of `trace_include_sensitive_data`;
- disable trace capture of model inputs and outputs and function-tool inputs and outputs while
  keeping the span structure;
- save a local record containing only application session/run IDs, the trace ID, provenance,
  tool-phase classifications, completion, evidence references, and error codes;
- replace the `Runner.run` boundary through dependency injection and write deterministic tests
  that do not call a real model;
- explain what unit tests, deterministic integration tests, and a real-model smoke test each
  prove;
- explicitly exclude the real-model smoke test from the default test run.

!!! abstract "Chapter boundary"

    This chapter adds observation and test boundaries to the single-run, read-only path from M03.
    It does not add custom trace processors, a complete eval platform, an SDK Session
    implementation, streaming, or a production logging system. It also does not store raw
    prompts, tool arguments, tool outputs, or complete answers.

## Core material

### 1. A trace shows the run path; it does not prove the answer is correct

`Runner.run(...)` creates a trace by default and records several spans within the run. A trace is
one workflow from start to finish. A span is one step with a start and end time.

The main layers recorded by `v0.20.0` are:

```text
one Runner.run: trace
  → runner invocation: task span
  → each model-loop turn: turn span
  → Agent execution: agent span
  → model generation: generation span
  → each function-tool call: function span
```

After you add the two function tools from M02, one trace can show how many model turns ran, which
tools were called, when a tool call started and ended, and which span was marked with an error. It
cannot answer “does the evidence sufficiently support the answer?” M03 status rules, source
coverage checks, and tests still make that decision.

| Where you look | What it can confirm | What it cannot confirm alone |
| --- | --- | --- |
| `generation` span | Whether a model call happened, its timing, and its error location | Whether the output is factually correct for the domain |
| `function` span | Tool name, call order, timing, and error location | Whether returned data is sufficient to complete the task |
| `WorkerResult` | Status, evidence references, and stable error codes | Every model and tool step that actually occurred |
| Deterministic test | Whether a fixed input produces the required result | Whether the real provider currently responds |

Troubleshooting therefore joins two kinds of evidence. Use the local record to find the `trace_id`,
inspect the path in the trace, and then use the result status and consistency rules to decide whether
the caller may use the returned content.

### 2. Session, run, and trace identifiers are different state spaces

The application owns two identifiers first; SDK tracing owns another. M05 adds an SDK Session
identifier for conversation storage. Do not collapse them into one “session ID”:

| Identifier | Lifetime | Question it answers |
| --- | --- | --- |
| application session ID | Several turns in one user conversation | Which application turns belong to one continuous interaction? |
| application run ID | Unique for every `Submit` | Which command, event sequence, and `RunOutcome` belong to this execution? |
| SDK Session ID | M05 conversation-history storage key | Which history container does the SDK read and update? |
| trace ID | One trace for one SDK run | Which model-and-tool path should the Trace viewer open? |

An application session ID may be an input to the SDK Session factory, but the concepts remain
separate: the former is an application correlation key, while the latter belongs to a replaceable
history implementation. The application creates its run ID; `trace_id` must satisfy the SDK
format. One application session can contain several runs, each with its own trace.

`RunConfig` also provides three trace-correlation fields:

| Field | Purpose | Rule in this chapter |
| --- | --- | --- |
| `workflow_name` | Display one kind of workflow under one logical name | Use a fixed constant; do not append user input |
| `trace_id` | Uniquely identify one trace | Generate it with `gen_trace_id()` before every run and save it in the minimal record |
| `group_id` | Link traces from one application session | Use the opaque application session ID, not an email, question, or file path |

A “stable name” does not mean reusing one ID for every run. Keep `workflow_name` stable, make
`trace_id` unique for every run, and reuse `group_id` only across runs that belong to the same
application session.

```python
from agents import RunConfig, gen_trace_id

WORKFLOW_NAME = "Read-only maintenance assistant"


def make_run_config(correlation_id: str) -> tuple[str, RunConfig]:
    trace_id = gen_trace_id()
    return trace_id, RunConfig(
        workflow_name=WORKFLOW_NAME,
        trace_id=trace_id,
        group_id=correlation_id,
        trace_include_sensitive_data=False,
    )
```

`gen_trace_id()` produces a trace ID accepted by the SDK. Do not hash task text and use the hash as
`trace_id`: a hash may still expose enumerable content and may not have the format required by the
SDK. Both `group_id` and `trace_metadata` are exported with the trace, so put only allowed opaque
identifiers and fixed categories in them.

### 3. Exclude sensitive content while keeping spans

In `v0.20.0`, `trace_include_sensitive_data` defaults to `True`. A generation span may then contain
model input and output, and a function span may contain tool arguments and return values. That
default is too risky for an application that reads controlled sources.

This course explicitly sets the following value in every run's `RunConfig`:

```python
RunConfig(trace_include_sensitive_data=False)
```

With this value set to `False`, the SDK still creates generation and function spans, but it does not
add sensitive model inputs and outputs or tool inputs and outputs to them. Tool names, span timing,
and run structure remain available for diagnosis. You can also change the default before the
program starts:

```bash
export OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA=0
```

This chapter still requires an explicit `False` in code because a test can assert that boundary
without depending on the machine's environment.

!!! warning "One setting protects only the trace"

    `trace_include_sensitive_data=False` does not sanitize application logs, local records, test
    failure output, or `RunResult.new_items` and `raw_responses` in memory. Do not print those
    objects. Application logs and local records need their own allowlists.

In `v0.20.0`, the `openai.agents` and `openai.agents.tracing` loggers do not log model and tool input
or output by default. Do not set `OPENAI_AGENTS_DONT_LOG_MODEL_DATA` or
`OPENAI_AGENTS_DONT_LOG_TOOL_DATA` to `0` for debugging. Your application logger should write only
fixed event names, `trace_id`, status, and error codes—not exception text, prompts, tool arguments,
or tool results.

### 4. A minimal `RunRecord` links results, provenance, and tool phases

A trace is useful for inspecting the run path. A local record lets the application quickly answer
“what was the result, and where is its trace?” Neither needs a copy of the source documents.

```python
from typing import Literal

from pydantic import BaseModel


class ProvenanceRef(BaseModel):
    kind: Literal["source", "skill"]
    artifact_id: str
    revision: str
    checksum: str


class ToolPhase(BaseModel):
    tool_name: str
    phase: Literal["started", "finished"]
    outcome: Literal["ok", "error", "timeout", "cancelled"] | None = None


class RunRecord(BaseModel):
    application_session_id: str
    application_run_id: str
    trace_id: str
    provenance: list[ProvenanceRef]
    tool_phases: list[ToolPhase]
    completion: Literal[
        "completed", "incomplete", "failed", "cancelled", "timed_out"
    ]
    evidence_refs: list[str]
    error_codes: list[str]
```

Here `skill` means a public instruction package on the course allowlist, not another Agent or an
SDK runtime extension point; keep the list empty when the capstone uses none. Source and skill
records contain only ID, revision/version, and checksum—not body text. `ToolPhase` records only an
approved tool's start, finish, and finish classification, never arguments or raw output.
`evidence_refs` keeps stable locators; `error_codes` keeps M03 classifications.

| Store | Do not store |
| --- | --- |
| Application session/run IDs and trace ID | API keys, access tokens, or client configuration |
| Five completion classifications | Raw task text, complete prompts, or complete answers |
| Source/skill provenance and evidence references | Source text or raw tool output |
| Tool start/finish classifications and stable error codes | Tool arguments, exception text, stacks, or absolute paths |

Serialize each `RunRecord` as one line of JSON and write it to the record file specified by local
context. The path, logger, and write function remain local dependencies and do not enter the
prompt. Tests use `tmp_path`; they must not write to the real run record.

Generate the application run ID and `trace_id` before calling `Runner.run`. If the model or a tool
fails, the run times out, or the caller cancels, the M03 wrapper can still write the same IDs with
the accurate final classification. No abnormal branch may write `completed`.

### 5. Inject the runner at its call site so default tests need no model

M03 may temporarily replace `Runner.run`. M04 makes that replacement point an explicit parameter:
production code receives `Runner.run` by default, while a test passes an asynchronous fake. The
application needs one boundary, not a general runner framework.

```python
from collections.abc import Awaitable, Callable

from agents import Agent, RunResult, Runner

RunAgent = Callable[..., Awaitable[RunResult]]


async def run_observed(
    agent: Agent[object],
    model_input: str,
    local_context: object,
    application_session_id: str,
    application_run_id: str,
    *,
    run_agent: RunAgent = Runner.run,
) -> WorkerResult:
    trace_id, run_config = make_run_config(application_session_id)
    sdk_result = await run_agent(
        agent,
        model_input,
        context=local_context,
        max_turns=6,
        run_config=run_config,
    )
    result = check_domain_completion(
        sdk_result.final_output_as(WorkerResult, raise_if_incorrect_type=True)
    )
    append_run_record(application_session_id, application_run_id, trace_id, result)
    return result
```

The example shows only the injection point on the normal path. In the lab, connect the same point
to the timeout and exception mapping from M03 so abnormal paths also write records. Do not create a
second run flow.

A deterministic test passes `fake_run_agent`. The fake returns a result constructed by the test
and captures the keyword arguments it received:

```python
import pytest

from agents import RunConfig, RunResult


@pytest.mark.asyncio
async def test_run_uses_redacted_trace_config(tmp_path):
    captured: dict[str, object] = {}

    async def fake_run_agent(*_args: object, **kwargs: object) -> RunResult:
        captured.update(kwargs)
        return stub_sdk_result(completed_result())

    result = await run_observed(
        test_agent(),
        "public fixture request",
        test_context(tmp_path),
        "session_test_001",
        "run_test_001",
        run_agent=fake_run_agent,
    )

    config = captured["run_config"]
    assert isinstance(config, RunConfig)
    assert config.workflow_name == WORKFLOW_NAME
    assert config.group_id == "session_test_001"
    assert config.trace_include_sensitive_data is False
    assert result.status == "completed"
```

`stub_sdk_result`, `completed_result`, `test_agent`, and `test_context` are test helpers to complete
in the lab. The test does not patch SDK global state or import the SDK repository's internal
`FakeModel`. As long as the fake runner has no network code, this test needs no API key.

### 6. Three test layers supply different evidence

| Test layer | What runs | What it proves | What it does not prove |
| --- | --- | --- | --- |
| Unit test | Validators, record filtering, and tool functions | Ordinary Python rules are correct for fixed inputs | Whether the runner and parts are connected correctly |
| Deterministic integration test | Application wrapper + fake runner + fixture tools | Parameters, status mapping, records, and exception paths are connected correctly | Whether the real model or provider currently works |
| Real smoke test | Explicit model configuration + complete read-only path | The minimum end-to-end path currently runs | All input quality, long-term reliability, or production readiness |

The real smoke test must have a `smoke` marker and be excluded from default tests. Register the
marker in `pyproject.toml` and make the default selection expression exclude it:

```toml
[tool.pytest.ini_options]
addopts = "-q -m 'not smoke'"
markers = [
    "smoke: makes a real model API call and must be selected explicitly",
]
```

The smoke test reads only a public synthetic fixture. It must not print the prompt, complete model
output, or raw tool data. Run default tests first. Only after explicitly configuring a model and
credentials should you override the default selection expression and run the smoke test:

```bash
uv run pytest
uv run pytest -o addopts= -m smoke tests/test_smoke.py -q
```

The second command is a real network check with a cost. It is not part of every default `pytest`
run. If model configuration is missing, the smoke test should explicitly skip or fail; it must not
silently fall back to an SDK default model.

### 7. Use the trace to answer concrete questions

After the real smoke run, inspect the Trace viewer in this order:

1. Find this kind of application run by its fixed `workflow_name`.
2. Find this run with the `trace_id` from the local record.
3. Confirm that `group_id` matches the opaque correlation identifier used for this application
   session.
4. Expand task and turn spans to count model turns.
5. Inspect function-span tool names, order, timing, and error marks.
6. Confirm that generation and function spans do not contain raw input or output.
7. Compare a failed span with the local record's `status` and `error_codes`.

If an expected function span is absent, first check whether the model requested the tool. If a
function span exists and is marked with an error, the problem occurred during the tool call. If the
tool succeeded but the result is still `incomplete`, check source coverage and domain rules. These
three checks prevent every failure from being blamed on the model.

## Exercises

Answer the questions before expanding the reference answers.

### Concepts and code reading

1. What do a trace and a span represent?
2. Which two span types in a default trace are most likely to contain model or tool content?
3. True or false: `trace_include_sensitive_data=False` disables tracing completely.
4. What problems do the application session ID, application run ID, SDK Session ID, and trace ID solve?
5. Why should user questions and file paths not go directly into `group_id` or `trace_metadata`?
6. Why does the minimal local record store evidence references instead of evidence text?
7. True or false: after disabling sensitive trace content, it is safe to print
   `RunResult.new_items`.
8. How does injecting a `run_agent` parameter prevent deterministic tests from calling a real
   model?
9. What evidence does each layer add: unit test, deterministic integration test, and real smoke
   test?
10. What should you check first when an expected function span is absent, and what should you
    check when it exists but is marked with an error?

<details class="exercise-answers">
<summary>Reference answers</summary>

1. A trace represents one workflow from start to finish. A span represents one step with a start
   and end time.
2. A generation span may contain model input and output. A function span may contain tool input
   and output.
3. False. The setting keeps spans and excludes sensitive model and tool inputs and outputs.
4. The application session ID links turns; the application run ID identifies one command and
   event sequence; the SDK Session ID locates a history container; the trace ID locates one SDK
   execution path.
5. These fields are exported with the trace. User content, paths, or identifying values would keep
   exposing domain information after span content was disabled.
6. References are enough to locate and review a source. Storing source text expands the number of
   private-data copies, their retention time, and their access surface.
7. False. The setting changes only the trace payload; it does not sanitize in-memory objects,
   application logs, or test failure output.
8. Production code defaults to `Runner.run`. A test supplies an asynchronous fake with no network
   code and a predetermined return or exception, so execution never reaches the real runner.
9. A unit test proves a local rule. A deterministic integration test proves wrapper, parameter,
   record, and failure-mapping connections. A real smoke test proves the current model and complete
   read-only path can run at least once.
10. When there is no function span, first check whether the model requested a tool. When the span
    exists but failed, first check tool arguments, boundaries, and the underlying read-only
    service. If the tool succeeded but the result is incomplete, check source coverage and domain
    rules.

</details>

### Lab: add redacted observation and deterministic verification

Complete these tasks on the M03 run wrapper. You may add an observation module and tests, but do
not copy a parallel run path or rename the teaching skeleton above and treat it as a complete answer.

1. Define a fixed `WORKFLOW_NAME`. Generate an application run ID for every `Submit`, generate a
   trace ID with `gen_trace_id()` for every SDK run, and use the opaque application session ID as
   `group_id`.
2. Construct `RunConfig` with explicit `workflow_name`, `trace_id`, `group_id`, and
   `trace_include_sensitive_data=False`.
3. Check workflow names, group IDs, and trace metadata. They must not contain task text, file
   paths, credentials, or real service information.
4. Define and write the minimal `RunRecord`: application session/run IDs, trace ID, source/skill
   provenance, tool start/finish classifications, final completion, necessary evidence
   references, and stable error codes.
5. Inject `run_agent` at the existing run function's call site, defaulting it to `Runner.run`. Do
   not change the SDK global runner or build a general framework.
6. Use a fake runner to cover success, incomplete results, tool failure, model failure, tool
   timeout, run timeout, and cancellation. Assert the received `RunConfig`, returned `WorkerResult`, and written
   record.
7. Use synthetic fixtures and conspicuous forbidden strings to check the record file, `caplog`,
   and test failure output. No secret, raw task, evidence text, tool input/output, or exception text
   may appear.
8. Register the `smoke` marker in `pyproject.toml` and exclude it from default `pytest`. The real
   smoke test must select a model explicitly and read only a public synthetic fixture.
9. Run deterministic tests and all repository checks first, then explicitly run one real-model
   smoke test.
10. Find that run in the Trace viewer by `trace_id`, record the tool-call order and failure
    location, and confirm that raw model and tool inputs and outputs were not captured.

Run the chapter tests first, then the complete repository checks:

```bash
uv run pytest tests/test_observability.py -q
uv run ruff check .
uv run pyright
uv run pytest
```

After explicitly configuring the model and credentials, run the real smoke test separately:

```bash
uv run pytest -o addopts= -m smoke tests/test_smoke.py -q
```

Completion criteria:

- you can use a trace to explain how many model turns ran, which function tools were called, and
  which span contains the failure;
- the trace keeps the workflow, correlation identifiers, and span structure but contains no raw
  model or function-tool input or output;
- the local record contains only allowed IDs, source/skill provenance, tool phases, completion,
  evidence references, and error codes;
- deterministic tests need no API key and make no real model request;
- default `pytest` excludes the real smoke test;
- the explicitly run smoke test uses public synthetic sources and can be found in the Trace viewer;
- the repository, test output, and local record contain no secret, private source, or real service
  information.

This chapter does not provide the complete lab implementation. The core material only connects
trace configuration, a minimal record, and runner injection. You must still connect them to the
M03 status checks, exception mapping, context, and test scenarios.

## Version and official references

Last checked: 2026-08-11. Locked project version: `openai-agents==0.20.0`.

- [Current Agents SDK guide: overall positioning](https://developers.openai.com/api/docs/guides/agents)
- [`v0.20.0` Tracing: default spans, identifiers, and sensitive data](https://github.com/openai/openai-agents-python/blob/v0.20.0/docs/tracing.md)
- [`v0.20.0` Configuration: tracing and log controls](https://github.com/openai/openai-agents-python/blob/v0.20.0/docs/config.md)
- [`v0.20.0` RunConfig source](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/run_config.py)
- [`v0.20.0` trace span data structures](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/tracing/span_data.py)
- [`v0.20.0` trace ID generation source](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/tracing/util.py)
- [`v0.20.0` Runner trace creation source](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/run.py)
- [`v0.20.0` SDK tracing tests](https://github.com/openai/openai-agents-python/blob/v0.20.0/tests/test_tracing.py)
- [`v0.20.0` SDK runner replacement test](https://github.com/openai/openai-agents-python/blob/v0.20.0/tests/test_run.py)
- [pytest markers](https://docs.pytest.org/en/stable/example/markers.html)

Changes to the examples: retain `RunConfig`, `workflow_name`, `trace_id`, `group_id`,
`gen_trace_id()`, and default span behavior from the official tracing documentation and tests;
adapt them to the course's single-run, read-only application path; explicitly disable sensitive-content
capture; add a minimal local record and call-site dependency injection; remove custom processors,
SDK global-runner replacement, concurrent traces, handoffs, streaming, real private input, and the
complete lab answer.
