---
title: M06 · UI 无关的应用用例与类型化事件
description: 用 Submit、Cancel 和有限事件集合隔离 Agents SDK 与终端，同时直接保留 SDK 能力。
---

<p class="lesson-kicker">M06 · 105 分钟 · 设计 + 实战</p>

# UI 无关的应用用例与类型化事件

<p class="lesson-deck">应用层拥有命令、事件、失败分类和运行生命周期；终端只提交命令并渲染事件。</p>

<div class="lesson-meta" aria-label="课程信息">
  <span>SDK v0.20.0</span>
  <span>2 种命令</span>
  <span>7 种事件</span>
  <span>1 个 Agent runtime</span>
</div>

## 学习结果

学完本章后，你应该能够：

- 用 `Submit` 与 `Cancel` 表示终端允许发出的全部应用命令；
- 用有限的 discriminated union（靠 `kind` 字段区分的联合类型）建模七种应用事件；
- 让异步用例发出事件并返回最终 `RunOutcome`；
- 把 SDK raw/high-level 事件翻译为稳定、UI 无关的应用事件；
- 保证终端不导入或判断任何 SDK event 类型；
- 让 `Cancel` 操作当前活动运行，而不是修改未被消费的标志；
- 确定性测试事件顺序、失败语义和同一 session 的两轮连续性。

!!! abstract "本章边界"

    应用用例可以直接依赖 OpenAI Agents SDK；本章不创建通用 runtime interface。它不引入
    多 Agent、handoff、审批、写工具、GUI 或事件总线框架。事件集合只有当前终端需要的
    七种，不能把所有 SDK 对象重新包装一遍。

## 核心内容

### 1. 命令表达用户意图，不携带 SDK 对象

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Submit:
    session_id: str
    text: str


@dataclass(frozen=True, slots=True)
class Cancel:
    session_id: str
    application_run_id: str
```

`Submit` 的 session ID 是应用关联键；用例为它创建唯一 application run ID、SDK Session 和
trace ID。`Cancel` 指向一个明确的活动 run，避免旧的 Ctrl-C 误伤下一轮。命令不接受
`Agent`、`RunConfig`、SDK Session 或 stream event；这些依赖由应用组合根（创建并连接
所有对象的那段启动代码）注入。

### 2. 七种事件构成封闭 union

最简单的实现是 frozen dataclass。每种事件都带字面量 `kind`、session ID 与 application
run ID；payload 只含 presentation adapter（M07 的展示适配层）需要且允许公开的字段：

```python
from dataclasses import dataclass
from typing import Literal, TypeAlias


@dataclass(frozen=True, slots=True)
class MessageDelta:
    kind: Literal["message_delta"]
    session_id: str
    run_id: str
    text: str


@dataclass(frozen=True, slots=True)
class ToolStarted:
    kind: Literal["tool_started"]
    session_id: str
    run_id: str
    tool_name: str


@dataclass(frozen=True, slots=True)
class ToolFinished:
    kind: Literal["tool_finished"]
    session_id: str
    run_id: str
    tool_name: str
    outcome: Literal["ok", "error", "timeout", "cancelled"]


@dataclass(frozen=True, slots=True)
class EvidenceFound:
    kind: Literal["evidence_found"]
    session_id: str
    run_id: str
    evidence_ref: str


@dataclass(frozen=True, slots=True)
class RunStateChanged:
    kind: Literal["run_state_changed"]
    session_id: str
    run_id: str
    state: Literal[
        "starting", "running", "cancelling", "completed", "incomplete",
        "failed", "cancelled", "timed_out"
    ]


@dataclass(frozen=True, slots=True)
class Final:
    kind: Literal["final"]
    session_id: str
    run_id: str
    outcome: "RunOutcome"


@dataclass(frozen=True, slots=True)
class Error:
    kind: Literal["error"]
    session_id: str
    run_id: str
    code: str
    safe_message: str


