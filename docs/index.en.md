---
title: Course home
description: Learn the essential OpenAI Agents SDK capabilities through one evolving project.
hide:
  - toc
---

<div class="course-hero" markdown>

<p class="hero-kicker">PRACTICAL FIELD GUIDE · SDK v0.19.1</p>

# Start with one real run

Use one evolving Python project to learn how to build a bounded, observable, and testable read-only
evidence worker. Lessons teach the required material directly; official sources appear at the end
for traceability.

[Start M00](lessons/m00-first-agent.md){ .md-button .md-button--primary }
[View the full route](https://github.com/M1racleShih/openai-agents-sdk-learning-lab/blob/main/LEARNING_PLAN-en.md){ .md-button }

</div>

## How to learn

<div class="learning-grid">
  <div class="learning-card">
    <span class="card-index">01</span>
    <h3>Core material</h3>
    <p>Build an accurate, sufficient mental model first. The lesson removes interfaces and concepts
    that the current task does not need.</p>
  </div>
  <div class="learning-card">
    <span class="card-index">02</span>
    <h3>Exercises</h3>
    <p>Check your understanding with concept questions, flow decisions, and code reading. Answers
    stay in an expandable section.</p>
  </div>
  <div class="learning-card">
    <span class="card-index">03</span>
    <h3>Lab</h3>
    <p>Write code only when real behavior needs to be observed. Several concept chapters may share
    one lab.</p>
  </div>
</div>

## Current module

<div class="module-panel">
  <div class="module-number" aria-hidden="true">M00</div>
  <div class="module-copy">
    <span class="status-badge">IN PROGRESS · 学习中</span>
    <h3>Run your first Agent</h3>
    <p>Distinguish <code>Agent</code>, <code>Runner.run</code>, and <code>RunResult</code>, understand
    the smallest agent loop, and find your first real model call in the Trace viewer.</p>
    <p><strong>45 minutes · 7 review questions · 1 coding exercise · 1 trace check</strong></p>
    <a class="module-link" href="lessons/m00-first-agent/">Open the lesson →</a>
  </div>
</div>

## Model configuration

Course code always loads the model through `load_learning_model()`. Agent and Runner exercises do
not need provider-specific branches.

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

    Third-party endpoints use `chat_completions` by default. Set the following only when the
    provider explicitly supports the Responses API:

    ```bash
    export OPENAI_COMPATIBLE_API=responses
    ```

!!! warning "Model calls and tracing are separate paths"

    A third-party compatible model can complete the model-call exercise, but the OpenAI Trace
    viewer still needs a separate `OPENAI_API_KEY`. Without that key, set
    `OPENAI_AGENTS_DISABLE_TRACING=1`; the exercise can run, but the M00 trace check is not complete.

## Open the lesson site locally

Lessons remain Markdown source. MkDocs Material generates the HTML site locally:

```bash
uv sync
uv run mkdocs serve
```

The terminal prints the local address. The browser refreshes after a lesson changes. Before
publishing, run a strict build:

```bash
uv run mkdocs build --strict
```

See the [lesson site guide](site-guide.md) for the complete editing, bilingual maintenance, and
troubleshooting workflow.

!!! info "Current scope"

    The site currently includes the home page, M00, M01, M02, M03, and M04. The learning route,
    progress log, and later modules remain in the repository. Later lessons will be added in the
    planned order.
