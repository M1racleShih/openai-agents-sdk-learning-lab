# OpenAI Agents SDK: Shortest Practical Learning Path

[中文](LEARNING_PLAN.md)

## Goal and audience

This route is for engineers who are proficient in Python and understand common Agent concepts but
have not built an AI application. It does not survey the full SDK. After roughly 11–13 hours, you
should be able to begin building this minimum application:

```text
user
  → thin terminal adapter
  → UI-independent application use case
  → one OpenAI Agents SDK Agent
  → approved read-only sources and read-only CLI/service tools
  → typed application events, a structured RunOutcome, and a streamed user answer
```

After the route, you should be able to:

- explain the relationship between one application turn and one SDK run;
- use one `Agent` and `Runner` as the only agent loop;
- select a model explicitly instead of relying on the SDK default;
- define requests, source provenance, errors, and structured results with Pydantic;
- build read-only fixture, simulated-service, and constrained CLI tools;
- distinguish completed, incomplete, failed, cancelled, and timed-out work;
- continue two turns with a Session and stream user answers plus tool progress;
- translate SDK events into a finite, stable, UI-independent application event set;
- build interactive and plain terminals with prompt-toolkit and Rich;
- keep default tests offline with fake runners, streams, and event sources;
- complete explicit real-model and real-terminal smoke runs.

This means you can begin the minimum application. It does not mean the application is production
ready.

## Responsibility split

| Layer | Owns | Does not own |
| --- | --- | --- |
| Agents SDK | Agent loop, tool orchestration, sessions, streaming, traces | Domain completion, source approval, terminal UI |
| Application | Use cases, commands, typed events, failure classification, minimal audit metadata | A second Agent runtime or general runtime framework |
| Terminal adapter | Input, shortcuts, batched refresh, Markdown/table rendering | Workflow, SDK Session, authoritative run state |

A Session preserves conversation continuity, a Trace preserves an observable path, and terminal
state serves the current presentation. The application's `RunOutcome` is the authoritative run
conclusion; the application must explicitly persist any necessary business record.

## Scope

| Must learn | Explicitly excluded |
| --- | --- |
| `Agent`, `Runner.run`, `Runner.run_streamed` | Handoffs and agents-as-tools |
| `output_type`, Pydantic, application-owned `RunOutcome` | Multiple Agents |
| `RunContextWrapper` and source provenance | Human approvals and write operations |
| Local read-only `function_tool` | SandboxAgent |
| `RunConfig`, tracing, and redacted records | GUI, Realtime, and voice |
| SDK Session and one capstone strategy | General runtime abstractions |
| Streaming events, cancellation, settlement | Automatic routing, failover, and a complete eval platform |
| prompt-toolkit, Rich, and plain mode | Production deployment and real private data integration |

Every external capability remains read-only. The final two-channel path uses deterministic
application-side composition, not a dedicated result-submission tool: the Agent streams natural
language while the application derives status, provenance, evidence, and errors from controlled
tool results and the settled run.

## How to learn

One project evolves across the route. Lessons follow “Learning outcomes → Core material →
Exercises → Lab → Completion criteria → Version and official references.” Write code only when
behavior must be observed. Lessons provide minimal interfaces, event mappings, and test skeletons,
not a complete capstone implementation.

Every chapter checks interfaces against official sources for `openai-agents==0.20.0`. A third-party
endpoint's compatibility requires an explicit smoke test; the label “OpenAI-compatible” is not
evidence by itself.

## Modules and completion criteria

### M00: First observable Agent (45 minutes)

Learn the SDK/Responses responsibility split, `Agent`, `Runner.run`, the agent loop, `RunResult`,
and traces. Run one explicitly modeled Agent and find the run in the Trace viewer.

Complete when you can explain that the SDK advances the loop while the application defines its
capability boundaries, and that the final product has one SDK Agent runtime.

### M01: Structured results and local context (75 minutes)

Learn `TaskRequest`, `Evidence`, `WorkerError`, `WorkerResult`, `output_type`, strict JSON Schema,
`final_output_as`, and the boundary between model input and local `RunContextWrapper` data.
Recognize that a final structured result and a streamed user-visible answer are separate interface
problems; do not solve both yet.

