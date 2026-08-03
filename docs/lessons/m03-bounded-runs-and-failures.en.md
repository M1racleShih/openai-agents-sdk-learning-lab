---
title: M03 · Bounded runs and truthful failures
description: Use status consistency rules, turn limits, and run timeouts to keep incomplete, timed-out, and failed work machine-readable.
---

<p class="lesson-kicker">M03 · 90 minutes · concepts + lab</p>

# Bounded runs and truthful failures

<p class="lesson-deck">Limit the time and turns one run can consume, and let callers determine completion from result fields alone.</p>

<div class="lesson-meta" aria-label="Lesson information">
  <span>SDK v0.19.1</span>
  <span>10 review questions</span>
  <span>3 domain statuses</span>
  <span>4 abnormal scenario groups</span>
</div>

## Learning outcomes

After this chapter, you should be able to:

- distinguish `RunResult.final_output`, `new_items`, and `raw_responses`;
- explain why a normally returned SDK run does not mean the domain task is complete;
- represent the three caller-visible results with `completed`, `incomplete`, and `failed`;
- use deterministic rules to keep status, answer, evidence, and errors consistent;
- limit model-call turns with `max_turns`;
- use tool timeouts and run-level timeouts to bound two different waits;
- convert turn limits, invalid final output, tool failures, and timeouts into stable,
  machine-readable results;
- cover missing sources, tool failure, timeout, and incomplete-result scenarios.

!!! abstract "Chapter boundary"

    This chapter adds status and failure wrapping to one non-streaming run. It does not add
    retries, sessions, handoffs, approvals, persistence, or a general exception framework. M04
    covers traces, redacted records, and replacement of the runner boundary.

## Core material

### 1. `RunResult` records run products; it does not judge the domain task

`Runner.run(...)` returns a `RunResult` when it ends normally. M03 mainly uses three properties:

| Property | What it contains | How this chapter uses it |
| --- | --- | --- |
| `final_output` | The final output from the last Agent | The structured candidate result for the caller |
| `new_items` | Messages, tool calls, tool outputs, and other `RunItem` objects produced by this run | Debug the steps that actually occurred |
| `raw_responses` | One raw `ModelResponse` per model call | Provider-level diagnosis, not a domain result |

After the Agent sets `output_type=WorkerResult`, the SDK parses and validates the model's
structured output first. On a normal return, `final_output` is already a `WorkerResult`. The call
below adds a runtime type check. It does not prove that the answer is correct or that the evidence
covers every requested source:

```python
output = sdk_result.final_output_as(WorkerResult, raise_if_incorrect_type=True)
```

`new_items` can answer “which tool did the model call?” and “what did the tool return?” Common
types include `MessageOutputItem`, `ToolCallItem`, and `ToolCallOutputItem`. Do not make an upstream
caller inspect these items or logs to infer task status. Put the status directly in `WorkerResult`.

An unhandled exception does not return a complete `RunResult`. `MaxTurnsExceeded`,
`ModelBehaviorError`, and `ToolTimeoutError` all inherit from `AgentsException`. In `v0.19.1`, the
SDK attaches a snapshot containing `new_items`, `raw_responses`, and other run data to the
exception's `run_data` for diagnosis. That snapshot has not passed domain completion checks and
must not be returned as a successful result.

### 2. SDK call success and domain completion are separate decisions

Both runs below may return a schema-validated `WorkerResult` normally:

```text
run A: read every requested source → answer has sufficient evidence → completed
run B: one requested source is missing → return existing evidence and list the gap → incomplete
```

Both SDK calls succeeded, but only run A completed the domain task. Structured output proves that
fields and types pass schema validation. The application must still compare
`TaskRequest.requested_source_ids` with the actual evidence sources and check for errors that block
completion.

This course uses these statuses:

| Status | What the caller can trust | Required rule |
| --- | --- | --- |
| `completed` | The answer is complete and can be used | No `WorkerError`; every requested source was handled |
| `incomplete` | The returned content is trustworthy but partial | At least one error explains the gap; a partial answer and evidence may remain |
| `failed` | No domain answer is safe to use | At least one error; answer and evidence are empty |

In this course, `WorkerError` is reserved for a problem that blocks completion. Ordinary notices
do not go into `errors`, so a `completed` result must have an empty error list. If a real need for
non-blocking notices appears later, add a separate `warnings` field instead of weakening the
existing meaning.

Start by making each result internally consistent with Pydantic:

