---
title: M06 · UI-independent application use case and typed events
description: Isolate the Agents SDK from the terminal with Submit, Cancel, and a finite event set while retaining direct SDK access.
---

<p class="lesson-kicker">M06 · 105 minutes · design + lab</p>

# UI-independent application use case and typed events

<p class="lesson-deck">The application owns commands, events, failure classification, and the run lifecycle; the terminal submits commands and renders events.</p>

<div class="lesson-meta" aria-label="Lesson information">
  <span>SDK v0.20.0</span>
  <span>2 commands</span>
  <span>7 events</span>
  <span>1 Agent runtime</span>
</div>

## Learning outcomes

After this chapter, you should be able to:

- represent every allowed terminal intention with `Submit` and `Cancel`;
- model seven application events as a finite discriminated union;
- emit events asynchronously and return a final `RunOutcome` from the use case;
- translate raw and high-level SDK events into stable, UI-independent application events;
- keep every SDK event type out of the terminal;
- make `Cancel` operate on the active run instead of an unconsumed flag;
- deterministically test event order, failure semantics, and two turns in one session.

!!! abstract "Chapter boundary"

    The application use case may depend directly on the OpenAI Agents SDK. This chapter creates
    no general runtime interface. It adds no multiple Agents, handoff, approval, write tool, GUI,
    or event-bus framework. The event set contains only the seven events this terminal needs.

## Core material

### 1. Commands express user intent and carry no SDK objects

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Submit:
    session_id: str
    text: str


@dataclass(frozen=True, slots=True)
class Cancel:
    session_id: str
    application_run_id: str
```

The Submit session ID is an application correlation key. The use case creates a unique
application run ID, SDK Session, and trace ID for it. Cancel identifies one exact active run so an
old Ctrl-C cannot stop the next turn. Commands do not accept an `Agent`, `RunConfig`, SDK Session,
or stream event; the application composition root injects those dependencies.

### 2. Seven events form a closed union

Frozen dataclasses are the smallest useful representation. Every event has a literal `kind`,
session ID, and application run ID; payloads contain only allowed presentation data:

```python
from dataclasses import dataclass
from typing import Literal, TypeAlias


@dataclass(frozen=True, slots=True)
class MessageDelta:
    kind: Literal["message_delta"]
    session_id: str
    run_id: str
    text: str


@dataclass(frozen=True, slots=True)
class ToolStarted:
    kind: Literal["tool_started"]
    session_id: str
    run_id: str
    tool_name: str


@dataclass(frozen=True, slots=True)
class ToolFinished:
    kind: Literal["tool_finished"]
    session_id: str
    run_id: str
    tool_name: str
    outcome: Literal["ok", "error", "timeout", "cancelled"]


@dataclass(frozen=True, slots=True)
class EvidenceFound:
    kind: Literal["evidence_found"]
    session_id: str
    run_id: str
    evidence_ref: str


@dataclass(frozen=True, slots=True)
class RunStateChanged:
    kind: Literal["run_state_changed"]
    session_id: str
    run_id: str
    state: Literal[
        "starting", "running", "cancelling", "completed", "incomplete",
        "failed", "cancelled", "timed_out"
    ]


@dataclass(frozen=True, slots=True)
class Final:
    kind: Literal["final"]
    session_id: str
    run_id: str
    outcome: "RunOutcome"


@dataclass(frozen=True, slots=True)
class Error:
    kind: Literal["error"]
    session_id: str
    run_id: str
    code: str
    safe_message: str


ApplicationEvent: TypeAlias = (
    MessageDelta | ToolStarted | ToolFinished | EvidenceFound
    | RunStateChanged | Final | Error
)
```

`kind` lets pyright and pattern matching prove the union is exhausted. `ToolFinished` carries no
stdout, stderr, or SDK item. `EvidenceFound` carries a stable reference, not evidence text.
`Error` carries no exception object or original exception string. Detailed diagnosis remains in
redacted logs and traces.

### 3. An event sink supports both streaming and a final return

An async generator cannot conveniently deliver a business return value to its caller, so the
course uses a minimal async sink. The use case calls `await emit(event)` and the function itself
returns `RunOutcome`:

```python
from collections.abc import Awaitable, Callable

EventSink = Callable[[ApplicationEvent], Awaitable[None]]


async def execute_submit(command: Submit, emit: EventSink) -> RunOutcome:
    ...
