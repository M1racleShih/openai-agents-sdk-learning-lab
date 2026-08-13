---
title: M05 · Sessions, streaming, and cancellation
description: Preserve conversation continuity, stream natural-language output, and form a trustworthy result only after the stream fully settles.
---

<p class="lesson-kicker">M05 · 120 minutes · compatibility spike + lab</p>

# Sessions, streaming, and cancellation

<p class="lesson-deck">Separate the user-visible answer from the machine-readable outcome while still running exactly one Agent.</p>

<div class="lesson-meta" aria-label="Lesson information">
  <span>SDK v0.20.0</span>
  <span>3 continuity strategies</span>
  <span>2 cancellation modes</span>
  <span>Default tests stay offline</span>
</div>

## Learning outcomes

After this chapter, you should be able to:

- explain how one application turn relates to one `Runner.run_streamed()` call;
- compare `to_input_list()`, an SDK `Session`, and `previous_response_id`;
- preserve two-turn continuity with an injectable Session factory;
- distinguish raw response events, high-level run-item events, and the final
  `RunResultStreaming`;
- consume `stream_events()` to completion before forming the final `RunOutcome`;
- use both `cancel()` and `cancel(mode="after_turn")` correctly;
- test deltas, tool events, failures, and cancellation with a deterministic fake stream;
- verify structured-output and text-delta shapes against the target model in an explicit spike.

!!! abstract "Chapter boundary"

    This chapter selects one conversation strategy, one Agent, and one streamed Runner run. It
    adds no second Agent, second application-initiated model call, handoff, write tool, partial JSON
    parser, or general runtime abstraction. M06 translates application events; M07 renders them.

## Core material

### 1. One application turn maps to one streamed Runner run

An application turn starts with `Submit(session_id, text)` and ends after `stream_events()` has
finished and one final `RunOutcome` exists. It may contain several SDK model turns and read-only
tool calls. Those are parts of one Agent loop, not separate application runs.

```text
application turn
  → Runner.run_streamed(...)
  → 0..n raw/high-level stream events
  → stream fully drained
  → one settled RunOutcome
```

The last visible token means only that no later text has arrived yet. Tools, Session updates,
tracing, and runner state may still be settling. The reliable end point is normal completion of
the `async for`, or an exception from it that the application classifies.

### 2. Compare three continuity strategies; select one

| Strategy | Who owns history | Good fit | Course decision |
| --- | --- | --- | --- |
| `result.to_input_list()` | The application explicitly combines prior input and new items | Full control of the next input list | Compare only |
| SDK `Session` | Runner reads history before and writes it after each run | Local multi-turn terminal conversation | **Capstone choice** |
| `previous_response_id` | The Responses API continues from a server-side response ID | An application that chose server-side continuity | Compare only |

Do not mix these strategies on the capstone path; doing so makes ownership unclear and may
duplicate history. An SDK Session stores model-conversation continuity only. It is not the
authoritative store for `RunOutcome`, cancellation, application events, the source allowlist, or
audit records.

The capstone accepts a minimal Session factory instead of constructing `SQLiteSession` inside the
use case:

```python
from collections.abc import Callable

from agents import Session, SQLiteSession

SessionFactory = Callable[[str], Session]


def make_memory_session_factory() -> SessionFactory:
    sessions: dict[str, SQLiteSession] = {}

    def get_session(application_session_id: str) -> Session:
        return sessions.setdefault(
            application_session_id,
            SQLiteSession(application_session_id, db_path=":memory:"),
        )

    return get_session
```

Memory mode must reuse the same instance: constructing a fresh `:memory:` database loses the
previous turn. Use a SQLite file under a test temporary directory when persistence must be
inspected, but still inject it through the same factory. Never treat the SDK Session database as a
business ledger or UI transcript.

### 3. Raw deltas, run items, and final state answer different questions

