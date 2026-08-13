---
title: Course home
description: Learn the essential capabilities for a single-Agent read-only terminal application.
hide:
  - toc
---

<div class="course-hero" markdown>

<p class="hero-kicker">PRACTICAL FIELD GUIDE · SDK v0.20.0</p>

# Start with one real run

In roughly 11–13 hours, progressively build a single-Agent, read-only, UI-independent terminal
assistant with streamed interaction and a structured result. Lessons teach the required material;
official sources appear at the end for traceability and upgrades.

[Start M00](lessons/m00-first-agent.md){ .md-button .md-button--primary }
[View the full route](https://github.com/M1racleShih/openai-agents-sdk-learning-lab/blob/main/LEARNING_PLAN-en.md){ .md-button }

</div>

## Final architecture

```text
user
  → thin terminal adapter
  → UI-independent application use case
  → one Agents SDK Agent
  → approved read-only sources and read-only CLI/service tools
  → typed events + streamed answer + structured RunOutcome
```

The SDK owns the agent loop, tool orchestration, sessions, streaming, and traces. The application
owns commands, use cases, stable events, failure classification, and minimal audit metadata. The
terminal owns input and presentation only. Session, Trace, and terminal state are not authoritative
business records.

## How to learn

<div class="learning-grid">
  <div class="learning-card">
    <span class="card-index">01</span>
    <h3>Core material</h3>
    <p>Build the accurate mental model required for the minimum application without surveying unrelated features.</p>
  </div>
  <div class="learning-card">
    <span class="card-index">02</span>
    <h3>Exercises and skeletons</h3>
    <p>Use concept questions, interface fragments, event mappings, and test skeletons instead of copying a finished answer.</p>
  </div>
  <div class="learning-card">
    <span class="card-index">03</span>
    <h3>Verifiable labs</h3>
    <p>Default tests use fake runners, streams, and event sources. Real model and terminal runs are explicit opt-ins.</p>
  </div>
</div>

## Module map

| Module | Topic | Status |
| --- | --- | --- |
| M00 | First observable Agent | `in_progress` |
| M01 | Structured results and local context | `pending` |
| M02 | Read-only tools and source boundaries | `pending` |
| M03 | Bounded runs and truthful failures | `pending` |
| M04 | Traces, minimal metadata, and deterministic tests | `pending` |
| M05 | Sessions, streaming, and cancellation | `pending` |
| M06 | UI-independent use case and typed events | `pending` |
| M07 | Thin terminal adapter | `pending` |
| M08 | Public capstone and readiness review | `pending` |

The course explicitly excludes handoffs, agents-as-tools, multiple Agents, approvals, writes,
SandboxAgent, a GUI, and a general runtime framework.

## Current module

<div class="module-panel">
  <div class="module-number" aria-hidden="true">M00</div>
  <div class="module-copy">
    <span class="status-badge">IN PROGRESS · 学习中</span>
    <h3>First observable Agent</h3>
    <p>Distinguish <code>Agent</code>, <code>Runner.run</code>, and <code>RunResult</code>, understand
    the minimum Agent loop, and find the first real model call in the Trace viewer.</p>
    <p><strong>45 minutes · 9 review questions · 1 coding exercise · 1 trace check</strong></p>
    <a class="module-link" href="lessons/m00-first-agent/">Open the lesson →</a>
  </div>
</div>

## Model configuration

The course never relies on the SDK default model. It loads an explicit model through
`load_learning_model()`.

=== "OpenAI"

    ```bash
    export LEARNING_MODEL_PROVIDER=openai
    export OPENAI_API_KEY=...
    export OPENAI_LEARNING_MODEL=...
    ```

=== "OpenAI-compatible"

    ```bash
    export LEARNING_MODEL_PROVIDER=openai-compatible
    export OPENAI_LEARNING_MODEL=provider-model-id
    export OPENAI_COMPATIBLE_BASE_URL=https://provider-endpoint
    export OPENAI_COMPATIBLE_API_KEY=...
    ```

    Third-party endpoints use `chat_completions` by default. Set
    `OPENAI_COMPATIBLE_API=responses` only when the provider explicitly supports it.

!!! warning "Model calls and tracing are separate paths"

    A third-party compatible model can make the model call, but the OpenAI Trace viewer still
    needs a separate `OPENAI_API_KEY`. You may disable tracing without it, but then you cannot pass
    an exercise that requires trace evidence.

## Open the lesson site locally

```bash
uv sync
uv run mkdocs serve
```

Run `uv run mkdocs build --strict` before publishing. See the
[lesson site guide](site-guide.md) for details.
