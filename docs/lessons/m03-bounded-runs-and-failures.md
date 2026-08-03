---
title: M03 · 有界运行与真实失败
description: 用状态一致性规则、轮次上限和运行超时，让不完整、超时和失败保持机器可读。
---

<p class="lesson-kicker">M03 · 90 分钟 · 概念 + 实战</p>

# 有界运行与真实失败

<p class="lesson-deck">限制一次运行能消耗的时间和轮次，并让调用方只看结果字段就知道任务是否完成。</p>

<div class="lesson-meta" aria-label="课程信息">
  <span>SDK v0.19.1</span>
  <span>10 道巩固题</span>
  <span>3 种领域状态</span>
  <span>4 组异常场景</span>
</div>

## 学习结果

学完本章后，你应该能够：

- 区分 `RunResult.final_output`、`new_items` 和 `raw_responses`；
- 说明一次 SDK 运行正常返回为什么不等于领域任务已经完成；
- 用 `completed`、`incomplete` 和 `failed` 表示调用方需要处理的三种结果；
- 用确定性规则保证状态、答案、证据和错误相互一致；
- 用 `max_turns` 限制模型调用轮次；
- 用工具超时和运行级超时限制两种不同的等待；
- 把 turn 上限、无效最终输出、工具失败和超时转换成稳定的机器可读结果；
- 覆盖资料缺失、工具失败、超时和结果不完整四组场景。

!!! abstract "本章边界"

    本章给单次、非 streaming 运行增加状态和失败包装。它不增加 retry、session、handoff、
    approval、持久化或通用异常框架。M04 再处理 trace、脱敏记录和 runner 边界替换。

## 核心内容

### 1. `RunResult` 记录运行产物，不替应用判断领域任务

`Runner.run(...)` 正常结束时返回 `RunResult`。M03 主要使用三个属性：

| 属性 | 包含什么 | 本章怎样使用 |
| --- | --- | --- |
| `final_output` | 最后一个 Agent 的最终输出 | 交给调用方的结构化候选结果 |
| `new_items` | 本次运行产生的消息、工具调用和工具输出等 `RunItem` | 调试运行实际经过的步骤 |
| `raw_responses` | 每次模型调用的原始 `ModelResponse` | 供应商级诊断，不作为领域结果 |

Agent 设置 `output_type=WorkerResult` 后，SDK 会先解析并校验模型给出的结构化输出。正常
返回时，`final_output` 已经是 `WorkerResult`。下面的调用再检查一次运行时类型；它不会
重新证明答案正确，也不会检查证据是否覆盖请求中的全部资料：

```python
output = sdk_result.final_output_as(WorkerResult, raise_if_incorrect_type=True)
```

`new_items` 适合回答“模型调用了哪个工具”和“工具返回了什么”。其中常见的类型包括
`MessageOutputItem`、`ToolCallItem` 和 `ToolCallOutputItem`。不要让上层调用方分析这些
items 或日志来猜任务状态；状态应直接写进 `WorkerResult`。

未处理的异常不会返回一个完整 `RunResult`。`MaxTurnsExceeded`、`ModelBehaviorError` 和
`ToolTimeoutError` 都继承 `AgentsException`。`v0.19.1` 会在这些异常的 `run_data` 中附上
当时的 `new_items` 和 `raw_responses` 等快照，供诊断使用。这份快照不是经过领域检查的
最终结果，不能直接当成成功输出。

### 2. SDK 调用成功和领域任务完成是两个判断

下面两次运行都可能正常返回经过 schema 校验的 `WorkerResult`：

```text
运行 A：读到全部请求资料 → 答案有足够证据 → completed
运行 B：一份请求资料不存在 → 返回已有证据并列出缺失项 → incomplete
```

两次 SDK 调用都成功了，但只有运行 A 完成了领域任务。结构化输出只证明字段和类型通过
schema 校验。应用还要比较 `TaskRequest.requested_source_ids` 与实际证据来源，并检查阻止
完成的错误。

