# OpenAI Agents SDK Learning Lab

[中文](README.md)

A short, hands-on learning project for experienced Python engineers. You will progressively build
a bounded, read-only evidence worker and learn only the OpenAI Agents SDK features needed for that
job.

## Learning outcomes

After completing all modules, you should be able to implement and explain:

- the run loop formed by one `Agent` and `Runner`;
- structured Pydantic input and output;
- read-only function tools and local run context;
- timeouts, turn limits, incomplete results, and failure propagation;
- redacted tracing, deterministic tests, and a real smoke run;
- a JSON-in/JSON-out worker that another runtime can call.

See [LEARNING_PLAN-en.md](LEARNING_PLAN-en.md) for the full route and
[LEARNING_LOG-en.md](LEARNING_LOG-en.md) for progress and verification evidence.

## How to learn

Each lesson first explains the concepts you must understand, then shows a trimmed or adapted
official example. You only need to read the lesson. Official sources appear at the end for
traceability and for checking changes when the SDK is upgraded.

The learning sequence is simple:

1. Read the core material and example.
2. Complete the concept, code-reading, or true/false exercises.
3. Write code only when behavior needs to be verified in practice.
4. Run the checks and record the result.

Not every chapter needs its own coding exercise. Several consecutive chapters may share one lab so
that you do not create repetitive demos just to satisfy a process. Course examples start from the
official examples for the locked SDK version and remove features unrelated to the current goal.

This project does not teach handoffs, sessions, streaming, Realtime, voice, sandbox agents, or a
general multi-agent framework in advance.

## Environment

- Python 3.12
- `uv`
- `openai-agents` 0.19.1

Initialize the environment:

```bash
uv sync
```

Run the repository checks:

```bash
uv run ruff check .
uv run pyright
uv run pytest
```

### Open the lesson site

Lessons are written in Markdown and rendered as HTML by MkDocs Material:

```bash
uv run mkdocs serve
```

Run a strict build before publishing:

```bash
uv run mkdocs build --strict
```

See the [lesson site guide](docs/site-guide.en.md) for the complete run, editing, bilingual
maintenance, and troubleshooting workflow.

### Choose a model provider

Every real model exercise requires an explicit `OPENAI_LEARNING_MODEL`. OpenAI is the default
provider:

```bash
export LEARNING_MODEL_PROVIDER=openai
export OPENAI_API_KEY=...
export OPENAI_LEARNING_MODEL=...
```

You may also use any service that provides an OpenAI-compatible endpoint:

```bash
export LEARNING_MODEL_PROVIDER=openai-compatible
export OPENAI_LEARNING_MODEL=provider-model-id
export OPENAI_COMPATIBLE_BASE_URL=https://provider-endpoint
export OPENAI_COMPATIBLE_API_KEY=...
```

Third-party providers use the more widely compatible Chat Completions API by default. Switch only
when the provider explicitly supports the Responses API:

```bash
export OPENAI_COMPATIBLE_API=responses
```

Common configuration examples:

| Service | `OPENAI_COMPATIBLE_BASE_URL` | Example model ID | API shape |
| --- | --- | --- | --- |
| [MiniMax (China)](https://platform.minimaxi.com/docs/guides/text-generation) | `https://api.minimaxi.com/v1` | `MiniMax-M2.7` | `chat_completions` |
| [DeepSeek](https://api-docs.deepseek.com/guides/multi_round_chat) | `https://api.deepseek.com` | `deepseek-v4-flash` | `chat_completions` |
| [Zhipu GLM](https://docs.bigmodel.cn/cn/guide/develop/openai/introduction) | `https://open.bigmodel.cn/api/paas/v4` | `glm-5.2` | `chat_completions` |

For example, you can reuse an existing provider-specific environment variable without copying or
renaming the secret:

```bash
export LEARNING_MODEL_PROVIDER=openai-compatible
export OPENAI_COMPATIBLE_API_KEY="$MINIMAX_API_KEY"
export OPENAI_COMPATIBLE_BASE_URL=https://api.minimaxi.com/v1
export OPENAI_LEARNING_MODEL=MiniMax-M3
export OPENAI_COMPATIBLE_API=responses
```

Replace the secret variable, base URL, model ID, and API shape to use the same loader with
DeepSeek, GLM, another cloud service, or a local compatible endpoint.

Course code obtains the model through `load_learning_model()`, so the Agent and Runner exercises do
not need provider-specific branches:

```python
from evidence_worker.model_provider import load_learning_model

agent = Agent(..., model=load_learning_model())
```

Third-party model requests and OpenAI tracing use different keys. Disable tracing when no OpenAI
API key is available:

```bash
export OPENAI_AGENTS_DISABLE_TRACING=1
```

To complete a check in the OpenAI Trace viewer, keep a separate `OPENAI_API_KEY` and do not disable
tracing. Traces may contain model input and output, so do not use sensitive data in exercises.

“OpenAI-compatible” does not mean full support for every OpenAI feature. Providers differ in their
support for tool calls, structured output, streaming events, and the Responses API. Before a module
depends on one of those capabilities, perform a real smoke test for that capability.

Never put a secret in the repository, a test fixture, the learning log, or shell history.

## Current progress

M00 is in progress: read the [English lesson](docs/lessons/m00-first-agent.en.md) or
[Chinese lesson](docs/lessons/m00-first-agent.md), complete the exercises, and run the first traceable
Agent.
