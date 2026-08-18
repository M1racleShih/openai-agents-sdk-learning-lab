---
title: M04 · 脱敏追踪与确定性测试
description: 用稳定的 trace 标识、最小本地记录和可替换的 runner 边界看清运行路径，同时阻止默认测试调用真实模型。
---

<p class="lesson-kicker">M04 · 60 分钟 · 概念 + 实战</p>

# 脱敏追踪与确定性测试

<p class="lesson-deck">保留足以解释一次运行的证据，但不把原始私有内容复制到 trace、测试输出或本地记录。</p>

<div class="lesson-meta" aria-label="课程信息">
  <span>SDK v0.20.0</span>
  <span>10 道巩固题</span>
  <span>3 层测试</span>
  <span>1 次真实 smoke run</span>
</div>

## 学习结果

学完本章后，你应该能够：

- 从默认 trace 中区分整次 run、模型调用和函数工具调用；
- 用稳定的 `workflow_name`、唯一的 `trace_id` 和不含业务内容的 `group_id` 关联一次运行；
- 说明 `trace_include_sensitive_data` 的默认行为和风险；
- 在保留 span 结构的同时，关闭模型输入输出与函数工具输入输出的 trace 捕获；
- 保存只含应用 session/run 标识、trace 标识、来源指纹、工具阶段分类、完成分类、证据引用
  和错误代码的本地记录；
- 通过依赖注入替换 `Runner.run` 边界，写不调用真实模型的确定性测试；
- 区分单元测试、确定性集成测试和真实模型 smoke test 分别能证明什么；
- 让默认测试明确排除真实模型 smoke test。

!!! abstract "本章边界"

    本章只为 M03 的单次、只读运行增加观测和测试边界。它复用项目已有的本地 MLflow
    processor，不再增加另一套 processor 或完整 eval 平台；也不增加 SDK Session 实现、
    streaming 或生产级日志系统，不保存原始 prompt、工具参数、工具输出或完整答案。

## 核心内容

### 1. Trace 说明运行经过，不证明答案正确

`Runner.run(...)` 默认创建一个 trace，并记录这次运行中的多个 span。Trace 表示从开始到
结束的一次 workflow；span 表示其中一个有开始时间和结束时间的步骤。

`v0.20.0` 默认记录的主要层次包括：

```text
一次 Runner.run：trace
  → runner 调用：task span
  → 每轮模型循环：turn span
  → Agent 执行：agent span
  → 模型生成：generation span
  → 每次函数工具调用：function span
```

使用 M02 的两个函数工具后，一次 trace 可以回答：模型运行了几轮、调用了哪个工具、工具
调用在何时开始和结束，以及哪个 span 标记了错误。它不能回答“证据是否足以支持答案”。
这个判断仍由 M03 的状态规则、资料覆盖检查和测试完成。

| 观察位置 | 可以确认 | 不能单独确认 |
| --- | --- | --- |
| `generation` span | 模型调用是否发生、耗时和错误位置 | 输出是否符合领域事实 |
| `function` span | 工具名称、调用顺序、耗时和错误位置 | 工具返回的数据是否足以完成任务 |
| `WorkerResult` | 状态、证据引用和稳定错误代码 | 模型与工具实际经过的全部步骤 |
| 确定性测试 | 给定输入是否得到规定结果 | 真实供应商当前能否响应 |

因此，排查一次失败时要把两类证据连起来：先用本地记录找到 `trace_id`，再在 trace 中查看
路径，最后用结果状态和一致性规则判断调用方能否使用返回内容。

### 2. Session、run 和 trace 标识不是同一个状态空间

这里一共有四个标识，分属三方：应用自己生成两个（session 和 run），SDK tracing
生成一个（trace），M05 的 SDK Session 还有一个（对话历史存储键）。不要把它们
折叠成“session ID”：

| 标识 | 生命周期 | 回答的问题 |
| --- | --- | --- |
| application session ID | 同一用户会话的多轮 turn | 哪些应用 turn 属于同一段连续交互？ |
| application run ID | 每个 `Submit` 唯一 | 哪条命令、事件序列和 `RunOutcome` 属于同一次运行？ |
| SDK Session ID | M05 的对话历史存储键 | SDK 从哪个历史容器读取和写入消息？ |
| trace ID | 每次 SDK run 的 trace | 在 Trace viewer 中查看哪条模型与工具路径？ |

`Submit` 和 `RunOutcome` 是 M06 应用用例中的命令与结果对象，本章只借用这两个名字。