本课程使用以下状态：

| 状态 | 调用方可以相信什么 | 必须满足的规则 |
| --- | --- | --- |
| `completed` | 答案完整，可以继续使用 | 没有任何 `WorkerError`，请求的资料都已处理 |
| `incomplete` | 返回内容可信，但只完成了一部分 | 至少有一个错误说明缺少什么；可以保留部分答案和证据 |
| `failed` | 没有可安全使用的领域答案 | 至少有一个错误；答案和证据都为空 |

这里把 `WorkerError` 专门用于阻止任务完成的问题，不把普通提示也塞进 `errors`。这样
`completed` 必须拥有空错误列表。以后若确实需要非阻塞提示，应另加 `warnings` 字段，
不要削弱现有含义。

可以先用 Pydantic 保证对象内部一致：

```python
from typing import Literal

from pydantic import BaseModel, model_validator


class SummaryError(BaseModel):
    code: str
    message: str


class BoundedSummary(BaseModel):
    status: Literal["completed", "incomplete", "failed"]
    answer: str
    evidence: list[str]
    errors: list[SummaryError]

    @model_validator(mode="after")
    def check_status(self) -> "BoundedSummary":
        if self.status == "completed" and self.errors:
            raise ValueError("completed results cannot contain errors")
        if self.status != "completed" and not self.errors:
            raise ValueError("non-completed results must explain why")
        if self.status == "failed" and (self.answer or self.evidence):
            raise ValueError("failed results cannot contain domain output")
        return self
```

这个 validator 只看到结果对象，无法知道请求了哪些资料。应用包装层仍要把结果与原始
`TaskRequest` 对照。若缺少请求的来源，即使模型写了 `completed`，应用也必须构造一个
新的 `incomplete` 结果，并加入稳定错误代码，例如 `SOURCE_MISSING`。

### 3. 三种边界限制不同的事情

一次运行至少需要三层边界：

```text
工具单次超时 → 限制一个异步工具调用
max_turns     → 限制一次运行可以发起多少次模型调用
运行级超时   → 限制 Runner.run 整体经过的墙钟时间
```

M02 已把异步查询工具设置为 2 秒，并选择
`timeout_behavior="raise_exception"`。超时时 SDK 抛出 `ToolTimeoutError`，其中包含工具名
和超时秒数。

`Runner.run(..., max_turns=6)` 最多允许 6 次模型调用。`v0.19.1` 把一个 turn 定义为一次
模型调用，包括这次模型输出引发的工具调用。`max_turns` 不能限制一次模型请求或工具调用
各自等待多久，也不能代替总运行时间限制。不要传 `max_turns=None` 给这个有边界的 worker，
因为这会关闭 turn 上限。

Python 3.12 的 `asyncio.timeout(...)` 可以包住整个 `Runner.run`：

```python
async with asyncio.timeout(20.0):
    sdk_result = await Runner.run(
        agent,
        model_input,
        context=local_context,
        max_turns=6,
    )
```

超时离开 context manager 后，应用收到内置 `TimeoutError`。取消是协作式的；运行超时
不会倒转已经完成的外部操作。这也是本课程在引入完整恢复策略前只允许只读工具的原因。

### 4. 用稳定代码转换异常，不把异常文本当协议

调用方需要稳定的 `WorkerError.code`，而不是 SDK 或供应商可能变化的异常字符串。建议的
最小映射是：

| 触发条件 | 状态 | 稳定错误代码 |
| --- | --- | --- |
| 请求资料缺失，但已有可信部分结果 | `incomplete` | `SOURCE_MISSING` |
| 超过 `max_turns`，没有完整最终结果 | `incomplete` | `MAX_TURNS` |
| 异步工具超过自己的超时 | `failed` | `TOOL_TIMEOUT` |
| 整次运行超过墙钟时间 | `failed` | `RUN_TIMEOUT` |
| 只读查询抛出应用定义的服务异常 | `failed` | `TOOL_FAILURE` |
| 模型输出不符合 `output_type` | `failed` | `INVALID_FINAL_OUTPUT` |
| 其他无法安全分类的异常 | `failed` | `UNEXPECTED_FAILURE` |

