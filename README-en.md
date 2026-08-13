# OpenAI Agents SDK Learning Lab

[中文](README.md)

A short practical course for engineers who are proficient in Python and understand basic Agent
concepts but have not built an AI application. It teaches only the OpenAI Agents SDK capabilities
needed for a minimal, observable, testable read-only terminal assistant.

## Learning outcomes

After roughly 11–13 hours across M00–M08, you should be able to build and explain this system from
scratch:

```text
user
  → thin terminal adapter
  → UI-independent application use case
  → one OpenAI Agents SDK Agent
  → approved read-only sources and read-only CLI/service tools
  → typed application events, a structured RunOutcome, and a streamed user answer
```

- one `Agent` and `Runner` as the only Agent runtime;
- Pydantic structured results, local context, and source provenance;
- read-only tools bounded by allowlists, arguments, environment, time, and output size;
- stable `completed`, `incomplete`, `failed`, `cancelled`, and `timed_out` semantics;
- SDK sessions, streaming, cancellation, and redacted traces;
- a UI-independent `Submit` / `Cancel` use case with a finite typed event set;
- an interactive prompt-toolkit and Rich terminal plus an ANSI-free plain mode;
- deterministic default tests with no network, followed by explicit real-model and real-terminal
  smoke runs.

See [LEARNING_PLAN-en.md](LEARNING_PLAN-en.md) for the route and
[LEARNING_LOG-en.md](LEARNING_LOG-en.md) for progress and evidence.

## Ownership boundaries

- The SDK owns the agent loop, tool orchestration, sessions, streaming, and traces.
- The application layer owns use cases, commands, typed events, failure classification, and
  minimal audit metadata.
- The terminal handles input and rendering only. It does not own workflow or conversation state.
- A Session preserves conversation continuity, a Trace preserves an observable path, and the
  terminal preserves temporary presentation state. None is the authoritative business record.
- Tools are read-only, and the application explicitly configures or approves every model, tool,
  and source.

The course does not add handoffs, agents-as-tools, multiple Agents, human approvals, writes,
SandboxAgent, a GUI, Realtime/voice, or a general runtime abstraction. The capstone uses public
synthetic sources and a simulated read-only CLI—never company names, internal systems, real
service addresses, private documents, or real data.

## How to learn

Each lesson follows “Learning outcomes → Core material → Exercises → Lab → Completion criteria →
Version and official references,” with a glossary when useful. One project evolves across the
route; the course does not clone a demo per concept or provide the complete capstone answer.

Suggested sequence:

1. Read the core material and trimmed official examples.
2. Answer the concept questions before expanding the references.
3. Complete the interface and test skeletons in the lab.
4. Run the checks and record evidence in the learning log.

## Environment

- Python 3.12
- `uv`
- `openai-agents==0.20.0`
- `prompt-toolkit==3.0.53`
- `rich==15.0.0`

Dependencies are declared in `pyproject.toml` and locked by `uv.lock`:

```bash
uv sync
```

Default checks make no real model call:

```bash
uv lock --check
uv run ruff check .
uv run pyright
uv run pytest
uv run mkdocs build --strict
git diff --check
```

Open the lesson site locally:

```bash
uv run mkdocs serve
```

See the [lesson site guide](docs/site-guide.en.md) for editing and bilingual maintenance.

## Explicit model configuration

The course never relies on the SDK default model. Every real-model exercise must explicitly set
`OPENAI_LEARNING_MODEL`:

```bash
export LEARNING_MODEL_PROVIDER=openai
export OPENAI_API_KEY=...
export OPENAI_LEARNING_MODEL=...
```

For an OpenAI-compatible endpoint:

```bash
export LEARNING_MODEL_PROVIDER=openai-compatible
export OPENAI_LEARNING_MODEL=provider-model-id
export OPENAI_COMPATIBLE_BASE_URL=https://provider-endpoint
export OPENAI_COMPATIBLE_API_KEY=...
```

Third-party endpoints use the more widely compatible Chat Completions API by default. Set the
following only when the provider explicitly supports the Responses API:

```bash
export OPENAI_COMPATIBLE_API=responses
```

Course code obtains the model through `load_learning_model()`. Third-party model calls and OpenAI
tracing use separate credentials. Without `OPENAI_API_KEY`, you may set
`OPENAI_AGENTS_DISABLE_TRACING=1`, but that does not complete an exercise that requires the Trace
viewer.

Compatibility for tools, JSON Schema, sessions, and streaming varies across OpenAI-compatible
providers. M05 requires an explicit opt-in compatibility spike with the locked SDK and the actual
target model.
Never put a secret in the repository, fixtures, test output, the learning log, or shell history.

## Current progress

M00 remains `in_progress`; M01–M08 remain `pending`. Start with the
[English M00 lesson](docs/lessons/m00-first-agent.en.md) or the
[Chinese lesson](docs/lessons/m00-first-agent.md).

## License and sources

This project is released under the MIT License. See [LICENSE](LICENSE). SDK interfaces are grounded
in `openai-agents==0.20.0`, the official OpenAI developer documentation, and the official
[openai/openai-agents-python](https://github.com/openai/openai-agents-python) repository. Every
lesson records the checked version, date, and exact sources. This project is not affiliated with
OpenAI.