```python
from typing import Literal

from pydantic import BaseModel, model_validator


class SummaryError(BaseModel):
    code: str
    message: str


class BoundedSummary(BaseModel):
    status: Literal["completed", "incomplete", "failed"]
    answer: str
    evidence: list[str]
    errors: list[SummaryError]

    @model_validator(mode="after")
    def check_status(self) -> "BoundedSummary":
        if self.status == "completed" and self.errors:
            raise ValueError("completed results cannot contain errors")
        if self.status != "completed" and not self.errors:
            raise ValueError("non-completed results must explain why")
        if self.status == "failed" and (self.answer or self.evidence):
            raise ValueError("failed results cannot contain domain output")
        return self
```

This validator sees only the result object; it cannot know which sources the request named. The
application wrapper must compare the result with the original `TaskRequest`. If a requested source
is missing, the application must construct a new `incomplete` result with a stable code such as
`SOURCE_MISSING`, even if the model wrote `completed`.

### 3. Three boundaries limit different things

One run needs at least three boundary layers:

```text
per-tool timeout → limits one asynchronous tool call
max_turns        → limits how many model calls one run may start
run-level timeout → limits elapsed wall-clock time for the whole Runner.run
```

M02 set a 2-second timeout on the asynchronous query tool and selected
`timeout_behavior="raise_exception"`. On timeout, the SDK raises `ToolTimeoutError`, which contains
the tool name and timeout duration.

`Runner.run(..., max_turns=6)` allows at most 6 model calls. `v0.19.1` defines a turn as one model
invocation, including any tool calls caused by that model output. `max_turns` does not limit how
long an individual model request or tool call waits, and it does not replace a total run timeout.
Do not pass `max_turns=None` to this bounded worker because that disables the turn limit.

Python 3.12 `asyncio.timeout(...)` can wrap the whole `Runner.run`:

```python
async with asyncio.timeout(20.0):
    sdk_result = await Runner.run(
        agent,
        model_input,
        context=local_context,
        max_turns=6,
    )
```

After the timeout context manager exits, the application receives the built-in `TimeoutError`.
Cancellation is cooperative: a run timeout does not undo an external operation that already
finished. This is another reason the course permits only read-only tools before it introduces a
complete recovery strategy.

### 4. Convert exceptions with stable codes, not exception text

The caller needs a stable `WorkerError.code`, not SDK or provider exception text that may change.
Use this minimal mapping:

| Trigger | Status | Stable error code |
| --- | --- | --- |
| A requested source is missing, but a trustworthy partial result exists | `incomplete` | `SOURCE_MISSING` |
| `max_turns` is exceeded without a complete final result | `incomplete` | `MAX_TURNS` |
| An asynchronous tool exceeds its own timeout | `failed` | `TOOL_TIMEOUT` |
| The complete run exceeds wall-clock time | `failed` | `RUN_TIMEOUT` |
| A read-only query raises an application-defined service exception | `failed` | `TOOL_FAILURE` |
| Model output does not match `output_type` | `failed` | `INVALID_FINAL_OUTPUT` |
| Another exception cannot be classified safely | `failed` | `UNEXPECTED_FAILURE` |

In `v0.19.1`, `Runner.run` accepts `error_handlers`. The `"max_turns"` and
`"invalid_final_output"` handlers may return a controlled final object, which the SDK validates
against the same `output_type`. A handler does not call the model again or replay tool calls that
already happened.

Other exceptions are converted at the application's outer boundary. Because M02 sets
`failure_error_function=None`, an original tool-handler exception continues outward. The service
adapter should first convert expected underlying exceptions to the application's own
`SourceQueryError`. This keeps the wrapper from labeling programming errors such as `TypeError` as
ordinary tool failures.

Keep one final general exception exit so the JSON-in/JSON-out boundary can always return a
machine-readable failure. Log the stack locally, but expose only a fixed code and safe message.
Do not return exception text, paths, or credentials.

### 5. Minimal skeleton: tighten run boundaries in one place

The following skeleton combines a turn limit, run-level timeout, two SDK error handlers, and
exception mapping. It uses the teaching model above and is not a complete implementation of the
lab's `WorkerResult`. The lab supplies `failed_result`, `incomplete_result`,
`check_domain_completion`, and `SourceQueryError`.