应用 session ID 可以作为 SDK Session factory 的输入，但概念上仍不同：前者是应用关联键，
后者属于一种可替换的对话历史实现。application run ID 由应用生成；`trace_id` 必须符合 SDK
格式。一个应用 session 可包含多个 run，每个 run 各有自己的 trace。

`RunConfig` 还提供三个 trace 关联字段：

| 字段 | 作用 | 本章规则 |
| --- | --- | --- |
| `workflow_name` | 把同一类 workflow 显示在同一个逻辑名称下 | 使用固定常量，不拼接用户输入 |
| `trace_id` | 唯一标识一次 trace | 每次运行前用 `gen_trace_id()` 生成，并写入最小记录 |
| `group_id` | 关联同一应用 session 的多条 trace | 使用不透明 application session ID，不使用邮箱、问题文本或文件路径 |

“稳定名称”不是“每次运行都使用相同 ID”。`workflow_name` 应稳定；`trace_id` 必须在每次
运行中唯一；`group_id` 可以在同一应用 session 的多次运行之间保持相同。

```python
from agents import RunConfig, gen_trace_id

WORKFLOW_NAME = "Read-only maintenance assistant"


def make_run_config(correlation_id: str) -> tuple[str, RunConfig]:
    trace_id = gen_trace_id()
    return trace_id, RunConfig(
        workflow_name=WORKFLOW_NAME,
        trace_id=trace_id,
        group_id=correlation_id,
        trace_include_sensitive_data=False,
    )
```

`gen_trace_id()` 生成 SDK 接受的 trace ID。不要自己把任务文本做哈希后当作 `trace_id`；哈希
仍可能泄露可枚举内容，也容易产生不符合 SDK 格式的值。`group_id` 和 `trace_metadata` 都会
随 trace 导出，所以只放允许公开的、不透明标识和固定分类。

### 3. 关闭敏感内容捕获，但保留 span

`v0.20.0` 默认把 `trace_include_sensitive_data` 设为 `True`。此时 generation span 可能包含
模型输入和输出，function span 可能包含工具参数和返回值。对读取受控资料的应用，这个
默认值风险过高。

本课程在每次运行的 `RunConfig` 中显式设置：

```python
RunConfig(trace_include_sensitive_data=False)
```

设置为 `False` 后，SDK 仍创建 generation 和 function span，但不在其中加入敏感的模型输入
输出或工具输入输出。工具名、span 的时间和运行结构仍可用于定位问题。也可以在程序启动前
用下面的环境变量改变默认值：

```bash
export OPENAI_AGENTS_TRACE_INCLUDE_SENSITIVE_DATA=0
```

本章仍要求在代码中显式设置 `False`，因为测试可以直接断言这个边界，不需要依赖运行机器
的环境。

!!! warning "一个开关只保护 trace"

    `trace_include_sensitive_data=False` 不会清理应用自己的日志、本地记录、测试失败输出，
    也不会删除内存中的 `RunResult.new_items` 或 `raw_responses`。不要打印这些对象。应用日志
    和本地记录必须另设允许字段列表。

SDK 的 `openai.agents` 和 `openai.agents.tracing` logger 在 `v0.20.0` 默认不记录模型和工具
输入输出。不要为排错把 `OPENAI_AGENTS_DONT_LOG_MODEL_DATA` 或
`OPENAI_AGENTS_DONT_LOG_TOOL_DATA` 设为 `0`。应用自己的 logger 只写固定事件名、`trace_id`、
状态和错误代码，不写异常文本、prompt、工具参数或工具结果。

### 4. 最小 `RunRecord` 关联结果、来源和工具阶段

Trace 适合查看运行路径，本地记录适合让应用快速回答“这次运行结果是什么，以及去哪里看
trace”。两者都不需要复制源文档。

```python
from typing import Literal

from pydantic import BaseModel


class ProvenanceRef(BaseModel):
    kind: Literal["source", "skill"]
    artifact_id: str
    revision: str
    checksum: str


class ToolPhase(BaseModel):
    tool_name: str
    phase: Literal["started", "finished"]
    outcome: Literal["ok", "error", "timeout", "cancelled"] | None = None


class RunRecord(BaseModel):
    application_session_id: str
    application_run_id: str
    trace_id: str
    provenance: list[ProvenanceRef]
    tool_phases: list[ToolPhase]
    completion: Literal[
        "completed", "incomplete", "failed", "cancelled", "timed_out"
    ]
    evidence_refs: list[str]
    error_codes: list[str]
```

