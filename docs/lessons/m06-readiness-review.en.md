---
title: M06 · Target-project readiness review
description: Use an explanation, a small change, automated checks, and a real run to decide whether you can begin target-project feature development.
---

<p class="lesson-kicker">M06 · 45 minutes · explanation + live change</p>

# Target-project readiness review

<p class="lesson-deck">Do not treat “the code is finished” as readiness. Explain control ownership, change one boundary, and prove the result with tests and a real run.</p>

<div class="lesson-meta" aria-label="Lesson information">
  <span>SDK v0.19.1</span>
  <span>10 review questions</span>
  <span>4 readiness gates</span>
  <span>1 real smoke run</span>
</div>

## Learning outcomes

After this chapter, you should be able to:

- explain the data flow between an upstream call, the process entry point, `Runner`, the model,
  tools, and the structured return in 15 minutes;
- identify what each layer controls and what it cannot decide for the next layer;
- explain which layer first detects an invalid request, missing source, tool failure, tool timeout,
  turn limit, run timeout, and invalid final output;
- add one field derived from existing read-only data and complete its schema, deterministic tests,
  and process-level assertions during the review;
- list the boundaries that must be replaced when the generic worker joins the target project, and
  the safety constraints that must remain;
- use default automated checks to prove that the change did not break existing paths;
- complete one real-model smoke run with public synthetic sources and review it by `trace_id`;
- distinguish “ready to start target-feature development” from “production-ready.”

!!! abstract "Chapter boundary"

    M06 is a capability review, not a new architecture chapter or a production launch approval. It
    does not add sessions, handoffs, write tools, a general multi-agent framework, or a new service
    dependency. Change only one small field or one read-only tool during the review; do not refactor
    the M05 worker.

## Core material

### 1. All four forms of evidence must pass

“I understand it” does not prove that you can change the worker independently. This chapter accepts
four forms of reviewable evidence:

| Gate | What to do | Passing signal |
| --- | --- | --- |
| Explanation | Explain input to output in 15 minutes, including failure ownership | Without the lesson, you can explain data, control ownership, and stopping points |
| Small change | Add one read-only field or tool and its tests | Schema, result, and process protocol change together without broader permissions |
| Automated checks | Run type checking, static checks, and default tests | Every command exits with `0`; default tests make no real model call |
| Real run | Run one complete path with public synthetic sources | The output is schema-valid JSON and the run can be found by `trace_id` |

All four must pass on the same final version. If you run the smoke test and then change the code,
the earlier run is not final evidence. When a gate fails, record the failure and return to the
corresponding chapter. Do not describe partial success as “ready.”

### 2. Explain how data moves before naming SDK components

The 15-minute explanation follows one main path:

```text
the upstream program prepares one TaskRequest JSON object
  → the process entry point reads and validates it
  → the application builds model input and local WorkerContext
  → Runner advances the loop between the model and read-only tools
  → the SDK produces and validates structured final output
  → the application checks source coverage and status invariants
  → the process writes one WorkerResult JSON object and the matching exit code
  → the upstream program decides to use the result, retry, or stop
```

For every step, answer three questions: who reads the data, who can change control flow, and who
checks the result. The following table is the minimum:

| Layer | Reads | Controls | Passes to the next layer |
| --- | --- | --- | --- |
| Upstream program | Request and JSON Schema | Whether to start, retry, or stop | One request object |
| Process entry point | Standard input or a UTF-8 file | Input validity, standard streams, and exit code | A validated `TaskRequest` |
| Application wrapper | Request, local dependencies, and run configuration | Prompt, tool list, timeout, and status invariants | Model input, `WorkerContext`, and `RunConfig` |
| `Runner` | Starting Agent and input | Model/tool loop, turn count, and stopping | A `RunResult` or SDK exception |
| Read-only tools | Constrained arguments and local context | Read-only access, allowlist, and per-call timeout | A result or explicit failure |
| Application wrapper | `final_output`, exceptions, and source coverage | Stable status, error codes, and minimal record | A valid `WorkerResult` |
| Upstream program | JSON, status, errors, and exit code | The next business action | Nothing enters the worker's internal loop |

`Runner` advances the loop. It does not own source permissions, credentials, persistent state, or
domain completion criteria. `output_type` validates the final output against a schema, but it does
not prove that every requested source was read. Explaining both points shows that you have not mixed
SDK capabilities with application responsibilities.

