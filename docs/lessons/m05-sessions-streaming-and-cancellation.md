---
title: M05 · Sessions、streaming 与取消
description: 在一次 Runner run 中维持对话、流式输出自然语言，并在 stream 完全结束后形成可信结果。
---

<p class="lesson-kicker">M05 · 120 分钟 · 兼容性 spike + 实战</p>

# Sessions、streaming 与取消

<p class="lesson-deck">把“边生成边回答”和“最终机器可读结果”分成两条通道，但仍只运行一个 Agent。</p>

<div class="lesson-meta" aria-label="课程信息">
  <span>SDK v0.20.0</span>
  <span>3 种连续性策略</span>
  <span>2 种取消模式</span>
  <span>默认测试不联网</span>
</div>

## 学习结果

学完本章后，你应该能够：

- 解释一次应用 turn 与一次 `Runner.run_streamed()` 的对应关系；
- 比较 `to_input_list()`、SDK `Session` 与 `previous_response_id`；
- 通过可注入 Session factory 为同一应用 session 保持两轮连续对话；
- 区分 raw response 事件、high-level run-item 事件和最终 `RunResultStreaming`；
- 持续消费 `stream_events()` 直到结束，再形成最终 `RunOutcome`；
- 正确使用 `cancel()` 与 `cancel(mode="after_turn")`；
- 用 fake stream 确定性测试 delta、工具事件、失败和取消；
- 用显式真实模型 spike 验证目标模型上的结构化输出与文本 delta 形状。

!!! abstract "本章边界"

    本章只选一个会话策略、一个 Agent 和一次 streamed Runner run。它不增加第二个 Agent、
    第二次应用侧模型调用、handoff、写工具、partial JSON parser 或通用 runtime abstraction。
    终端事件翻译留给 M06，终端渲染留给 M07。

## 核心内容

### 1. 一个应用 turn 对应一次 streamed Runner run

应用 turn 从收到 `Submit(session_id, text)` 开始，到 `stream_events()` 结束并产生一个最终
`RunOutcome` 为止。一个 turn 可以包含多个 SDK model turn 和多个只读工具调用；这些都属于
同一个 Agent loop，而不是多个应用运行。

```text
application turn
  → Runner.run_streamed(...)
  → 0..n raw/high-level stream events
  → stream fully drained
  → one settled RunOutcome
```

最后一个可见 token 只说明目前没有更多文本，不说明工具、Session 写入、trace 或 runner
状态已经 settle。唯一可靠的结束点是 `async for` 正常结束，或它以异常结束并被应用分类。

### 2. 三种连续性策略只选择一种

| 策略 | 历史由谁管理 | 适合什么情况 | 本课程决策 |
| --- | --- | --- | --- |
| `result.to_input_list()` | 应用显式把上轮输入与新 items 拼回下一轮 | 需要完全掌控输入列表 | 只比较，不用于 capstone |
| SDK `Session` | Runner 在每轮前取历史、结束后写回 | 本地多轮终端会话 | **capstone 采用** |
| `previous_response_id` | Responses API 通过服务端 response ID 延续 | 已选择服务端连续性时 | 只比较，不用于 capstone |

同一条 capstone 路径不要混用这些策略，否则历史可能重复或所有权不清。SDK Session 只保存
模型对话连续性。它不保存权威 `RunOutcome`、取消状态、应用事件、来源允许清单或审计记录。

capstone 接收一个最小 Session factory，而不是把 `SQLiteSession` 写死在用例内部：

```python
from collections.abc import Callable

from agents import Session, SQLiteSession

SessionFactory = Callable[[str], Session]


def make_memory_session_factory() -> SessionFactory:
    sessions: dict[str, SQLiteSession] = {}

    def get_session(application_session_id: str) -> Session:
        return sessions.setdefault(
            application_session_id,
            SQLiteSession(application_session_id, db_path=":memory:"),
        )

    return get_session
```

内存模式必须复用同一个实例；每次重新创建 `:memory:` 数据库会丢失上一轮。需要跨进程检查
时，用测试的临时目录创建 SQLite 文件，但仍通过同一个 factory 注入。不要把 SDK Session
数据库当成业务账本或 UI transcript。

### 3. raw delta、run item 和最终状态回答不同问题

`Runner.run_streamed()` 立即返回 `RunResultStreaming`，运行在后台推进。消费端使用：