`v0.19.1` 的 `Runner.run` 接受 `error_handlers`。`"max_turns"` 和
`"invalid_final_output"` handler 可以返回一个受控的最终对象；SDK 会用同一个
`output_type` 再校验它。handler 不会重新调用模型，也不会重放已经发生的工具调用。

其余异常在应用最外层转换。M02 中 `failure_error_function=None` 会让工具 handler 的原始
异常继续抛出，所以服务适配器应该先把预期的底层异常改成应用自己的
`SourceQueryError`。这样包装层不会把 `TypeError` 等编程错误误标为普通工具故障。

最后仍要保留一个通用异常出口，保证 JSON-in/JSON-out 边界可以返回机器可读失败。这个
出口应在本地记录堆栈，但对外只返回固定代码和安全说明，不回传异常文本、路径或凭据。

### 5. 最小骨架：在一个地方收紧运行边界

下面的骨架组合 turn 上限、运行级超时、两个 SDK error handler 和异常映射。它沿用上面
的讲解模型，不是实战题中 `WorkerResult` 的完整实现。`failed_result`、
`incomplete_result`、`check_domain_completion` 和 `SourceQueryError` 由实战补齐。

```python
import asyncio
import logging

from agents import (
    Agent,
    ModelBehaviorError,
    RunErrorHandlerInput,
    RunErrorHandlerResult,
    Runner,
    ToolTimeoutError,
)

RUN_TIMEOUT_SECONDS = 20.0
MAX_TURNS = 6


def on_max_turns(
    _data: RunErrorHandlerInput[object],
) -> RunErrorHandlerResult:
    return RunErrorHandlerResult(
        final_output=incomplete_result("MAX_TURNS"),
        include_in_history=False,
    )


def on_invalid_final_output(
    _data: RunErrorHandlerInput[object],
) -> RunErrorHandlerResult:
    return RunErrorHandlerResult(
        final_output=failed_result("INVALID_FINAL_OUTPUT"),
        include_in_history=False,
    )


async def run_bounded(
    agent: Agent[object],
    model_input: str,
    local_context: object,
    logger: logging.Logger,
) -> BoundedSummary:
    try:
        async with asyncio.timeout(RUN_TIMEOUT_SECONDS):
            sdk_result = await Runner.run(
                agent,
                model_input,
                context=local_context,
                max_turns=MAX_TURNS,
                error_handlers={
                    "max_turns": on_max_turns,
                    "invalid_final_output": on_invalid_final_output,
                },
            )
        output = sdk_result.final_output_as(
            BoundedSummary,
            raise_if_incorrect_type=True,
        )
        return check_domain_completion(output)
    except ToolTimeoutError:
        return failed_result("TOOL_TIMEOUT")
    except TimeoutError:
        return failed_result("RUN_TIMEOUT")
    except SourceQueryError:
        return failed_result("TOOL_FAILURE")
    except ModelBehaviorError:
        return failed_result("MODEL_BEHAVIOR")
    except Exception:
        logger.exception("unexpected worker failure")
        return failed_result("UNEXPECTED_FAILURE")
```

`ModelBehaviorError` 不只表示无效最终输出；模型调用不存在的工具或生成畸形工具参数时也
可能触发它。因此上面的后备分支使用 `MODEL_BEHAVIOR`，而
`INVALID_FINAL_OUTPUT` 只由对应的 error handler 产生。

### 6. 先断言结果，再查看诊断信息

每个异常场景的测试首先断言 `WorkerResult`，不先匹配日志：

