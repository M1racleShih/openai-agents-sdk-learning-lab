# OpenAI Agents SDK: Shortest Practical Learning Path

[中文](LEARNING_PLAN.md)

## Goal and audience

This route is for engineers who are proficient in Python and understand common Agent concepts but
have not built AI applications. The goal is not to study the entire OpenAI Agents SDK. After 8–10
hours of focused work, you should be able to independently implement and explain a bounded,
read-only evidence worker that an upstream runtime can call.

After completing the route, you should be able to:

- explain the run loop formed by an `Agent`, `Runner`, model calls, and tool calls;
- define input and machine-readable output with Pydantic;
- use local function tools to read allowed sources and query read-only services;
- distinguish model-visible context from run context used only by local code;
- set boundaries for tools and complete runs, and report incomplete, timed-out, and failed work
  truthfully;
- inspect redacted traces and keep the minimum run record needed for review;
- cover core logic with deterministic tests and then perform one real model smoke run;
- expose a stable JSON-in/JSON-out entry point for another runtime.

This is enough to start building the target worker. It does not mean you have mastered multi-agent
systems, long-term memory, human approval, or production autonomous agents.

## The system you will build

```text
upstream runtime
  → JSON task request
  → one Agents SDK run
  → read-only document tool / read-only query tool
  → structured WorkerResult
  → upstream runtime produces the final response
```

The SDK runs the model/tool loop. Application code still owns tool implementations, permission
boundaries, timeouts, the result contract, records, and the external entry point.

## Learning scope

| Must learn | Not covered in this route |
| --- | --- |
| `Agent` and `Runner` | handoffs and agents-as-tools |
| `output_type` and Pydantic | sessions and long-term memory |
| `RunContextWrapper` | streaming, Realtime, and voice |
| local `function_tool` | sandbox agents |
| tool timeouts and error propagation | human approval and resumable pauses |
| `max_turns` and run-level timeouts | a general multi-agent framework |
| `RunResult` and status classification | a complete eval platform |
| tracing and sensitive-data controls | custom `ModelProvider`, automatic routing, and failover |
| deterministic tests and one real smoke run | production experiment execution |

Deferred topics are not unimportant. The current read-only worker does not need them. Learn them
later when a concrete requirement appears.

## How to learn

The entire route evolves one project. It does not copy a new demo for every concept.

Writing a lesson and studying it are separate activities.

When writing a lesson:

1. Read the official documentation, source, and examples for the project's locked version.
2. Select only the knowledge required to complete the chapter goal.
3. Prefer adapting a version-matched official example, and state its source and changes.
4. Check lesson interfaces against the installed SDK and automated checks.
5. Record the version, review date, and references at the end.

When studying:

1. The lesson contains all required material; start with its core content and example.
2. Complete concept, code-reading, or true/false exercises before expanding the reference answers.
3. Write code only when behavior needs to be verified; several consecutive chapters may share one
   lab.
4. Run the checks and confirm the result meets the module completion criteria.

Lessons use the order “Core material → Exercises → References.” A lab appears only where coding is
necessary, or after several related chapters. Official documentation provides traceability and an
upgrade check; it is not the default reading assignment.

## Modules and completion criteria

### M00: Run one observable Agent (45 minutes)

Learn:

- how the responsibilities of the Agents SDK differ from direct Responses API use;
- `Agent`, `Runner.run`, one run, and stopping conditions;
- what a default trace shows.

Build:

- run one Agent with an explicit model;
- print `final_output`;
- find the run in the Trace viewer.

Complete when:

- you can draw the “model → tool → model → final output” loop;
- you can explain why the upstream application still owns tools, permissions, and persistent state;
- the code runs repeatedly and no secret enters the repository.

Submit: `feat(m00): 跑通首个可追踪的 Agent`

### M01: Establish typed task and result contracts (60 minutes)

Learn:

- how `output_type` makes the final result a Pydantic object;
- the difference between model input and local `RunContextWrapper` data;
- why downstream programs should not parse free text.