Complete one structured single-Agent run. The result must serialize directly, while loggers,
paths, clients, and credentials remain outside model context.

### M02: Read-only tools and source boundaries (105 minutes)

Learn function-tool schemas and errors; `ApprovedSource` / `SourceProvenance` with `source_id`,
`revision`, and `sha256`; fixture allowlists, resolved paths, checksums, and minimal return values;
read-only service-query limits; and a constrained read-only CLI adapter.

The CLI lab uses `asyncio.create_subprocess_exec`, never `shell=True`. Fix the executable and
read-only subcommands; validate arguments; allowlist environment variables; bound time, stdout,
and stderr; and never expose credentials, a complete environment, or unbounded raw output to the
model.

Complete when the tools have no external write capability, provenance is reviewable, failures are
not disguised as data, and direct tests call no model.

### M03: Bounded runs and truthful failures (75 minutes)

Distinguish `RunResult`, `new_items`, `raw_responses`, and domain `RunOutcome`. Bound one tool call,
model turns, and total elapsed time. Define `completed`, `incomplete`, `failed`, `cancelled`, and
`timed_out`, plus stable reasons/codes that do not expose SDK exception text.

Complete when failure, cancellation, timeout, and incomplete work can never become `completed`,
and callers need no log parsing.

### M04: Traces, minimal metadata, and deterministic tests (60 minutes)

Learn `workflow_name`, `trace_id`, `group_id`, `trace_include_sensitive_data=False`; distinguish
application session IDs, application run IDs, and trace IDs; and design `RunRecord` with
provenance, tool start/finish classifications, final completion, and evidence references.

Inject the runner at its call site, write only minimal records, and exclude `smoke` by default.
Do not store credentials, complete prompts, complete sources, unbounded tool output, or sensitive
user content.

### M05: Sessions, streaming, and cancellation (120 minutes)

Learn that one application turn maps to one `Runner.run_streamed`; compare `to_input_list()`, SDK
Session, and `previous_response_id`; choose an injectable Session factory backed initially by a
temporary SQLiteSession; and distinguish `ResponseTextDeltaEvent`, `RunItemStreamEvent`,
`tool_called`, and `tool_output`.

Consume `stream_events()` until it ends before treating the run as settled. Learn `result.cancel()`
and `result.cancel(mode="after_turn")`.

Run an explicit compatibility spike with the locked SDK and target model. Record the actual shape
of `output_type` plus raw text deltas. Never display structured JSON deltas or implement a partial
JSON parser.

The capstone uses one tested dual channel: the Agent's final message stays natural language and
produces `message_delta`; the application deterministically composes `RunOutcome` from controlled
tool results, the context accumulator, exception mapping, and settled final text. There is one
Agent and one Runner run, with no result-submission tool or model call outside that Agent loop.

Complete when fake-stream tests cover normal settlement, incomplete source coverage,
failures, timeouts, and both cancellation modes. Real-model spike and smoke tests are opt-in.

### M06: UI-independent application use case and typed events (105 minutes)

Define `Submit` and `Cancel`, plus `MessageDelta`, `ToolStarted`, `ToolFinished`, `EvidenceFound`,
`RunStateChanged`, `Final`, and `Error`. The application translates SDK raw and high-level events;
the terminal never sees SDK event objects. The use case emits events asynchronously and returns a
final `RunOutcome`.

Depend directly on the Agents SDK; do not create a general runtime interface. `Cancel` must act on
the current `RunResultStreaming` or running task, not set an unread Boolean.

Complete when tests cover event order, success, tool/model failure, timeout, cancellation,
incomplete results, and two consecutive turns in one session.

### M07: Thin terminal adapter (90 minutes)

Use `PromptSession.prompt_async()` for input, history, shortcuts, and Ctrl-C. Use Rich only for
completed Markdown, tables, and limited status. Batch token deltas into append-only refreshes; do
not redraw the transcript per token or use full-screen Rich Live in the first version. Exactly one
component owns stdout/cursor at a time.