```python
import asyncio
import logging

from agents import (
    Agent,
    ModelBehaviorError,
    RunErrorHandlerInput,
    RunErrorHandlerResult,
    Runner,
    ToolTimeoutError,
)

RUN_TIMEOUT_SECONDS = 20.0
MAX_TURNS = 6


def on_max_turns(
    _data: RunErrorHandlerInput[object],
) -> RunErrorHandlerResult:
    return RunErrorHandlerResult(
        final_output=incomplete_result("MAX_TURNS"),
        include_in_history=False,
    )


def on_invalid_final_output(
    _data: RunErrorHandlerInput[object],
) -> RunErrorHandlerResult:
    return RunErrorHandlerResult(
        final_output=failed_result("INVALID_FINAL_OUTPUT"),
        include_in_history=False,
    )


async def run_bounded(
    agent: Agent[object],
    model_input: str,
    local_context: object,
    logger: logging.Logger,
) -> BoundedSummary:
    try:
        async with asyncio.timeout(RUN_TIMEOUT_SECONDS):
            sdk_result = await Runner.run(
                agent,
                model_input,
                context=local_context,
                max_turns=MAX_TURNS,
                error_handlers={
                    "max_turns": on_max_turns,
                    "invalid_final_output": on_invalid_final_output,
                },
            )
        output = sdk_result.final_output_as(
            BoundedSummary,
            raise_if_incorrect_type=True,
        )
        return check_domain_completion(output)
    except ToolTimeoutError:
        return failed_result("TOOL_TIMEOUT")
    except TimeoutError:
        return failed_result("RUN_TIMEOUT")
    except SourceQueryError:
        return failed_result("TOOL_FAILURE")
    except ModelBehaviorError:
        return failed_result("MODEL_BEHAVIOR")
    except Exception:
        logger.exception("unexpected worker failure")
        return failed_result("UNEXPECTED_FAILURE")
```

`ModelBehaviorError` is broader than invalid final output. A model can also trigger it by calling
a missing tool or producing malformed tool arguments. The fallback branch above therefore uses
`MODEL_BEHAVIOR`; only the matching error handler produces `INVALID_FINAL_OUTPUT`.

### 6. Assert the result first, then inspect diagnostics

Each abnormal-path test should assert the `WorkerResult` before matching any log:

```text
missing source → status == "incomplete" and errors contains SOURCE_MISSING
tool failure   → status == "failed" and errors contains TOOL_FAILURE
tool or run timeout → status == "failed" with separate stable codes
incomplete result → status == "incomplete" and retained answer/evidence still satisfies the result model's consistency rules
```

Also verify that Pydantic rejects these three objects: `completed` with an error, `failed` with an
answer, and a non-completed status without an error. Trigger the `max_turns` and
invalid-final-output handlers separately. Tests may replace `Runner.run` at its call site, but this
chapter does not build a general runner abstraction; M04 cleans up that boundary with dependency
injection.

Only after a result assertion fails should you inspect exception `run_data`, `new_items`, or a local
log to find which tool ran in which model turn. Diagnostics explain a failure; they do not decide
the externally visible status.

## Exercises

Answer the questions before expanding the reference answers.

### Concepts and code reading

1. What questions do `final_output`, `new_items`, and `raw_responses` answer?
2. Why can `final_output_as(..., raise_if_incorrect_type=True)` not prove task completion?
3. True or false: if `Runner.run` does not raise, the status should be `completed`.
4. What is the main difference between `incomplete` and `failed`?
5. Why does this chapter require a `completed` result to have an empty `errors` list?
6. Does `max_turns=6` limit model calls, the number of tool calls, or wall-clock time?
7. Which layer does a tool timeout protect, and which layer does a run-level timeout protect?
8. After an `invalid_final_output` handler returns an object, what does the SDK still do? Does it
   call the model again?
9. Why must the wrapper not classify every `ModelBehaviorError` as `INVALID_FINAL_OUTPUT`?
10. Why should abnormal-path tests assert `WorkerResult` before matching log text?

<details class="exercise-answers">
<summary>Reference answers</summary>

1. `final_output` is the final candidate result for the caller. `new_items` contains messages,
   tool calls, and tool outputs with SDK metadata. `raw_responses` contains each raw model response
   for provider-level diagnosis.
2. The helper checks only the Python runtime type. The application must still check requested
   source coverage, status/error consistency, and whether evidence supports the answer.
3. False. A missing source can produce a normally returned, schema-validated `incomplete` result.
4. `incomplete` has a trustworthy partial answer or evidence. `failed` has no safe domain output.
5. This chapter defines every `WorkerError` as a problem that blocks completion. The task cannot
   claim completion while such an error remains.
6. It permits at most 6 model calls. One turn includes tool calls caused by that model output. It
   does not separately limit tool calls within a turn, and it does not limit wall-clock time.
7. A tool timeout limits one asynchronous tool call. A run-level timeout limits elapsed time for
   the whole `Runner.run`.
8. The SDK validates the handler's value against the Agent's same `output_type`. The handler does
   not retry the model or replay tool calls.