### 3. For every failure, identify both detection and external representation

One failure often passes through two layers: the component closest to the cause detects it, and the
application wrapper turns it into a stable `WorkerResult`. In the review, do not merely recite error
codes. Explain both actions.

| Scenario | Layer that first detects it | How the application represents it externally |
| --- | --- | --- |
| Invalid JSON or wrong field type | `TaskRequest.model_validate_json(...)` in the process entry point | `failed`, `INVALID_REQUEST`, exit code `1` |
| Path escapes the allowed root or argument is outside the allowlist | Ordinary code in a read-only tool | Map to a stable tool error; do not access the target resource |
| A requested source does not exist | The source tool reports it first; the wrapper then checks coverage | With a trusted partial result: `incomplete`, `SOURCE_MISSING`, exit code `2` |
| Read-only query fails | Query tool or client | `failed`, `TOOL_FAILURE`, exit code `1` |
| One tool call times out | Tool timeout boundary | `failed`, `TOOL_TIMEOUT`, exit code `1` |
| Run exceeds `max_turns` | `Runner` reaches the turn limit | `incomplete`, `MAX_TURNS`, exit code `2` |
| Complete run exceeds 20 seconds | Application's run-level timeout | `failed`, `RUN_TIMEOUT`, exit code `1` |
| Final output has the wrong structure or runtime type | SDK output parsing or `final_output_as(...)` check | `failed`, `INVALID_FINAL_OUTPUT`, exit code `1` |
| Structure is valid but source coverage is insufficient | Deterministic domain checks in the application | `incomplete` with a stable error, exit code `2` |

Error strings, stack traces, and raw input may contain caller data. The wrapper needs to record only
fixed event names, `trace_id`, status, and error codes. The upstream program reads JSON to choose its
next action; it should not infer task status by parsing logs.

### 4. The live change must cross real boundaries and remain small

Prefer an output field derived from existing read-only data, such as an evidence category. This is
a better live review than adding a service client: it still checks the contract, data movement,
serialization, and tests without expanding permissions or adding network failures.

Make the change in this order:

1. Write a failing test that requires the new field in the result schema, serialized JSON, and the
   process-level success scenario.
2. Add the field to the Pydantic model that owns the data and decide whether it is required.
3. Populate it from an existing read-only tool result or deterministic local code, not from a
   credential, logger, or private path.
4. Change Agent instructions only if the model must produce the field. When ordinary code can
   determine it, do not add model work.
5. Add assertions for invalid values, serialization round trips, and process output.
6. Run every default check, then run the real smoke test.

If you add a read-only tool instead, make it do one thing: define narrow arguments, use an existing
read-only dependency from local `WorkerContext`, set a per-call timeout, and directly test success,
boundary rejection, and underlying failure. Do not add a new client, cache, retry framework, or
write operation during the 45-minute review.

!!! tip "How to tell whether the change is small enough"

    You should be able to finish the change in about 15 minutes and use the remaining time to run
    tests and explain its effects. If it requires rewriting the result contract or process entry
    point, the change is too large or M05's boundaries are not yet stable.

### 5. State what changes and what remains when joining the target project

A generic worker does not automatically fit a target project after a few environment-variable
changes. Write a boundary list first, then find the actual owner of each item in the target project.
Do not put a company name, private address, real credential, or private source content in the list.

| Boundary | Replace or confirm during integration | Constraint that must remain |
| --- | --- | --- |
| Call method | Subprocess, task queue, or in-process call; who creates the request | Input, output, and timeout for one call remain explicit and testable |
| `TaskRequest` | Target task identifiers, questions, and source references | Validate before use; requests cannot inject local dependencies |
| `WorkerResult` | Answer, evidence, and error fields the downstream system needs | Status invariants remain stable; downstream code does not parse free text for completion |
| Source tool | Target source location, identity, and access interface | Deny by default; read-only; paths or identifiers use an allowlist |
| Query tool | Target read-only client and allowed query arguments | Per-call timeout; exceptions are not disguised as normal data |
| Model configuration | Explicit model, provider settings, and credential source | Credentials stay in local context or environment and never enter the prompt |
| Run budget | Turn count and total deadline allowed by the target system | Both `max_turns` and a run-level timeout remain |
| Error mapping | Stable error codes the target project must recognize | Cause, status, and exit behavior remain consistent and assertable |
| Tracing | Workflow name, correlation identifier, and export destination | Sensitive model and tool content stays disabled; `trace_id` remains correlatable |
| Minimal record | Storage location, retention period, and access permissions | Do not store prompts, complete answers, raw tool output, or exception text |
| Test boundary | How the target project injects a fake runner and fake read-only client | Default tests make no real model or service call |
| Retry ownership | Which errors the upstream program retries | The worker does not hide failures; repeat calls still have cost and audit records |