`Runner.run_streamed()` returns `RunResultStreaming` immediately while the run progresses in the
background. Its consumer uses:

```python
from agents import RawResponsesStreamEvent, RunItemStreamEvent, Runner
from openai.types.responses import ResponseTextDeltaEvent

result = Runner.run_streamed(agent, user_text, session=session)

async for event in result.stream_events():
    if isinstance(event, RawResponsesStreamEvent) and isinstance(
        event.data, ResponseTextDeltaEvent
    ):
        on_text_delta(event.data.delta)
    elif isinstance(event, RunItemStreamEvent):
        on_run_item(event.name, event.item)
```

| Observation | Typical content | Application use |
| --- | --- | --- |
| `ResponseTextDeltaEvent` | Natural-language text delta | Translate to user-visible `MessageDelta` |
| `RunItemStreamEvent` | A complete message or tool item | Translate to stable tool/evidence events |
| `tool_called` | Tool-call item created | Record a tool-start classification |
| `tool_output` | Tool-output item created | Record finish classification without exposing raw output |
| `RunResultStreaming` | `is_complete`, `final_output`, `new_items`, and more | Read final state after stream completion |

Do not pass SDK event objects to the terminal. Do not expose raw tool output as a `ToolFinished`
payload; M06 emits only allowed fields and stable classifications.

### 4. Compatibility spike: structured final output is not display text

Verify two paths against the locked SDK and actual target model:

1. With `output_type=SpikeResult`, record the shape of `ResponseTextDeltaEvent.delta` and the type
   of settled `final_output`.
2. Without `output_type`, confirm that deltas compose into readable natural language and the
   settled `final_output` is the complete text.

Structured output constrains the final value to a schema. It does not promise that raw text
deltas are a human-readable answer. A target model may stream serialized JSON fragments. Do not
display those fragments and do not build a partial JSON parser that guesses brace boundaries.

The real spike is explicit opt-in: mark it `@pytest.mark.smoke`, require
`OPENAI_LEARNING_MODEL` and credentials, and record SDK version, model, date, and redacted event
samples. Default `uv run pytest` excludes it:

```bash
uv run pytest -o addopts= -m smoke tests/test_streaming_spike.py -q
```

### 5. The selected two-channel design

The capstone uses the smallest application-side composition and does not set a structured
`output_type` on the Agent:

```text
same Agent, same Runner.run_streamed call
  ├─ ResponseTextDeltaEvent → natural-language MessageDelta
  └─ application-owned tool results, provenance, errors, and settled final text
       → deterministic RunOutcome composition
```

`RunOutcome.answer` uses the settled complete natural-language final output. Its `status`,
`evidence`, `provenance`, and `errors` come from application-owned read-only tool results, the
context accumulator, and M03 mappings. This adds no model call outside that Agent loop and no
second Agent. A model claim such as “completed” cannot override missing sources or an exception.

Test these failure paths: missing final text, incomplete requested-source coverage, tool failure,
model failure, timeout, cancellation, and a result that still violates an invariant after the
stream ends. None may fall back to `completed`. If a target-model spike later proves a different
single-output shape naturally satisfies both channels, record the evidence before changing the
design.

### 6. Cancellation is a run operation, not a UI flag

`RunResultStreaming.cancel()` requests immediate cancellation.
`cancel(mode="after_turn")` lets the current SDK turn reach its boundary but starts no next turn.
Keep consuming `stream_events()` until it ends or raises a classified exception:

```python
result.cancel()                       # immediate
result.cancel(mode="after_turn")     # finish current turn boundary
```

The application retains the active `RunResultStreaming` or task reference. Setting a Boolean that
nothing consumes cancels nothing. Even after partial text or evidence is visible, a cancelled run
settles as `cancelled`; a run-level timeout settles as `timed_out`. Neither reports success.

### 7. Fake streams keep default tests deterministic