这里的 `skill` 只是课程允许清单中的公开指令包，不是第二个 Agent，也不是 SDK runtime
扩展点；capstone 没有使用时，列表保持为空。来源和指令包只记录 ID、revision/version 与
checksum，不记录正文。`ToolPhase` 只记录已批准工具的开始、结束和结束分类，不记录参数或
原始输出。`evidence_refs` 只保存稳定定位信息；`error_codes` 只保存 M03 的稳定分类。

| 允许写入 | 不写入 |
| --- | --- |
| application session/run ID、trace ID | API key、访问令牌或客户端配置 |
| 五种完成分类 | 原始任务文本、完整 prompt 或完整答案 |
| source/skill provenance、证据引用 | 源文档正文或工具原始输出 |
| 工具开始/结束分类、稳定错误代码 | 工具参数、异常文本、堆栈或本机绝对路径 |

把每个 `RunRecord` 序列化成一行 JSON，写到本地 context 指定的记录文件。记录路径、logger
和写入函数仍属于本地依赖，不进入 prompt。测试使用 `tmp_path`，不能写入真实运行记录。

应用应在调用 `Runner.run` 前生成 application run ID 和 `trace_id`。这样，即使模型失败、
工具失败、超时或取消，M03 包装层仍能写入同一组标识和准确的最终分类。任何异常分支都
不得写成 `completed`。

### 5. 在调用点注入 runner，默认测试就不需要模型

M03 可以临时替换 `Runner.run`。M04 把这个替换点变成明确参数：生产代码默认接收
`Runner.run`，测试传入一个异步假函数。应用只需要一个边界，不需要建立通用 runner 框架。

```python
from collections.abc import Awaitable, Callable

from agents import Agent, RunResult, Runner

RunAgent = Callable[..., Awaitable[RunResult]]


async def run_observed(
    agent: Agent[object],
    model_input: str,
    local_context: object,
    application_session_id: str,
    application_run_id: str,
    *,
    run_agent: RunAgent = Runner.run,
) -> WorkerResult:
    trace_id, run_config = make_run_config(application_session_id)
    sdk_result = await run_agent(
        agent,
        model_input,
        context=local_context,
        max_turns=6,
        run_config=run_config,
    )
    result = check_domain_completion(
        sdk_result.final_output_as(WorkerResult, raise_if_incorrect_type=True)
    )
    append_run_record(application_session_id, application_run_id, trace_id, result)
    return result
```

上面只展示正常路径中的注入位置。实战要把同一位置接入 M03 的超时和异常映射，保证非正常
路径也写入记录；不要另写第二套运行流程。

确定性测试传入 `fake_run_agent`，让它返回测试构造的结果，并捕获收到的关键字参数：

```python
import pytest

from agents import RunConfig, RunResult


@pytest.mark.asyncio
async def test_run_uses_redacted_trace_config(tmp_path):
    captured: dict[str, object] = {}

    async def fake_run_agent(*_args: object, **kwargs: object) -> RunResult:
        captured.update(kwargs)
        return stub_sdk_result(completed_result())

    result = await run_observed(
        test_agent(),
        "public fixture request",
        test_context(tmp_path),
        "session_test_001",
        "run_test_001",
        run_agent=fake_run_agent,
    )

    config = captured["run_config"]
    assert isinstance(config, RunConfig)
    assert config.workflow_name == WORKFLOW_NAME
    assert config.group_id == "session_test_001"
    assert config.trace_include_sensitive_data is False
    assert result.status == "completed"
```

`stub_sdk_result`、`completed_result`、`test_agent` 和 `test_context` 是实战需要完成的测试
helper。测试不 patch SDK 全局状态，也不导入 SDK 仓库内部的 `FakeModel`。只要假 runner
没有网络代码，这个测试就不需要 API key。

### 6. 三层测试提供不同证据

| 测试层 | 运行什么 | 能证明什么 | 不能证明什么 |
| --- | --- | --- | --- |
| 单元测试 | validator、记录筛选、工具函数 | 普通 Python 规则在固定输入下正确 | runner 与各部分是否连接正确 |
| 确定性集成测试 | 应用包装层 + 假 runner + fixture 工具 | 参数、状态映射、记录和异常路径连接正确 | 真实模型或供应商当前可用 |
| 真实 smoke test | 显式配置模型 + 完整只读路径 | 最小端到端路径当前能运行 | 所有输入质量、长期稳定性或生产就绪 |

真实 smoke test 必须有 `smoke` marker，并从默认测试中排除。在 `pyproject.toml` 注册 marker
并让默认选择表达式排除它：