```

This is not a general event bus. One terminal turn supplies one sink; a test supplies a fake sink
that appends to a list. A different presentation adapter could call the same use case later, but
the use case depends on no Rich, prompt-toolkit, stdout, or TTY.

### 4. Translation rules live in the application

| SDK observation | Application event | Filter rule |
| --- | --- | --- |
| `ResponseTextDeltaEvent` | `MessageDelta` | Emit only nonempty natural-language deltas |
| `RunItemStreamEvent(name="tool_called")` | `ToolStarted` | Tool name must be allowlisted |
| `RunItemStreamEvent(name="tool_output")` | `ToolFinished` | Emit only `ok/error/timeout/cancelled` |
| New evidence ref in controlled tool context | `EvidenceFound` | Emit stable references, deduplicated in discovery order |
| Use-case lifecycle change | `RunStateChanged` | Application state, not an SDK internal state name |
| Normal or incomplete settle | `Final` | Payload is a validated `RunOutcome` |
| Failure, timeout, or cancellation | `Error` | Fixed code plus safe message; return the matching outcome |

The terminal module must not import `RawResponsesStreamEvent`, `RunItemStreamEvent`, or
`ResponseTextDeltaEvent`. An SDK upgrade should affect the translator and compatibility tests,
not force renderer changes.

### 5. Event order is part of the application protocol

The minimum normal sequence is:

```text
RunStateChanged(starting)
RunStateChanged(running)
0..n × (MessageDelta | ToolStarted | ToolFinished | EvidenceFound)
RunStateChanged(completed | incomplete)
Final(outcome)
return the same outcome
```

For a successful tool, `ToolStarted` precedes its `ToolFinished`; evidence discovered from that
result follows `ToolFinished`. Failure, timeout, and cancellation emit the matching terminal
`RunStateChanged` and then one `Error`, not `Final`. Every path returns a `RunOutcome` with the same
classification.

`MessageDelta` may interleave before or after tool events. Do not specify that a model always talks
before it uses a tool. Tests fix fake input and assert order for that input instead of treating a
real model's behavior as protocol.

### 6. Cancel must reach the active object

The application keeps a small active-run registry keyed by application run ID. Each value contains
at least the active `RunResultStreaming` and its `asyncio.Task`. Registration happens at start and
cleanup happens in `finally`:

```text
Submit → create task/result → register active run → consume → finally unregister
Cancel → look up exact run → emit cancelling → result.cancel() → await task settle
```

If the run has ended, Cancel returns stable `RUN_NOT_ACTIVE` and never silently cancels a later
command. On timeout, request cancellation from the active result before awaiting settle. If the
task itself must be cancelled, still catch and classify `CancelledError`. An unconsumed
`cancel_requested = True` does nothing.

### 7. Deterministic tests focus on use-case behavior

Inject fixed inputs through a fake stream and fake Session factory. Cover at least:

| Scenario | Required assertion |
| --- | --- |
| Normal completion | Ordered deltas; Final after terminal state; returned outcome is identical |
| Tool failure | started → finished(error) → failed → Error; no Final |
| Model failure | `failed` plus stable `MODEL_FAILURE`; no exception text leaks |
| Timeout | Active result is cancelled; final classification is `timed_out` |
| Explicit cancel | `cancelling` then `cancelled`; cancellation reaches the current object |
| Incomplete result | `incomplete` plus Final; missing-source code is directly readable |
| Two turns in one session | Factory receives the same ID and history continues into turn two |

Also test that Cancel with a different run ID does not affect the active run, and the registry is
cleaned after an exception. Default tests use fakes and create no real model client.

## Exercises

1. Why should Submit not carry an `Agent` or `RunConfig`?
2. What type-checking value does a discriminating `kind` add?
3. Why does `ToolFinished` not return an SDK tool-output item?
4. Why does this course choose an async sink instead of returning `RunOutcome` from an async
   generator?
5. Which layer should know `ResponseTextDeltaEvent`?
6. How should Final relate to the function's returned `RunOutcome`?
7. Why can a tool-failure path not emit Final before Error?
8. Why is the Cancel registry keyed by run ID, not only session ID?
9. Why wait for stream settle after a timeout?
10. How can a test prove Cancel is not an unconsumed Boolean?

## Lab: implement the application-use-case skeleton

1. Define Submit, Cancel, seven events, and the closed union.
2. Define `EventSink` and `execute_submit(...)->RunOutcome`.
3. Call the streamed Agents SDK runner directly; add no runtime interface.
4. Translate M05 raw/high-level events and filter their payloads.
5. Build the minimal active-run registry so Cancel calls cancel on the current result.
6. Connect M03's five completion classes to terminal state, Final/Error, and the return value.
7. Clean the active registry in `finally` on every path.
8. Use fake streams to cover order, success, tool failure, model failure, timeout, cancellation,
   and incomplete results.
9. Use a fake Session factory to cover two continuous turns in one session.
10. Use pyright to ensure a future renderer exhausts every event `kind`.

Completion criteria:

- terminal code imports no SDK event type;
- one Submit emits an assertable sequence and returns the same final outcome;
- Cancel reaches the active result/task, and a wrong run ID affects no other run;
- callers distinguish all five completion classes without parsing logs;
- two turns in one session are continuous and default tests stay offline;
- there is no general runtime interface, event bus, or complete capstone answer.

## Glossary

| Term | Course meaning |
| --- | --- |
| command | A finite intention sent from a presentation adapter to the application use case |
| application event | Application-owned, SDK-independent, exhaustive UI output |
| active run | The streamed result and task currently addressable by Cancel |
| event sink | An async callback for one application event, not a general message system |

## Version and official references

Last checked: 2026-08-11. Locked: `openai-agents==0.20.0`.

- [Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents)
- [Results](https://developers.openai.com/api/docs/guides/agents/results)
- [Streaming guide](https://openai.github.io/openai-agents-python/streaming/)
- [`v0.20.0` stream events](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/stream_events.py)
- [`v0.20.0` run results and cancellation](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/result.py)
- [Python dataclasses](https://docs.python.org/3/library/dataclasses.html)

Changes to official examples: translate only the deltas and tool items this course needs; add
finite commands, stable events, active-run cancellation, and a returned `RunOutcome`. The learner
still completes the connecting code and tests.