“Must remain” does not require the target project to keep the same filenames. The target
implementation must preserve the same observable behavior and safety boundaries.

### 6. The 15-minute explanation has a fixed time box

Ask another engineer to keep time and interrupt with questions. Use this order; the parts total
exactly 15 minutes:

1. 2 minutes: show the request and result schemas, plus the three statuses and exit codes.
2. 4 minutes: follow one successful path and explain data and control ownership.
3. 3 minutes: choose failures from three different layers and explain who detects, who maps, and how
   the caller responds.
4. 2 minutes: show what the redacted trace and minimal record each store.
5. 2 minutes: show what fake-runner deterministic tests and a real smoke run prove separately.
6. 2 minutes: show the target-project boundary list and identify the first interface to replace.

The reviewer may change one condition, such as “the source exists, but the query times out.” Follow
the existing path to its result; do not invent a new status or retry rule during the explanation.

### 7. Automated checks and a real run provide different evidence

Run the default checks first:

```bash
uv run ruff check .
uv run pyright
uv run pytest
```

These commands should cover ordinary code, type boundaries, schemas, status invariants, and the
process protocol without making a real model request. Then configure the model and credentials
explicitly and run once with public synthetic sources:

```bash
uv run python -m evidence_worker.cli fixtures/requests/complete.json
```

Verify that standard output contains one `WorkerResult` JSON object, status is `completed`, and the
exit code is `0`. Use the `trace_id` in the minimal record to inspect model turns, read-only tool
order, and the sensitive-content setting. Do not copy an API key, raw prompt, tool output, or private
source into the review record.

Default tests prove that listed scenarios are stable under controlled input. One real run proves
only that the current model, configuration, tools, and process entry point connected successfully
once. Passing both still does not prove capacity, long-term reliability, security review, or
production deployment.

### 8. When a gate fails, return only to the chapter it exposes

| Evidence that failed | Return to |
| --- | --- |
| Cannot distinguish model input from local context | M01 |
| Cannot prove tools are read-only, paths are constrained, or timeouts work | M02 |
| Status, errors, or stopping conditions contradict each other | M03 |
| Default tests can reach the network, or traces and records contain sensitive content | M04 |
| JSON, standard streams, exit codes, or the end-to-end path are unstable | M05 |

After the correction, repeat all four gates. Record “ready to start target-feature development”
only when the explanation, small change, automated checks, and final-version real smoke run all
pass. This conclusion permits integration work to begin; it does not say that the worker is
production-ready.

## Exercises

Answer the questions before expanding the reference answers.

### Concepts and code reading

1. Why are complete code and one successful run still insufficient to pass M06?
2. What does `Runner` control, and what does application code still control?
3. Why does a failure review identify both the layer that first detects the problem and the layer
   that represents it externally?
4. After a source tool reports a missing source, why does the application wrapper still check
   coverage and decide `incomplete`?
5. Why should the live change prefer a field derived from existing read-only data?
6. If ordinary code can determine a new field, why should the model not generate it?
7. May the target project change the process call method? Which constraints must remain?
8. What do default automated tests and one real smoke run prove separately?
9. True or false: after all four gates pass, the worker is production-ready.
10. If the result model changes after the last smoke run, may that earlier smoke run remain the
    final evidence?

<details class="exercise-answers">
<summary>Reference answers</summary>

1. M06 also requires the learner to explain control ownership independently, make one small live
   change, pass automated checks, and complete a real run on the same final version. Existing code
   may have been copied, and one success does not cover failure paths.
2. `Runner` advances the model/tool loop and enforces the turn limit. The application still controls
   tool implementation and permissions, input validation, timeouts, domain status, records, and the
   external protocol.
3. The component closest to the cause can identify the specific problem, while the application
   wrapper gives callers a stable representation across exceptions. Mixing them hides failures or
   makes upstream code depend on SDK internals.
4. The tool can report only that one read failed. The wrapper knows which sources the request
   required and whether the existing result is trustworthy, so it decides whether the whole task
   is incomplete.