```text
资料缺失   → status == "incomplete"，errors 中有 SOURCE_MISSING
工具失败   → status == "failed"，errors 中有 TOOL_FAILURE
工具或运行超时 → status == "failed"，错误代码分别稳定
结果不完整 → status == "incomplete"，保留的答案和证据仍符合结果模型的一致性规则
```

另外检查 Pydantic 会拒绝这三种对象：`completed` 加错误、`failed` 加答案、非完成状态没有
错误。`max_turns` 和无效最终输出也要分别触发对应 handler。测试可以在调用点替换
`Runner.run`，但本章不建立通用 runner 抽象；M04 会用依赖注入整理这个边界。

只有断言失败时，才查看异常的 `run_data`、`new_items` 或本地日志，定位模型在哪一轮调用
了什么工具。诊断信息帮助解释失败，不决定对外状态。

## 习题

先完成问题，再展开参考答案。

### 概念与代码阅读

1. `final_output`、`new_items` 和 `raw_responses` 分别回答什么问题？
2. 为什么 `final_output_as(..., raise_if_incorrect_type=True)` 不能证明任务已经完成？
3. 判断正误：只要 `Runner.run` 没有抛异常，状态就应是 `completed`。
4. `incomplete` 与 `failed` 的主要区别是什么？
5. 为什么本章要求 `completed` 的 `errors` 为空？
6. `max_turns=6` 限制的是模型调用、工具调用次数，还是墙钟时间？
7. 工具超时和运行级超时分别保护哪一层？
8. `invalid_final_output` handler 返回对象后，SDK 还会做什么？它会重新调用模型吗？
9. 为什么不能把所有 `ModelBehaviorError` 都标成 `INVALID_FINAL_OUTPUT`？
10. 为什么异常路径测试应先断言 `WorkerResult`，而不是匹配日志文本？

<details class="exercise-answers">
<summary>参考答案</summary>

1. `final_output` 是交给调用方的最终候选结果；`new_items` 是带 SDK 元数据的消息、工具
   调用和工具输出；`raw_responses` 是每次模型调用的原始响应，用于供应商级诊断。
2. 这个 helper 只检查 Python 运行时类型。应用仍要检查请求资料是否被覆盖、状态与错误
   是否一致，以及证据是否足以支持答案。
3. 错。资料缺失时，SDK 可以正常返回一个经过 schema 校验的 `incomplete` 结果。
4. `incomplete` 含有可信的部分答案或证据；`failed` 没有可安全使用的领域输出。
5. 本章把 `WorkerError` 定义为阻止完成的问题。若还有这类错误，任务就不能声称完成。
6. 它最多允许 6 次模型调用；一个 turn 包含该次模型输出引发的工具调用。它没有单独限制
   每轮工具调用数，也不限制墙钟时间。
7. 工具超时限制一个异步工具调用；运行级超时限制整个 `Runner.run` 的墙钟时间。
8. SDK 会用 Agent 的同一个 `output_type` 校验 handler 返回值。handler 不会重试模型，也
   不会重放工具调用。
9. 这个异常还可能表示不存在的工具或畸形工具参数。只有专门的
   `invalid_final_output` handler 能稳定区分最终输出错误。
10. 调用方依赖结果字段和稳定错误代码。日志和异常消息会变化，而且可能含有不应外发的
    诊断信息。

</details>

### 实战：建立有界运行和失败语义

在 M01 数据模型和 M02 两个只读工具的基础上完成以下任务。可以修改
`src/evidence_worker/contracts.py`，并新增运行包装和测试文件；不要把上面的讲解模型直接
改名当作完整答案。

1. 给 `WorkerResult` 增加必填的 `status`，只允许 `completed`、`incomplete`、`failed`；
2. 规定 `errors` 中每一项都表示阻止完成的问题，并加入确定性校验：`completed` 没有
   error，`incomplete` 和 `failed` 至少有一个 error，`failed` 没有答案或证据；
