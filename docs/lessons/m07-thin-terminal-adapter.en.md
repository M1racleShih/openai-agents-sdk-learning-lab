---
title: M07 · Thin terminal adapter
description: Use prompt-toolkit for input, one output owner for incremental answers, and an ANSI-free plain mode.
---

<p class="lesson-kicker">M07 · 90 minutes · terminal design + lab</p>

# Thin terminal adapter

<p class="lesson-deck">The terminal owns input, shortcuts, and display; workflow, conversation continuity, and failure semantics remain in the application use case.</p>

<div class="lesson-meta" aria-label="Lesson information">
  <span>prompt-toolkit 3.0.53</span>
  <span>Rich 15.0.0</span>
  <span>interactive + plain</span>
  <span>Default tests need no TTY</span>
</div>

## Learning outcomes

After this chapter, you should be able to:

- read asynchronous input, history, and limited shortcuts with `PromptSession.prompt_async()`;
- let one terminal component own stdout and the cursor during a run;
- flush token deltas in small, append-only batches;
- use Rich only for complete Markdown, tables, and limited status information;
- provide an ANSI-free `--plain` mode for SSH, redirection, and tests;
- translate Ctrl-C to Cancel while a run is active and exit only while idle;
- test rendering, batching, plain mode, and cancellation with a fake event source.

!!! abstract "Chapter boundary"

    The first version is not a full-screen TUI. It does not use Rich Live, redraw the full
    transcript, or let input and output components control the cursor concurrently. The terminal
    does not own the Agent loop, SDK Session, RunOutcome, or active-run registry. It calls M06.

## Core material

### 1. Presentation-adapter dependency direction

```text
prompt_toolkit input ─┐
                     ├─ Submit / Cancel → application use case
renderer ← events ───┘
```

Terminal code may import M06 commands, events, and use case. It must not import Agents SDK events,
`Runner`, `SQLiteSession`, or tool implementations. Interactive and plain modes construct the same
use case. Two workflows would eventually diverge in failure and conversation semantics.

### 2. PromptSession owns only input

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory


def make_prompt_session(history_path: str) -> PromptSession[str]:
    return PromptSession(history=FileHistory(history_path))


async def read_command(session: PromptSession[str]) -> str:
    return await session.prompt_async("maintenance> ")
```

The lab adds only limited shortcuts, such as clearing input or cancelling the current edit. Do not
hide business commands in key bindings. The history file contains submitted terminal input, so a
real application needs a published retention policy. Tests use `tmp_path`. Plain redirected mode
may disable persistent history so automated input is not retained unexpectedly.

Show a prompt only when no run is active. After submission, PromptSession yields the cursor and
the renderer owns output until the turn settles. Only then show the next prompt.

### 3. Batch deltas instead of redrawing per token

Each `MessageDelta` enters a small buffer. Flush after a byte/character threshold or a short time
threshold—for example 64 characters or 40 ms as initial UI parameters:

```text
delta → buffer → threshold reached → write(new_text) → flush
Final/Error → flush remainder → newline → completed metadata
```

Do not reconstruct the complete transcript per token or clear and redraw prior content. Redirected
output remains valid text, and slow SSH avoids cursor flicker. Tests inject a fake clock rather
than waiting with real `sleep()` calls.

Streaming output appends plain text and does not incrementally parse Markdown. Rich handles only
closed Markdown content, the completed evidence/provenance table, and limited status lines. Do not
redraw an answer at Final if the complete answer was already streamed; that duplicates the
transcript.

### 4. One object owns stdout and the cursor

Give the renderer a small output port such as `write(text)`, `flush()`, and `isatty()`. The
interactive renderer may use Rich `Console.print(Markdown(...))` or a `Table` after content is
complete. The plain renderer uses only a text writer. The terminal controller calls either one
sequentially.

This first-version structure is forbidden:

```text
PromptSession edits an input line
  while Rich Live refreshes status
  while a background task prints tokens
```

Three cursor owners corrupt input, tests, and redirected output. Concurrent input and output would
be a separate TUI design problem, not a hidden extension of this adapter.

### 5. Plain mode is a complete product path

`--plain` must:

- emit no ANSI escape sequences;
- depend on no terminal width, color, cursor movement, or real TTY;
- still convert input lines into Submit and retain the Ctrl-C rule;
- call the same application use case as interactive mode;
- append `MessageDelta` and use short text lines for tools and state;
- work over SSH, in `command | tee output.txt`, and in automated tests.

Setting only Rich `no_color=True` does not prove there are no ANSI controls. The plain renderer
uses a dedicated text writer, and tests assert that output contains no `\x1b`.

### 6. Run state determines Ctrl-C meaning

```text
no active run + Ctrl-C → exit terminal loop
active run + Ctrl-C    → Cancel(session_id, application_run_id)
                         → wait for cancelled outcome
                         → keep terminal open