```python
from agents import RawResponsesStreamEvent, RunItemStreamEvent, Runner
from openai.types.responses import ResponseTextDeltaEvent

result = Runner.run_streamed(agent, user_text, session=session)

async for event in result.stream_events():
    if isinstance(event, RawResponsesStreamEvent) and isinstance(
        event.data, ResponseTextDeltaEvent
    ):
        on_text_delta(event.data.delta)
    elif isinstance(event, RunItemStreamEvent):
        on_run_item(event.name, event.item)
```

| 观察对象 | 典型内容 | 应用怎样用 |
| --- | --- | --- |
| `ResponseTextDeltaEvent` | 自然语言文本增量 | 转成用户可见 `MessageDelta` |
| `RunItemStreamEvent` | 已形成的 message/tool item | 转成稳定工具或证据事件 |
| `tool_called` | 工具调用 item 已创建 | 记录工具开始分类 |
| `tool_output` | 工具输出 item 已创建 | 记录结束分类；原始内容不外泄 |
| `RunResultStreaming` | `is_complete`、`final_output`、`new_items` 等 | stream 结束后读取最终状态 |

不要把 SDK event 对象直接交给终端。也不要把 raw tool output 当作 `ToolFinished` 的公开
payload；M06 只暴露允许字段和稳定分类。

### 4. 兼容性 spike：结构化 final output 不等于可显示文本流

必须在锁定版本和实际目标模型上验证两条路径：

1. Agent 使用 `output_type=SpikeResult` 时，记录 `ResponseTextDeltaEvent.delta` 的形状以及
   settle 后 `final_output` 的类型；
2. Agent 不设置 `output_type` 时，确认 delta 是可以直接拼接的自然语言，settle 后
   `final_output` 是完整文本。

SDK 的 structured output 约束最终输出符合 schema；它不承诺 raw text delta 是适合人读的
逐字答案。目标模型可能流出序列化 JSON 片段。不得把这些片段直接显示，也不得实现一个靠
猜括号边界工作的 partial JSON parser。

真实 spike 必须显式 opt-in：测试加 `@pytest.mark.smoke`，要求
`OPENAI_LEARNING_MODEL` 与凭据存在，并记录 SDK 版本、模型名、日期和两条事件样本。默认
`uv run pytest` 不选中它：

```bash
uv run pytest -o addopts= -m smoke tests/test_streaming_spike.py -q
```

### 5. 本课程选择的双通道方案

capstone 选择最小应用侧组合，不把 Agent final output 设为结构化类型：

```text
同一个 Agent、同一次 Runner.run_streamed
  ├─ ResponseTextDeltaEvent → 自然语言 MessageDelta
  └─ 应用掌握的工具结果、provenance、异常和 settled final text
       → 确定性组装 RunOutcome
```

`RunOutcome.answer` 使用 settle 后的完整自然语言 final output；`status`、`evidence`、
`provenance` 和 `errors` 来自应用自己拥有的只读工具结果、context 累积器与 M03 映射。这样
没有独立于这次 Agent loop 的额外模型调用，也没有第二个 Agent。模型不能仅靠一句
“已完成”把缺资料或异常改写成 `completed`。

必须测试以下失败路径：没有最终文本、请求来源未覆盖、工具失败、模型失败、超时、取消，
以及 stream 结束后结果仍不满足一致性规则。任何一条都不能回退成 `completed`。如果你的
目标模型 spike 证明另一种单输出形状能同时自然满足两条通道，应记录证据后再改设计，不能
只凭假设替换。

### 6. 取消是运行操作，不是 UI 标志位

`RunResultStreaming.cancel()` 立即请求停止；`cancel(mode="after_turn")` 允许当前 SDK turn
收尾，但不再开始下一 turn。两者都要求继续消费 `stream_events()`，直到迭代结束或抛出
已分类异常：

```python
result.cancel()                       # immediate
result.cancel(mode="after_turn")     # finish current turn boundary
```

应用需要保存当前活动的 `RunResultStreaming` 或运行任务引用。设置一个没人读取的布尔变量不
会取消任何东西。取消到达后，即使已经显示部分文本或记录部分 evidence，最终也必须是
`cancelled`；运行级超时必须是 `timed_out`。两者都不能报告成功。

### 7. fake stream 让默认测试完全确定

fake 不需要伪造 SDK 全部内部状态，只需实现用例实际消费的最小协议：异步事件迭代、取消
调用记录和 settle 后最终值。测试固定事件序列：