Build:

- define `TaskRequest`, `Evidence`, `WorkerError`, and `WorkerResult`;
- return a typed result from one Agent;
- put dependencies such as the logger and allowed source root in local context.

Complete when:

- a successful run returns a directly serializable `WorkerResult`;
- you can identify what the model sees and what remains in local code;
- credentials, clients, and loggers are not inserted into the prompt.

Submit: `feat(m01): 建立结构化结果与上下文边界`

### M02: Give the Agent only the read-only capabilities it needs (90 minutes)

Learn:

- how Python type annotations and docstrings form a function-tool schema;
- tool allowlists, argument constraints, timeouts, and error policy;
- how tool return values re-enter model context.

Build:

- implement a text tool that can read only a fixture directory;
- implement a read-only simulated service query tool;
- add a per-call timeout to asynchronous tools;
- test tool success, path escape attempts, and underlying failures directly.

Complete when:

- the tool set contains no write operation;
- a path cannot escape the allowed root;
- a timeout or exception is not disguised as normal data;
- tool logic can be tested without calling a model.

Submit: `feat(m02): 增加有边界的只读函数工具`

### M03: Keep incomplete and failed work truthful (90 minutes)

Learn:

- `RunResult`, `final_output`, and items produced during a run;
- `max_turns`, tool timeouts, run-level timeouts, and SDK exceptions;
- the difference between “the SDK call succeeded” and “the domain task completed.”

Build:

- define `completed`, `incomplete`, and `failed` states;
- handle timeouts, turn limits, tool failures, and invalid final output in one application wrapper;
- return a machine-readable error even on exceptional paths;
- cover missing sources, tool failures, timeouts, and incomplete results.

Complete when:

- all four abnormal scenarios produce stable, assertable results;
- `completed` cannot contain an error that prevented task completion;
- the caller can determine task completion without parsing logs.

Submit: `feat(m03): 建立有界运行与真实失败语义`

### M04: Use traces and tests to see what happened (75 minutes)

Learn:

- default run, model, and function-tool spans;
- the default behavior and risk of `trace_include_sensitive_data`;
- the different evidence supplied by unit tests, integration tests, and a real smoke run.

Build:

- give the workflow a stable name and correlation identifier;
- disable capture of sensitive input and tool content in traces;
- save a local record containing only status, evidence references, error classification, and run ID;
- replace the runner boundary through dependency injection and write deterministic tests with no
  real model call;
- keep one explicitly marked real-model smoke test.

Complete when:

- you can use a trace to explain which tools ran and where the run failed;
- the repository, test output, and local records contain no secret or raw private data;
- default tests cannot accidentally make a real API call.

Submit: `test(m04): 增加脱敏观测与确定性验证`

### M05: Finish the JSON-in/JSON-out evidence worker (120 minutes)

Complete the capstone:

- accept one task request from standard input or a file;
- let the worker read allowed sources and call read-only query tools as needed;
- write exactly one `WorkerResult` JSON object to standard output;
- write logs to standard error;
- define clear status and exit behavior for completed, incomplete, and failed work;
- return curated results to the caller instead of every source document;
- cover success, missing sources, tool failure, timeout, and incomplete results with automated
  checks;
- complete one real end-to-end model run.

Complete when:

- a new caller can integrate using only the JSON schema;
- the run can be reviewed without storing tool output indefinitely;
- the implementation has no sessions, handoffs, write tools, or general framework;
- without looking at the finished implementation, you can rebuild the core skeleton.

Submit: `feat(m05): 完成有边界的只读证据 worker`

### M06: Review readiness for the target project (45 minutes)

Complete a 15-minute explanation and one small change:

- explain the data and control flow from upstream call to structured return;
- explain which layer identifies each failure scenario;
- add one new read-only field or tool and its tests;
- list the boundaries that must be replaced when the generic worker is connected to the target
  project.

You are ready to start the target feature only after the explanation, small change, automated
checks, and real smoke run all pass.