```toml
[tool.pytest.ini_options]
addopts = "-q -m 'not smoke'"
markers = [
    "smoke: makes a real model API call and must be selected explicitly",
]
```

Smoke test 只读取公开的合成 fixture，不能打印 prompt、模型完整输出或工具原始数据。先运行
默认测试；只有显式配置模型和凭据后，才覆盖默认选择表达式运行 smoke test：

```bash
uv run pytest
uv run pytest -o addopts= -m smoke tests/test_smoke.py -q
```

第二条命令是一次有成本的真实网络检查，不属于每次默认 `pytest`。如果缺少模型配置，smoke
test 应明确跳过或失败，不能静默改用 SDK 默认模型。

### 7. 用 trace 回答具体问题

真实 smoke run 完成后，按以下顺序检查本地 MLflow Trace viewer：

1. 用固定的 `workflow_name` 找到这类应用运行；
2. 用本地记录中的 `trace_id` 找到这一次运行；
3. 确认 `group_id` 与本次 application session 使用的不透明关联标识一致；
4. 展开 task 和 turn span，确认模型调用轮次；
5. 查看 function span 的工具名称、顺序、耗时和错误标记；
6. 确认 generation 和 function span 没有原始输入输出；
7. 把失败 span 与本地记录的 `status` 和 `error_codes` 对照。

如果预期的 function span 根本不存在，先检查模型是否请求了工具。如果 function span 存在
并标记错误，问题发生在工具调用阶段。如果工具成功但结果仍是 `incomplete`，再检查资料
覆盖和领域规则。分别检查这三种情况，才能避免把所有失败都归因于模型。

## 习题

先完成问题，再展开参考答案。

### 概念与代码阅读

1. Trace 和 span 分别表示什么？
2. 默认 trace 中，哪两类 span 最可能包含模型内容或工具内容？
3. 判断正误：`trace_include_sensitive_data=False` 会彻底关闭 tracing。
4. application session ID、application run ID、SDK Session ID 和 trace ID 分别解决什么问题？
5. 为什么不能把用户问题或文件路径直接放进 `group_id` 或 `trace_metadata`？
6. 最小本地记录为什么保存证据引用，而不保存证据原文？
7. 判断正误：关闭 trace 敏感内容后，可以安全打印 `RunResult.new_items`。
8. 注入 `run_agent` 参数怎样阻止确定性测试调用真实模型？
9. 单元测试、确定性集成测试和真实 smoke test 各自增加了什么证据？
10. Trace 中没有预期的 function span，与 function span 存在但标记错误，分别说明先检查
    什么？

<details class="exercise-answers">
<summary>参考答案</summary>

1. Trace 表示一次 workflow 从开始到结束的运行；span 表示其中一个有开始和结束时间的
   步骤。
2. Generation span 可能包含模型输入输出，function span 可能包含工具输入输出。
3. 错。这个设置保留 span，只排除敏感的模型和工具输入输出。
4. application session ID 关联多轮应用交互；application run ID 唯一标识一次命令与事件
   序列；SDK Session ID 定位对话历史容器；trace ID 定位一次 SDK 运行路径。
5. 这些字段会随 trace 导出。用户内容、路径或可识别标识会在关闭 span 内容后继续泄露
   业务信息。
6. 引用足以定位和复查资料；保存原文会扩大私有数据的副本、保留时间和访问范围。
7. 错。这个开关只影响 trace payload，不会清理内存对象、应用日志或测试失败输出。
8. 生产代码默认使用 `Runner.run`；测试传入不含网络代码的异步假函数，并预先指定返回或
   异常，所以执行路径不会到达真实 runner。
9. 单元测试证明局部规则；确定性集成测试证明包装、参数、记录和失败映射连接正确；真实
   smoke test 证明当前模型和完整只读路径至少成功运行一次。
10. 没有 function span 时先检查模型是否请求工具；span 存在但报错时先检查工具参数、
    边界和底层只读服务。工具成功后仍不完整，则检查资料覆盖和领域规则。

</details>

### 实战：增加脱敏观测和确定性验证

在 M03 的运行包装层上完成以下任务。本章可以新增观测模块和测试，但不要复制一套平行的
运行路径，也不要把上面的讲解骨架直接改名当作完整答案。

1. 定义固定的 `WORKFLOW_NAME`；应用为每个 `Submit` 生成 application run ID，每次 SDK run
   用 `gen_trace_id()` 生成 trace ID，并把不透明 application session ID 用作 `group_id`；