Interactive and ANSI-free `--plain` modes use the same M06 use case. Ctrl-C becomes `Cancel` while
a run is active and exits only while idle. Test the renderer, batching, plain mode, and cancellation
with a fake event source and no real TTY.

### M08: Public capstone and readiness review (75 minutes)

Build a user-facing, single-Agent, read-only terminal assistant that inspects maintenance records
for fictional devices. Every source, device name, and simulated CLI response is public synthetic
fixture data.

Acceptance:

1. Interactive input receives a streamed natural-language answer.
2. The same use case returns a structured `RunOutcome`.
3. An SDK Session supports two consecutive turns.
4. Only the minimum allowlisted sources are loaded.
5. Read-only CLI/query tools run on demand.
6. Source provenance is recorded.
7. A trace correlates with redacted application metadata.
8. Success, missing sources, tool failure, model failure, timeout, cancellation, and incomplete
   results are distinguishable.
9. Plain and interactive modes use the same use case.
10. There are no writes, handoffs, multiple Agents, approvals, GUI, or general runtime framework.
11. Default tests make no network call.
12. One explicit real-model smoke run and one real-terminal run are completed.

The readiness review requires a 15-minute architecture explanation, one small cross-layer change
without the answer, all automated checks, real-model and terminal smoke runs, and an explanation
of why Session, Trace, application `RunOutcome`, and terminal state are different.

The lesson does not provide the complete capstone implementation. The learner must assemble it
and preserve verification evidence.

## Suggested schedule

- Session 1, about 3 hours 45 minutes: M00–M02.
- Session 2, about 3 hours 15 minutes: M03–M04 and the first half of M05.
- Session 3, about 3 hours 45 minutes: the second half of M05 through M07.
- Session 4, about 1 hour 15 minutes: M08.

Total: about 12.5 hours. Waiting time for real-model and terminal smoke runs is not study time.

## Version and environment policy

- Python 3.12 and `uv`;
- `openai-agents==0.20.0`, `prompt-toolkit==3.0.53`, and `rich==15.0.0`;
- `uv.lock` is the reproducibility source;
- model IDs are always explicit;
- API keys come only from environment variables or a local secret facility;
- default `pytest` excludes real-model smoke tests;
- every SDK upgrade rechecks Agent, Runner, structured output, function_tool, RunConfig, tracing,
  sessions, streaming, cancellation, and event interfaces.

The official 0.20.0 release changes the implicit default model and includes an MCP dependency
migration. The course relies on neither the default model nor MCP, so neither changes its design.

The upgrade audit from the prior lock confirms that the course's `Agent`/`output_type`,
`Runner.run`, `Runner.run_streamed`, `function_tool` timeout, `RunConfig` tracing fields,
`SQLiteSession`, stream events, and both cancel modes remain available. The new optional
tool-name-collision policy in `RunConfig` does not change any course call. The current versions and
these public entry points are guarded by `tests/test_dependency_baseline.py`.

## Sources

Last checked: 2026-08-11. Locked version: `openai-agents==0.20.0`.

- [Agents SDK overview](https://developers.openai.com/api/docs/guides/agents)
- [Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents)
- [Results and state](https://developers.openai.com/api/docs/guides/agents/results)
- [Integrations and observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability)
- [Python SDK streaming](https://openai.github.io/openai-agents-python/streaming/)
- [Python SDK sessions](https://openai.github.io/openai-agents-python/sessions/)
- [Python SDK v0.20.0 source and examples](https://github.com/openai/openai-agents-python/tree/v0.20.0)
- [Official v0.20.0 release](https://github.com/openai/openai-agents-python/releases/tag/v0.20.0)

Each lesson selects the minimum sources for its objective and records exact references. Learners
do not need to read all official documentation first.

## Start here

Open the [English M00 lesson](docs/lessons/m00-first-agent.en.md) or
[Chinese lesson](docs/lessons/m00-first-agent.md). M00 remains `in_progress`; every later module
remains `pending` until the learner personally completes its lab and verification.