5. The change crosses model, schema, serialization, and test boundaries without requiring broader
   permissions or a new service.
6. A value determined by ordinary code is more stable and easier to test, and it does not spend a
   model call guessing an existing fact.
7. Yes. The target project may use a queue or an in-process call, but input and output contracts,
   validation, timeout, status, and testable behavior must remain explicit.
8. Default tests prove that listed scenarios repeat under controlled input without reaching the
   network. A real smoke run proves that the current model, configuration, tools, and entry point
   connected successfully at least once.
9. False. Passing means you can start target-feature development. Capacity, long-term reliability,
   security review, and deployment still require separate verification.
10. No. A result-model change can alter output and serialization, so rerun the smoke test on the
    final version.

</details>

### Lab: complete one target-project readiness review

Complete these tasks on the same worker finished in M05. Do not copy a new worker or add another
Agent architecture in this chapter.

1. Ask another engineer to keep time. In 15 minutes, explain a successful path, failures from three
   different layers, redacted observation, both test types, and the first integration boundary.
2. Let the reviewer change one failure condition and explain the resulting status, stable error,
   and exit code live.
3. Choose one small field derived from existing read-only data. Add a failing test first, then change
   the model, data path, schema, and process-level assertion. If you choose a tool, add only one
   narrow read-only tool and directly test its three tool paths.
4. Write the target-project boundary list. Cover at least the call method, request, result, source
   tool, query tool, model configuration, run budget, error mapping, tracing, minimal record, test
   boundary, and retry ownership.
5. Run `uv run ruff check .`, `uv run pyright`, and `uv run pytest`.
6. Configure a model explicitly and run `uv run python -m evidence_worker.cli
   fixtures/requests/complete.json` once with public synthetic sources.
7. Validate one JSON object, `completed`, and exit code `0`; then use `trace_id` to inspect model
   turns, tool calls, and the sensitive-content setting.
8. Record evidence for each of the four gates and any open issue. Do not record secrets, private
   names, real addresses, or raw source material.

Completion criteria:

- the 15-minute explanation does not depend on the lesson and identifies data, control ownership,
  stopping points, and failure ownership layer by layer;
- one small change crosses the contract, implementation, schema, and deterministic tests without
  broadening read permissions;
- the target-project boundary list states who replaces every item and which constraints remain;
- all three default checks pass without making a real model call;
- the final-version real smoke run uses public synthetic sources and returns one `completed` JSON
  object with exit code `0`;
- the trace and minimal record support review without secrets, raw private data, or raw tool output;
- you can name the production questions that remain unverified and do not rewrite “ready to start
  development” as “production-ready.”

This chapter does not provide the complete live change or boundary-list answer. The review exists
to show that, without a finished implementation to copy, you can safely connect one small
requirement to the existing path and explain why the evidence is sufficient.

## References

Last checked: 2026-08-02. Locked project version: `openai-agents==0.19.1`.

- [Current Agents SDK guide: overall positioning](https://developers.openai.com/api/docs/guides/agents)
- [`v0.19.1` Agent output types](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/agents.md#output-types)
- [`v0.19.1` Runner lifecycle and configuration](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/running_agents.md#runner-lifecycle-and-configuration)
- [`v0.19.1` function tools](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/tools.md#function-tools)
- [`v0.19.1` RunResult and final output](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/results.md#final-output)
- [`v0.19.1` tracing](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/tracing.md)
- [`v0.19.1` Runner.run source](https://github.com/openai/openai-agents-python/blob/v0.19.1/src/agents/run.py)
- [`v0.19.1` final_output_as source](https://github.com/openai/openai-agents-python/blob/v0.19.1/src/agents/result.py)
- [`v0.19.1` function_tool source](https://github.com/openai/openai-agents-python/blob/v0.19.1/src/agents/tool.py)
- [`v0.19.1` lifecycle example](https://github.com/openai/openai-agents-python/blob/v0.19.1/examples/basic/agent_lifecycle_example.py)

Changes to the examples: this chapter provides no copyable lab implementation. Its flow and review
checklist place the official single-Agent, `Runner.run`, function-tool, structured-result, and
tracing concepts inside this course's existing JSON process boundary. Sessions, handoffs,
streaming, write tools, production deployment, and the lab answer are omitted. Error statuses, exit
codes, the 20-second run deadline, review time boxes, and the target-project boundary list are course
rules, not built-in Agents SDK protocols.