2. 构造 `RunConfig`，显式设置 `workflow_name`、`trace_id`、`group_id` 和
   `trace_include_sensitive_data=False`；
3. 检查 workflow 名称、group ID 和 trace metadata，不允许其中出现任务文本、文件路径、
   凭据或真实服务信息；
4. 定义并写入最小 `RunRecord`：application session/run ID、trace ID、source/skill
   provenance、工具开始/结束分类、最终 completion 分类、必要 evidence references 和
   稳定 error codes；
5. 在现有运行函数的调用点注入 `run_agent`，默认值为 `Runner.run`；不要修改 SDK 全局
   runner，也不要建立通用框架；
6. 用假 runner 覆盖正常、不完整、工具失败、模型失败、工具超时、运行超时和取消；断言收到
   的 `RunConfig`、返回的 `WorkerResult` 和写入的记录；
7. 用合成 fixture 和明显的禁止字符串检查记录文件、`caplog` 和测试失败输出，不得出现
   密钥、原始任务、证据正文、工具输入输出或异常文本；
8. 在 `pyproject.toml` 注册 `smoke` marker，并让默认 `pytest` 排除它；真实 smoke test
   必须显式选择模型，只读取公开合成 fixture；
9. 先运行确定性测试和完整仓库检查，再显式运行一次真实模型 smoke test；
10. 在本地 MLflow Trace viewer 中用 `trace_id` 找到该运行，记录工具调用顺序和失败位置，并确认模型
    与工具的原始输入输出未被捕获。

先运行本章测试，再运行完整仓库检查：

```bash
uv run pytest tests/test_observability.py -q
uv run ruff check .
uv run pyright
uv run pytest
```

显式配置模型和凭据后，单独运行真实 smoke test：

```bash
uv run pytest -o addopts= -m smoke tests/test_smoke.py -q
```

完成标准：

- 能从 trace 说明模型运行了几轮、调用了哪些函数工具，以及失败出现在哪个 span；
- trace 保留 workflow、关联标识和 span 结构，但不包含模型或函数工具原始输入输出；
- 本地记录只含允许的标识、来源/指令指纹、工具阶段、完成分类、证据引用和错误代码；
- 确定性测试不需要 API key，也不会发出真实模型请求；
- 默认 `pytest` 排除真实 smoke test；
- 显式运行的 smoke test 使用公开合成资料，并能在本地 MLflow Trace viewer 中找到；
- 仓库、测试输出和本地记录不含密钥、私有资料或真实服务信息。

本章不提供实战完整实现。核心内容只给出 trace 配置、最小记录和 runner 注入的连接方式；
你仍需把它们接入 M03 的状态检查、异常映射、context 和测试场景。

## 版本与官方参考

本章最后核对日期：2026-08-13。项目锁定版本：`openai-agents==0.20.0`、`mlflow==3.13.0`。

- [当前 Agents SDK 指南：整体定位](https://developers.openai.com/api/docs/guides/agents)
- [`v0.20.0` Tracing：默认 spans、标识与敏感数据](https://github.com/openai/openai-agents-python/blob/v0.20.0/docs/tracing.md)
- [`v0.20.0` Configuration：tracing 与日志控制](https://github.com/openai/openai-agents-python/blob/v0.20.0/docs/config.md)
- [`v0.20.0` RunConfig 源码](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/run_config.py)
- [`v0.20.0` trace span 数据结构](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/tracing/span_data.py)
- [`v0.20.0` trace ID 生成源码](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/tracing/util.py)
- [`v0.20.0` Runner trace 建立源码](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/run.py)
- [`v0.20.0` SDK tracing 测试](https://github.com/openai/openai-agents-python/blob/v0.20.0/tests/test_tracing.py)
- [`v0.20.0` SDK runner 替换测试](https://github.com/openai/openai-agents-python/blob/v0.20.0/tests/test_run.py)
- [MLflow OpenAI Agents SDK tracing](https://mlflow.org/docs/latest/genai/tracing/integrations/listing/openai-agent/)
- [pytest markers](https://docs.pytest.org/en/stable/example/markers.html)

示例改动：从官方 tracing 文档和测试保留 `RunConfig`、`workflow_name`、`trace_id`、
`group_id`、`gen_trace_id()` 与默认 span 行为；改为课程自己的单次只读应用运行，显式关闭
敏感内容捕获，增加最小本地记录和调用点依赖注入；移除自定义 processor、SDK 全局 runner
替换、并发 trace、handoff、streaming、真实私有输入和实战完整答案。
