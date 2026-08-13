---
title: M08 · Public capstone and readiness review
description: Build a single-Agent, read-only streaming terminal assistant over public synthetic maintenance records and pass a cross-layer review.
---

<p class="lesson-kicker">M08 · 75-minute review + learner lab</p>

# Public capstone and readiness review

<p class="lesson-deck">Connect the previous lessons into a minimal user-facing application and prove each layer's state, data boundary, and failure semantics.</p>

<div class="lesson-meta" aria-label="Lesson information">
  <span>SDK v0.20.0</span>
  <span>12 acceptance checks</span>
  <span>1 Agent</span>
  <span>Read-only public synthetic data</span>
</div>

## Learning outcomes

After this chapter, you should be able to:

- connect the minimum M00–M07 capabilities into a directly usable terminal assistant;
- demonstrate allowlisted sources, provenance, and on-demand read-only queries with synthetic
  device-maintenance material;
- deliver both a streamed natural-language answer and a structured `RunOutcome`;
- prove that Session continuity, Trace path, application outcome, and terminal state are related
  but not interchangeable;
- provide different evidence through default offline tests and an explicit real smoke run;
- explain the architecture in 15 minutes and independently make one small cross-layer change.

!!! abstract "Chapter boundary"

    The capstone is learner work, not a bundled answer. This chapter supplies the task,
    architectural constraints, acceptance checks, and review method. It does not supply complete
    Agent instructions, use case, renderer, or end-to-end implementation. Every name and record is
    public and synthetic.

## Core material

### 1. Task: inspect fictional devices' public maintenance records

Create a small synthetic fixture set, such as public-garden irrigation devices:

- `pump-a17`: manual revision `2026.1` and two maintenance records;
- `sensor-b04`: manual revision `2025.3` and one calibration record;
- `valve-c12`: present on the allowlist but intentionally missing its latest inspection record;
- one fixed mock read-only CLI allowing only `list-records` and `show-record`;
- a `source_id`, revision/version, and SHA-256 checksum for every source.

A user can ask: “Which devices' latest maintenance records indicate follow-up, with citations?”
The Agent loads only the minimum allowlisted sources and calls read-only tools on demand. Missing
material produces truthful `incomplete`, never an invented record.

Fixtures may borrow no real organization, project, service, address, or data. The mock CLI also
uses a public generic name, fixed executable, and fixed read-only subcommands. It is not a general
shell, sandbox, or command framework.

### 2. The final architecture has one Agent runtime

```text
user
  → thin terminal adapter (interactive or plain)
  → UI-independent application use case
  → one OpenAI Agents SDK Agent
  → approved fixture documents + mock read-only CLI/query tools
  → typed application events + settled RunOutcome
```

Responsibilities cannot drift:

| Layer | Owns | Does not own |
| --- | --- | --- |
| terminal | Input, shortcuts, batching, display | Workflow, SDK events, Session truth, result classification |
| application | Submit/Cancel, event translation, IDs, timeout/failure, minimal audit fields | Agent loop or tool-orchestration algorithm |
| Agents SDK | One-Agent loop, tool orchestration, Session, streaming, Trace | Authoritative business record or UI transcript |
| tools | Allowlisted read-only access and provenance | Writes, arbitrary commands, or credential exposure |

SDK Session is conversation continuity; Trace is an execution path; RunOutcome is a caller
protocol; terminal state is the current presentation lifecycle. None can replace another.

### 3. Twelve capstone acceptance checks

1. The interactive terminal submits a question and displays a natural-language answer in small
   streamed batches.
2. The same application use case produces a structured `RunOutcome` after settle.
3. An SDK Session supports two continuous turns under one session.
4. Only the minimum allowlisted sources needed for the question are loaded.
5. The mock read-only CLI/query tools run only when needed and enforce argument, environment,
   timeout, and output-size boundaries.
6. `RunRecord` contains provenance for used sources/skills; the skill list is explicitly empty
   when none are used.
7. Trace ID and redacted application session/run metadata correlate in both directions.
8. Success, missing source, tool failure, model failure, timeout, cancellation, and incomplete
   results are distinguishable without parsing logs.
9. Plain and interactive modes use the same application use case and express the same outcome.
10. There is no write tool, handoff, multiple Agents, approval, GUI, or general runtime framework.
11. Default tests use no network, real TTY, or API key.
12. One explicit real-model smoke run and one real-terminal run are completed with redacted
    evidence.

For item 8, missing source is commonly `incomplete/SOURCE_MISSING`; tool or model exceptions are
`failed`; a time boundary is `timed_out`; and user interruption is `cancelled`. Do not collapse
them into one error string.

### 4. The test matrix proves protocol before live connectivity

| Layer | Input | Key assertion |
| --- | --- | --- |
| contract/unit | Fixed model objects | Five status invariants, provenance, event union |
| tool | Fixtures + fake subprocess/service | Allowlist, no shell, timeout, output limit, checksum |
| use case | Fake stream + fake Session | Order, two turns, abnormal paths, active Cancel |
| terminal | Fake events + writer/clock | Batching, append-only, plain without ANSI, Ctrl-C |
| opt-in smoke | Explicit model + synthetic fixtures | Streamed answer, tool path, RunOutcome, trace |
| manual terminal | Real TTY | History, shortcuts, Ctrl-C, completed display, plain redirection |