3. 应用比较请求的资料标识与返回的 evidence；缺少资料时返回 `incomplete` 和
   `SOURCE_MISSING`，不能相信模型给出的 `completed`；
4. 调用 `Runner.run` 时设置 `max_turns=6`，并用 error handler 把 turn 上限转换为
   `incomplete`、把无效最终输出转换为 `failed`；
5. 用 `asyncio.timeout(20.0)` 包住整次运行；保持 M02 查询工具的 2 秒单次超时；
6. 把预期的只读查询异常转换成应用自己的异常类型，再在包装层返回 `TOOL_FAILURE`；
7. 分别处理 `ToolTimeoutError`、运行级 `TimeoutError`、其他 `ModelBehaviorError` 和最后的
   未知异常；对外只返回稳定代码和安全说明；
8. 不调用真实模型，覆盖四组场景：资料缺失、工具失败、超时和有效但不完整的结果；超时
   组要分别断言 `TOOL_TIMEOUT` 与 `RUN_TIMEOUT`；
9. 另外覆盖 `MAX_TURNS`、`INVALID_FINAL_OUTPUT` 和三条状态一致性规则；
10. 让每个结果都能直接 `model_dump_json()`；调用方不解析日志、异常文本或 `new_items`
    就能决定下一步。

先运行本章测试，再运行完整仓库检查：

```bash
uv run pytest tests/test_runner.py -q
uv run ruff check .
uv run pyright
uv run pytest
```

完成标准：

- 资料缺失、工具失败、超时和结果不完整四组场景都有稳定、可断言的 `WorkerResult`；
- `completed` 不可能同时包含阻止任务完成的错误；
- 工具 2 秒超时、运行 20 秒超时和 6 turn 上限分别生效；
- 无效最终输出和其他模型行为错误使用不同代码；
- 上层调用方只读 `status` 和 `errors` 就能判断任务是否完成；
- 测试不需要 API key，完整仓库检查全部通过。

本章不提供实战完整实现。核心内容给出了状态不变量和异常包装的连接方式；你仍需把它们
应用到自己的 `TaskRequest`、`WorkerResult`、资料覆盖检查、错误构造函数和测试场景中。

## 参考

本章最后核对日期：2026-08-02。项目锁定版本：`openai-agents==0.19.1`。

- [当前 Agents SDK 指南：整体定位](https://developers.openai.com/api/docs/guides/agents)
- [`v0.19.1` Running agents：agent loop、turn 上限与错误](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/running_agents.md)
- [`v0.19.1` Results：final output 与 new items](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/results.md)
- [`v0.19.1` Runner 与 turn 上限源码](https://github.com/openai/openai-agents-python/blob/v0.19.1/src/agents/run.py)
- [`v0.19.1` SDK 异常源码](https://github.com/openai/openai-agents-python/blob/v0.19.1/src/agents/exceptions.py)
- [`v0.19.1` run error handler 源码](https://github.com/openai/openai-agents-python/blob/v0.19.1/src/agents/run_error_handlers.py)
- [`v0.19.1` 结构化输出校验源码](https://github.com/openai/openai-agents-python/blob/v0.19.1/src/agents/agent_output.py)
- [`v0.19.1` 函数工具超时源码](https://github.com/openai/openai-agents-python/blob/v0.19.1/src/agents/tool.py)
- [`v0.19.1` Agent lifecycle 示例](https://github.com/openai/openai-agents-python/blob/v0.19.1/examples/basic/agent_lifecycle_example.py)
- [Python 3.12 `asyncio.timeout`](https://docs.python.org/3.12/library/asyncio-task.html#asyncio.timeout)

示例改动：从官方基础运行文档和 lifecycle 示例中保留单次异步 `Runner.run`；加入课程自己的
三状态规则、6 turn 上限、20 秒运行级超时、稳定错误代码和受控 error handlers；移除
随机工具、handoff、hooks、交互输入、session、streaming、retry 和实战完整答案。