```text
text delta("Check")
tool_called("read_maintenance_record")
tool_output(classification="ok", evidence_ref="device-a#2026-04")
text delta(" complete.")
stream end
```

断言拼接文本、工具阶段、evidence reference、最终状态以及“stream end 之后才发布 Final”。
另用独立序列覆盖 tool error、模型异常、timeout、immediate cancel、after-turn cancel 和
缺失最终文本。默认测试不得读取 API key，也不得创建真实网络 client。

## 习题

1. 为什么一个应用 turn 可以包含多个 SDK turn？
2. `to_input_list()`、SDK Session 和 `previous_response_id` 的历史所有权分别在哪里？
3. 为什么内存 SQLite factory 要缓存实例？
4. 最后一个文本 delta 到达后还可能有哪些工作没有 settle？
5. `ResponseTextDeltaEvent` 与 `RunItemStreamEvent` 的抽象层级有什么差别？
6. 为什么 structured output delta 不能默认作为终端文本？
7. 本课程怎样在一次模型运行中同时得到自然语言与 `RunOutcome`？
8. `cancel()` 和 `cancel(mode="after_turn")` 的边界有什么不同？
9. 为什么取消后已显示部分文本也不能把结果标为完成？
10. fake stream 至少要记录什么，才能证明取消真的作用于活动运行？

## 实战：完成 streaming 兼容性与双通道骨架

1. 写一个可注入 Session factory，默认使用缓存的内存 `SQLiteSession`，测试可使用临时文件；
2. 用同一 session ID 完成两轮 fake 对话，断言第二轮取到第一轮历史；
3. 只调用一次 `Runner.run_streamed()`，持续消费全部事件；
4. 分别处理文本 delta、tool called、tool output 与最终 settled 状态；
5. 从应用拥有的数据组装 `RunOutcome`，不得解析 partial JSON；
6. 让 active result 接收 immediate 和 after-turn cancel，并断言最终分类为 `cancelled`；
7. 用 `asyncio.timeout()` 覆盖整条消费路径，并断言 `timed_out`；
8. 用 fake stream 覆盖成功、缺资料、工具失败、模型失败、超时、取消和不完整；
9. 添加默认排除的真实模型 spike，记录结构化与纯文本两条路径的实际事件形状；
10. 不提交真实模型输出、凭据或完整 trace；只提交脱敏结论和测试断言。

完成标准：

- capstone 明确只选 SDK Session，并可通过 factory 替换；
- 同一 session 的两轮对话在确定性测试中连续；
- 自然语言 delta 可见，最终 `RunOutcome` 机器可读；
- stream 总是消费至 settle，取消和超时永不变成 `completed`；
- 默认测试不联网；真实模型 spike 只能显式运行；
- 没有第二个 Agent、Agent loop 之外的额外模型调用或 partial JSON parser。

本章不提供 capstone 的完整实现。学习者仍需编写 factory、fake stream、结果组合器和所有
异常路径测试。

## 术语表

| 术语 | 本课程含义 |
| --- | --- |
| application turn | 一次 Submit 到一个 settled RunOutcome |
| SDK turn | Agent loop 中的一次模型调用及其触发的工具工作 |
| settle | stream 完全结束，Session、trace 与最终结果状态都可读取 |
| 双通道 | 同一次 run 的用户文本事件与机器可读最终结果 |

## 版本与官方参考

最后核对：2026-08-11。锁定：`openai-agents==0.20.0`。

- [Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents)
- [Results](https://developers.openai.com/api/docs/guides/agents/results)
- [Streaming guide](https://openai.github.io/openai-agents-python/streaming/)
- [Sessions guide](https://openai.github.io/openai-agents-python/sessions/)
- [`v0.20.0` run result source](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/result.py)
- [`v0.20.0` stream event source](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/stream_events.py)
- [`v0.20.0` session package](https://github.com/openai/openai-agents-python/tree/v0.20.0/src/agents/memory)

示例改动：官方示例保留 `run_streamed()`、`stream_events()`、`ResponseTextDeltaEvent`、SDK
Session 与两种 cancel 模式；课程增加公开合成 fixture、应用侧 `RunOutcome` 组合、fake
stream 和 opt-in 兼容性 spike，省略多 Agent、handoff、写操作与完整 capstone 答案。