9. The exception can also represent a missing tool or malformed tool arguments. Only the specific
   `invalid_final_output` handler reliably identifies a final-output error.
10. Callers depend on result fields and stable error codes. Logs and exception messages may change
    and may contain diagnostic information that must not be exposed.

</details>

### Lab: establish bounded runs and failure semantics

Build on the M01 data models and the two M02 read-only tools. You may modify
`src/evidence_worker/contracts.py` and add run-wrapper and test files. Do not rename the teaching
model above and treat it as the complete answer.

1. Add a required `status` to `WorkerResult`, allowing only `completed`, `incomplete`, and `failed`.
2. Define every entry in `errors` as a completion-blocking problem. Add deterministic validation:
   `completed` has no error; `incomplete` and `failed` have at least one error; `failed` has no
   answer or evidence.
3. Compare requested source IDs with returned evidence in application code. Return `incomplete`
   and `SOURCE_MISSING` for a gap instead of trusting a model-supplied `completed`.
4. Call `Runner.run` with `max_turns=6`. Use error handlers to convert the turn limit to
   `incomplete` and invalid final output to `failed`.
5. Wrap the full run in `asyncio.timeout(20.0)`. Keep the M02 query tool's 2-second per-call timeout.
6. Convert expected read-only query failures to an application-owned exception, then return
   `TOOL_FAILURE` at the wrapper boundary.
7. Handle `ToolTimeoutError`, run-level `TimeoutError`, other `ModelBehaviorError` cases, and a
   final unknown exception separately. Expose only stable codes and safe messages.
8. Without calling a real model, cover four groups: missing source, tool failure, timeout, and a
   valid but incomplete result. In the timeout group, assert both `TOOL_TIMEOUT` and `RUN_TIMEOUT`.
9. Also cover `MAX_TURNS`, `INVALID_FINAL_OUTPUT`, and the three status consistency rules.
10. Make every result directly serializable with `model_dump_json()`. The caller must decide what
    to do without parsing logs, exception text, or `new_items`.

Run the chapter tests first, then the complete repository checks:

```bash
uv run pytest tests/test_runner.py -q
uv run ruff check .
uv run pyright
uv run pytest
```

Completion criteria:

- the four groups—missing source, tool failure, timeout, and incomplete result—each produce a
  stable, assertable `WorkerResult`;
- `completed` cannot contain an error that prevented task completion;
- the 2-second tool timeout, 20-second run timeout, and 6-turn limit apply separately;
- invalid final output and other model behavior errors use different codes;
- an upstream caller can determine completion by reading only `status` and `errors`;
- tests require no API key, and all repository checks pass.

This chapter does not provide the complete lab implementation. The core material connects status
invariants to the exception wrapper. You must still apply them to your `TaskRequest`,
`WorkerResult`, source-coverage check, error constructors, and test scenarios.

## References

Last checked: 2026-08-02. Locked project version: `openai-agents==0.19.1`.

- [Current Agents SDK guide: overall positioning](https://developers.openai.com/api/docs/guides/agents)
- [`v0.19.1` Running agents: agent loop, turn limits, and errors](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/running_agents.md)
- [`v0.19.1` Results: final output and new items](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/results.md)
- [`v0.19.1` Runner and turn-limit source](https://github.com/openai/openai-agents-python/blob/v0.19.1/src/agents/run.py)
- [`v0.19.1` SDK exception source](https://github.com/openai/openai-agents-python/blob/v0.19.1/src/agents/exceptions.py)
- [`v0.19.1` run error handler source](https://github.com/openai/openai-agents-python/blob/v0.19.1/src/agents/run_error_handlers.py)
- [`v0.19.1` structured-output validation source](https://github.com/openai/openai-agents-python/blob/v0.19.1/src/agents/agent_output.py)
- [`v0.19.1` function-tool timeout source](https://github.com/openai/openai-agents-python/blob/v0.19.1/src/agents/tool.py)
- [`v0.19.1` Agent lifecycle example](https://github.com/openai/openai-agents-python/blob/v0.19.1/examples/basic/agent_lifecycle_example.py)
- [Python 3.12 `asyncio.timeout`](https://docs.python.org/3.12/library/asyncio-task.html#asyncio.timeout)

Changes to the examples: retain one asynchronous `Runner.run` from the official basic-run
documentation and lifecycle example; add the course's three-status rules, 6-turn limit,
20-second run-level timeout, stable error codes, and controlled error handlers; remove random
tools, handoffs, hooks, interactive input, sessions, streaming, retries, and the complete lab answer.