ApplicationEvent: TypeAlias = (
    MessageDelta | ToolStarted | ToolFinished | EvidenceFound
    | RunStateChanged | Final | Error
)
```

`kind` 让 pyright 和模式匹配知道 union 已被穷尽。`ToolFinished` 不携带 stdout、stderr 或
SDK item；`EvidenceFound` 只携带稳定引用，不携带证据原文；`Error` 不携带异常对象或异常
文本。必要的详细诊断只存在脱敏日志和 trace 中。

### 3. 用事件 sink 同时满足 streaming 与最终返回

Python async generator 不能方便地把一个业务返回值交给调用者，因此本课程使用最小异步
sink：用例 `await emit(event)` 产生事件，函数本身 `return RunOutcome`。

```python
from collections.abc import Awaitable, Callable

EventSink = Callable[[ApplicationEvent], Awaitable[None]]


async def execute_submit(command: Submit, emit: EventSink) -> RunOutcome:
    ...
```

这不是通用 event bus。每次终端 turn 传入一个 sink，测试传入把事件收集到 list 的
fake sink。同一个用例以后也可以被非终端的 presentation adapter 调用，但用例不依赖
Rich、prompt-toolkit、stdout 或 TTY。

### 4. 翻译规则固定在应用层

| SDK 观察 | 应用事件 | 过滤规则 |
| --- | --- | --- |
| `ResponseTextDeltaEvent` | `MessageDelta` | 只发非空自然语言 delta |
| `RunItemStreamEvent(name="tool_called")` | `ToolStarted` | 工具名必须属于 allowlist |
| `RunItemStreamEvent(name="tool_output")` | `ToolFinished` | 只发 `ok/error/timeout/cancelled` 分类 |
| 受控工具 context 新增 evidence ref | `EvidenceFound` | 只发稳定 reference，去重且保持发现顺序 |
| 用例生命周期变化 | `RunStateChanged` | 应用状态，不复用 SDK 内部状态名 |
| 正常或不完整 settle | `Final` | payload 是已校验 `RunOutcome` |
| 失败、超时或取消 | `Error` | 固定 code + 安全消息；返回值仍是对应 `RunOutcome` |

终端模块不得导入 `RawResponsesStreamEvent`、`RunItemStreamEvent` 或
`ResponseTextDeltaEvent`。SDK 升级只影响翻译器与兼容性测试，不应该迫使 renderer
（M07 的终端渲染层）跟着改变。

### 5. 事件顺序也是应用协议

正常路径的最小顺序：

```text
RunStateChanged(starting)
RunStateChanged(running)
0..n × (MessageDelta | ToolStarted | ToolFinished | EvidenceFound)
RunStateChanged(completed | incomplete)
Final(outcome)
return the same outcome
```

工具成功时 `ToolStarted` 必须先于对应 `ToolFinished`；从这次工具结果得到的新 evidence 在
`ToolFinished` 之后发出。失败、超时和取消路径先发出相应的终态 `RunStateChanged`，再发
一个 `Error`，而不是 `Final`。每条路径最后都返回同一分类的 `RunOutcome`。

`MessageDelta` 可以在工具事件前后交错，不要写死模型一定先说话还是先用工具。测试应该
固定 fake 输入并断言该输入的顺序，而不是把某个真实模型行为当协议。

### 6. Cancel 必须触达当前活动对象

应用维护一个很小的 active-run registry，以 application run ID 为键，值至少包含当前
`RunResultStreaming` 与执行它的 `asyncio.Task`。注册发生在运行开始，清理放在 `finally`：

```text
Submit → create task/result → register active run → consume → finally unregister
Cancel → look up exact run → emit cancelling → result.cancel() → await task settle
```

若 run 已结束，`Cancel` 返回稳定的 `RUN_NOT_ACTIVE`，不能悄悄取消下一条命令。对于 timeout，
先请求取消 active result，再等待 stream settle；如果需要取消 task，仍要捕获并转换
`CancelledError`。一个从未被 runner 或 task 检查的 `cancel_requested = True` 没有任何效果。

### 7. 确定性测试围绕用例行为

为 fake stream 和 fake Session factory 注入固定输入，至少覆盖：

| 场景 | 必须断言 |
| --- | --- |
| 正常结束 | delta 按序；terminal state 后 `Final`；返回 outcome 相同 |
| 工具失败 | started → finished(error) → failed → Error；无 Final |
| 模型失败 | `failed` + 稳定 `MODEL_FAILURE`，不外泄异常文本 |
| 超时 | active result 被取消；最终 `timed_out` |
| 主动取消 | `cancelling` 后 `cancelled`；取消作用于当前对象 |
| 结果不完整 | `incomplete` + Final，缺失来源 code 可直接读取 |
| 同一 session 两轮 | Session factory 收到同一 ID，第二轮历史连续 |

再增加两个边界测试：不同 run ID 的 Cancel 不影响当前运行；发生异常时 registry 仍被
清理。默认测试使用 fake，不实例化真实模型 client。

## 习题

1. 为什么 `Submit` 不应该携带 `Agent` 或 `RunConfig`？
2. discriminated union 中的 `kind` 给类型检查带来什么价值？
3. 为什么 `ToolFinished` 不返回 SDK tool output item？
4. 为什么本课程选择 async sink，而不是让 async generator 返回 `RunOutcome`？
5. 哪一层应该认识 `ResponseTextDeltaEvent`？
6. `Final` 与函数返回的 `RunOutcome` 应有什么关系？
7. 工具失败路径为什么不能先发 `Final` 再发 `Error`？
8. Cancel registry 为什么用 run ID，而不只用 session ID？
9. timeout 后为什么还要等待 stream settle？
10. 怎样证明 Cancel 不是一个无人消费的布尔变量？

## 实战：实现应用用例骨架

1. 定义 `Submit`、`Cancel`、七种事件和封闭 union；
2. 定义 `EventSink` 与 `execute_submit(...)->RunOutcome`；
3. 直接调用 Agents SDK streamed runner，不增加 runtime interface；
4. 把 M05 的 raw/high-level 事件翻译成应用事件，并过滤 payload；
5. 建立最小 active-run registry，使 Cancel 调用当前 result 的 cancel；
6. 把 M03 的五种完成分类接入 terminal state、Final/Error 与返回值；
7. 保证所有路径在 `finally` 清理 active registry；
8. 使用 fake stream 覆盖事件顺序、正常、工具失败、模型失败、超时、取消、不完整；
9. 使用 fake Session factory 覆盖同一 session 的连续两轮；
10. 用 pyright 检查 renderer 以后能穷尽所有 event `kind`。

完成标准：

- 终端侧不导入任何 SDK event 类型；
- 一个 Submit 产生一条可断言的事件序列并返回同一个最终 outcome；
- Cancel 触达活动 result/task，错误 run ID 不影响其他运行；
- 五种完成分类无需解析日志即可区分；
- 同一 session 两轮连续，默认测试不联网；
- 没有通用 runtime interface、事件总线或 capstone 完整答案。

## 术语表

| 术语 | 本课程含义 |
| --- | --- |
| command | presentation adapter 发给应用用例的有限意图 |
| application event | 应用拥有、SDK 无关、可穷尽的 UI 输出 |
| active run | 当前可被 Cancel 操作的 streamed result 与 task |
| event sink | 接收一个应用事件的异步回调，不是通用消息系统 |

## 版本与官方参考

最后核对：2026-08-11。锁定：`openai-agents==0.20.0`。

- [Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents)
- [Results](https://developers.openai.com/api/docs/guides/agents/results)
- [Streaming guide](https://openai.github.io/openai-agents-python/streaming/)
- [`v0.20.0` stream events](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/stream_events.py)
- [`v0.20.0` run result and cancellation](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/result.py)
- [Python dataclasses](https://docs.python.org/3/library/dataclasses.html)

示例改动：从官方 streaming 类型中只翻译课程需要的 delta 与 tool item；应用新增有限命令、
稳定事件、active-run 取消和 `RunOutcome` 返回。学习者仍需自行完成连接代码与测试。