A fake need not reproduce every SDK internal. It implements only the protocol consumed by the use
case: asynchronous event iteration, cancellation-call recording, and a final value after settle.
Use a fixed event sequence:

```text
text delta("Check")
tool_called("read_maintenance_record")
tool_output(classification="ok", evidence_ref="device-a#2026-04")
text delta(" complete.")
stream end
```

Assert composed text, tool phases, the evidence reference, final status, and that `Final` is not
published until after stream end. Add separate sequences for tool error, model exception, timeout,
immediate cancellation, after-turn cancellation, and missing final text. Default tests must not
read an API key or construct a real network client.

## Exercises

1. Why may one application turn contain several SDK turns?
2. Where does history ownership live for `to_input_list()`, SDK Session, and
   `previous_response_id`?
3. Why must an in-memory SQLite factory cache instances?
4. What may remain unsettled after the last text delta?
5. How do `ResponseTextDeltaEvent` and `RunItemStreamEvent` differ in abstraction level?
6. Why is a structured-output delta not display text by default?
7. How does this course get natural language and `RunOutcome` from one model run?
8. Where do immediate and after-turn cancellation differ?
9. Why can partial displayed text not turn cancellation into completion?
10. What must a fake stream record to prove cancellation reached the active run?

## Lab: build the streaming compatibility and two-channel skeleton

1. Write an injectable Session factory using cached in-memory `SQLiteSession` by default and a
   temporary file in tests when needed.
2. Run two fake turns with one session ID and prove the second receives first-turn history.
3. Call `Runner.run_streamed()` once and consume every event.
4. Handle text delta, tool called, tool output, and settled final state separately.
5. Compose `RunOutcome` from application-owned data without parsing partial JSON.
6. Route immediate and after-turn cancellation to the active result and assert `cancelled`.
7. Bound the entire consumption path with `asyncio.timeout()` and assert `timed_out`.
8. Cover success, missing source, tool failure, model failure, timeout, cancellation, and
   incomplete result with fake streams.
9. Add the default-excluded real-model spike and record actual structured and text event shapes.
10. Commit no real model output, credentials, or complete trace—only a redacted conclusion and
    assertions.

Completion criteria:

- the capstone explicitly selects SDK Session and receives it through a factory;
- deterministic tests prove two-turn continuity for one session;
- natural-language deltas are visible and the final `RunOutcome` is machine-readable;
- the stream is always consumed to settle, and cancellation or timeout never becomes `completed`;
- default tests stay offline and the real-model spike is explicit;
- there is no second Agent, model call outside the Agent loop, or partial JSON parser.

This lesson does not provide the complete capstone implementation. The learner still writes the
factory, fake stream, outcome composer, and every abnormal-path test.

## Glossary

| Term | Course meaning |
| --- | --- |
| application turn | One Submit through one settled RunOutcome |
| SDK turn | One model call and its triggered tool work inside the Agent loop |
| settle | The stream has ended; Session, trace, and result state are readable |
| two-channel design | User text events and a machine-readable result from one run |

## Version and official references

Last checked: 2026-08-11. Locked: `openai-agents==0.20.0`.

- [Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents)
- [Results](https://developers.openai.com/api/docs/guides/agents/results)
- [Streaming guide](https://openai.github.io/openai-agents-python/streaming/)
- [Sessions guide](https://openai.github.io/openai-agents-python/sessions/)
- [`v0.20.0` run-result source](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/result.py)
- [`v0.20.0` stream-event source](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/stream_events.py)
- [`v0.20.0` session package](https://github.com/openai/openai-agents-python/tree/v0.20.0/src/agents/memory)

Changes to official examples: retain `run_streamed()`, `stream_events()`,
`ResponseTextDeltaEvent`, SDK Session, and both cancel modes; add public synthetic fixtures,
application-side `RunOutcome` composition, fake streams, and an opt-in compatibility spike; omit
multiple Agents, handoffs, write operations, and the complete capstone answer.