```

The controller receives the current application run ID from M06 and sends Cancel. It does not call
`RunResultStreaming.cancel()` directly. During cancellation, print only one limited status line—
not a stack or complete accumulated object. A second Ctrl-C must not bypass application state and
report success; define and test stable behavior in the lab.

### 7. The renderer knows only application events

| Event | Interactive | Plain |
| --- | --- | --- |
| `MessageDelta` | Enter batching buffer | Enter the same batching buffer |
| `ToolStarted` | Short status line or spinner text | `[tool] name started` |
| `ToolFinished` | Completion class, no raw output | `[tool] name: outcome` |
| `EvidenceFound` | Add to completed Rich Table | `evidence: ref` |
| `RunStateChanged` | Limited status; no transcript redraw | `state: value` |
| `Final` | Flush and render completed metadata | Flush and print plain metadata |
| `Error` | Flush and render safe error | `error CODE: safe message` |

Use `match event.kind` and let pyright exhaust the union. An unknown event must not silently print
an SDK repr; treat it as a programming error during development.

### 8. Tests open no real TTY

A fake event source delivers events at fixed call boundaries; a fake writer records every
`write()`. Test that:

1. small deltas stay buffered before a threshold, then only new text is written;
2. Final and Error flush the remainder first;
3. written content is never redrawn;
4. complete plain output contains no `\x1b`;
5. raw tool output never reaches the writer;
6. Ctrl-C sends Cancel when active and exits when idle;
7. both modes preserve the same semantic information for one event sequence.

Test PromptSession through fake input or at the controller boundary; pytest needs no real TTY.
For Rich tables, assert allowed fields and essential text, not every space or terminal width.

## Exercises

1. Why can the terminal not consume `RunItemStreamEvent` directly?
2. Why should PromptSession yield the cursor during a run?
3. What do the character and time batching thresholds each solve?
4. Why is an incremental Markdown renderer fragile?
5. Why is Rich Live outside this first version?
6. Why is `no_color=True` insufficient proof of an ANSI-free mode?
7. Why should Final not redraw an already streamed answer?
8. Which application command should Ctrl-C send during an active run?
9. Why does a renderer assert allowed fields instead of comparing an SDK repr?
10. How does a fake clock make batching tests faster and deterministic?

## Lab: complete both thin terminal modes

1. Implement async input, test history, and limited shortcuts with
   `PromptSession.prompt_async()`.
2. Let the controller construct only Submit/Cancel and call the M06 use case.
3. Implement a delta buffer with injectable clock and writer.
4. Use Rich in the interactive renderer only for complete Markdown, tables, and limited state.
5. Do not use full-screen Rich Live or redraw the transcript.
6. Implement `--plain` and prove complete output has no ANSI.
7. Implement active and idle Ctrl-C behavior.
8. Cover renderer, batching, plain mode, cancellation, and errors with a fake event source.
9. Assert both modes preserve the same answer, status, and evidence references for one sequence.
10. Default tests must read no real TTY, API key, or network.

Completion criteria:

- PromptSession owns input and exactly one renderer owns output;
- deltas append in small batches without per-token transcript redraw;
- Rich renders only complete content and limited metadata;
- plain mode has no ANSI and reuses the same use case;
- Ctrl-C cancels when active and exits when idle;
- fake tests need no real TTY or model.

## Glossary

| Term | Course meaning |
| --- | --- |
| presentation adapter | Thin boundary that turns input into commands and events into display |
| batching | Combine neighboring deltas by a short time or size threshold, then append |
| append-only | Write new content without redrawing the transcript |
| plain mode | Equivalent terminal path with no ANSI and no TTY requirement |

## Version and official references

Last checked: 2026-08-11. Locked: `prompt-toolkit==3.0.53`, `rich==15.0.0`, and
`openai-agents==0.20.0`.

- [prompt-toolkit asynchronous prompts](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html)
- [prompt-toolkit history](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html#history)
- [Rich Markdown](https://rich.readthedocs.io/en/stable/markdown.html)
- [Rich tables](https://rich.readthedocs.io/en/stable/tables.html)
- [Python signal handling](https://docs.python.org/3/library/signal.html)

Changes to official examples: use only prompt-toolkit asynchronous input/history and Rich
rendering of complete content; add one output owner, delta batching, plain mode, and Ctrl-C command
translation. The learner still completes the terminal implementation.