Default pytest runs the first four. The final two require network, cost, or a real TTY and must be
explicit. Record date, model configuration name, run ID, trace ID, and completion class. Never
record credentials, complete prompt, complete answer, or raw tool output.

### 5. Minimal evidence for a real smoke run

After explicitly setting `OPENAI_LEARNING_MODEL` and credentials:

```bash
uv run pytest -o addopts= -m smoke tests/test_smoke.py -q
uv run python -m evidence_worker.terminal --plain
```

The command is only the expected public course entry point. Document a different module name if
the learner chooses one. Also run the interactive terminal manually—not through redirection—to
inspect PromptSession history and Ctrl-C during an active run.

The smoke record needs only SDK/model configuration name, date, application session/run ID, trace
ID, used source IDs/revisions/checksums, tool classifications, completion, and evidence references.
Do not capture or commit a Trace viewer screen containing sensitive content.

### 6. Readiness review is more than a feature demo

The review has four parts:

1. **15-minute architecture explanation:** follow one Submit through command, Session factory,
   Agent loop, read-only tools, event translator, renderer, RunOutcome, RunRecord, and trace.
2. **Unseen cross-layer change:** the reviewer chooses a small requirement—for example, adding an
   allowed `revision` to `EvidenceFound`. The learner updates contract, translator, both renderers,
   and tests without an answer key.
3. **Every automated check:** lock, lint, types, default tests, strict site build, and diff
   whitespace.
4. **Live evidence:** one explicit real-model smoke and one real interactive-terminal run.

The explanation must cover why SDK Session ID, application run ID, trace ID,
`RunOutcome.status`, and terminal `running/cancelling` are not the same state; why Session and Trace
are not authoritative business records; and why the last visible token is not success.

### 7. Diagnose failed review evidence at its boundary

- Two turns are discontinuous: check factory reuse of one SDK Session; do not copy the answer into
  the prompt.
- Text appears but Final does not: check full stream consumption and settle exceptions.
- Cancel has no effect: inspect the current result/task registry and the requested run ID.
- Plain output contains ANSI: bypass Rich/TTY branches and inspect every writer output.
- Trace cannot be found: compare RunRecord trace ID with `RunConfig`; do not search user text.
- `completed` still lacks a source: inspect application coverage rules, not model self-report.
- A test unexpectedly goes online: inspect default markers, fake injection, and explicit model
  configuration; never use a fake API key.

Fix only the boundary supported by evidence. Do not add retry, multiple Agents, writes, or a
general framework while repairing it.

## Exercises

1. Why is this capstone a user-facing terminal application rather than a machine-to-machine boundary?
2. Which layer owns the Agent loop, and which owns completion classification?
3. How can a test prove only minimum allowlisted sources were loaded?
4. What different questions do source provenance and an evidence reference answer?
5. Why may `incomplete` emit Final while tool failure normally emits Error?
6. Why is the Session database not a RunRecord?
7. Why must plain and interactive modes reuse one use case?
8. What do default tests and a real smoke each prove?
9. Why does a cross-layer event change update contract, translator, renderer, and tests?
10. What must settle after the last visible token?

## Lab: the learner completes the capstone

1. Create public synthetic sources, a checksum manifest, and the mock read-only CLI.
2. Complete M01–M04 contracts, tool boundaries, failure classes, and RunRecord.
3. Complete the M05 Session factory, stream drain, two-channel composition, and compatibility
   spike.
4. Complete M06 commands, events, translator, active Cancel, and use case.
5. Complete M07 interactive/plain controller, renderer, and fake tests.
6. Implement offline tests for all twelve acceptance checks.
7. Run every automated check.
8. Explicitly run the real-model spike and smoke.
9. In a real terminal, complete two turns, one active Ctrl-C, and one plain redirection.
10. Prepare the architecture explanation and accept an unknown small cross-layer change.

Completion criteria: every acceptance item has reviewable evidence, all four review parts pass,
and the repository contains no real organization information, private source, credential, or
complete capstone answer template.

## Glossary

| Term | Course meaning |
| --- | --- |
| capstone | Learner-built public synthetic terminal application connecting every lesson |
| readiness review | Checks explanation, independent change, automated verification, and live run |
| authoritative record | Caller-facing application outcome/audit record, not Session, Trace, or UI state |
| smoke run | Explicit, bounded, real-model end-to-end connectivity check |

## Version and official references

Last checked: 2026-08-11. Locked: `openai-agents==0.20.0`, `prompt-toolkit==3.0.53`, and
`rich==15.0.0`.

- [Agents guide](https://developers.openai.com/api/docs/guides/agents)
- [Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents)
- [Results](https://developers.openai.com/api/docs/guides/agents/results)
- [Observability integration](https://developers.openai.com/api/docs/guides/agents/integrations-observability)
- [Streaming](https://openai.github.io/openai-agents-python/streaming/)
- [Sessions](https://openai.github.io/openai-agents-python/sessions/)
- [`openai-agents-python` releases](https://github.com/openai/openai-agents-python/releases)

This chapter intentionally supplies only acceptance and review scaffolding. The learner must build
the capstone, compatibility spike, real smoke, and terminal run; the course does not provide a
ready-to-submit complete answer.