Submit: `docs(m06): 记录 worker 就绪证据与剩余问题`

## Suggested schedule

Use two adjacent focused sessions:

- first session, about 4 hours: M00–M02;
- second session, about 5 hours: M03–M06.

You may compress the route into one day, but on the next day spend 20 minutes rebuilding the M05
skeleton without looking at the code. If that fails, review only the modules exposed by the failed
rebuild.

## Git workflow

Use the separate `M1racleShih/openai-agents-sdk-learning-lab` repository:

- keep it private at first and make it public only after a public-safety check;
- keep one evolving capstone on `main`;
- use one runnable Conventional Commit per module, without branches or pull requests that add
  process but no learning value;
- record only completion time, verification evidence, one corrected misconception, and one open
  question in `LEARNING_LOG-en.md`;
- add the `v0.1-learning-complete` tag after M06;
- never include a company name, internal system name, private document, real service address,
  credential, or real data.

Minimum repository structure:

```text
README.md
README-en.md
LEARNING_PLAN.md
LEARNING_PLAN-en.md
LEARNING_LOG.md
LEARNING_LOG-en.md
pyproject.toml
uv.lock
mkdocs.yml
docs/
  index.md
  index.en.md
  lessons/
src/evidence_worker/
tests/
fixtures/
```

Do not use a GitHub Project, a course issue list, or a copied codebase for every lesson. Git history
and the learning log are enough to track progress.

## Version and environment policy

- use Python 3.12 and `uv`;
- lock the confirmed `openai-agents` version in the first commit;
- configure and record the model name explicitly instead of relying on the SDK default;
- supply API keys only through environment variables or a local secret facility;
- put variable names only, never real values, in `.env.example`;
- upgrade the SDK in a separate commit and rerun every acceptance scenario.

The SDK version confirmed at the start on 2026-07-30 is 0.19.1. Versions will continue to change;
`uv.lock` is the reproducibility source for this learning project.

## Sources

This course primarily uses materials for the locked Python SDK version:

- [Python SDK v0.19.1](https://github.com/openai/openai-agents-python/tree/v0.19.1)
- [Quickstart](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/quickstart.md)
- [Agent definitions](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/agents.md)
- [Running agents](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/running_agents.md)
- [Results](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/results.md)
- [Context management](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/context.md)
- [Tools](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/tools.md)
- [Tracing](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/tracing.md)
- [Versioned examples](https://github.com/openai/openai-agents-python/tree/v0.19.1/examples)

The [OpenAI Agents SDK developer guide](https://developers.openai.com/api/docs/guides/agents)
supplements the versioned sources with product positioning, the distinction between the Agents SDK
and the Responses API, and current official direction. If the two sources differ, course interfaces
and behavior follow the `v0.19.1` source, documentation, and observed local behavior.

You do not need to read all these sources. Each lesson selects the required material and lists its
specific sources at the end.

Lesson structure takes inspiration from the Hello-Agents
[concept chapter](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter3/%E7%AC%AC%E4%B8%89%E7%AB%A0%20%E5%A4%A7%E8%AF%AD%E8%A8%80%E6%A8%A1%E5%9E%8B%E5%9F%BA%E7%A1%80.md)
and [practice chapter](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter4/%E7%AC%AC%E5%9B%9B%E7%AB%A0%20%E6%99%BA%E8%83%BD%E4%BD%93%E7%BB%8F%E5%85%B8%E8%8C%83%E5%BC%8F%E6%9E%84%E5%BB%BA.md):
explain concepts first, then show examples and exercises, and finish with references. Their
technical content is not a source for this course.

## Start here

Open the [M00 English lesson](docs/lessons/m00-first-agent.en.md) or
[M00 Chinese lesson](docs/lessons/m00-first-agent.md):

1. Read the core material and example.
2. Answer the concept and code-reading questions before checking the reference answers.
3. Write the first Agent described by the lab.
4. Run the repository checks and one real model call.
5. Find the run in the Trace viewer, then record the verification evidence in the learning log.
