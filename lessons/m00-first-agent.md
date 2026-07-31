# M00：跑通一次可观察的 Agent 运行

## 本节目标

完成本节后，你应该能：

- 用自己的话解释 Agents SDK 替应用管理了哪一段循环；
- 区分 `Agent` 的静态定义与 `Runner.run` 的一次运行；
- 运行一个使用显式模型名称的单 Agent；
- 从 `RunResult` 读取最终输出；
- 在 Trace viewer 中定位该次运行；
- 说明哪些职责仍然属于应用代码。

本节不讲工具、结构化输出、多轮状态或多 Agent。

## 先建立一个准确的心智模型

最小运行只有三个重要角色：

```text
应用代码
  → 定义 Agent（模型、instructions、可用能力）
  → Runner 开始一次运行
  → 模型产生最终输出
  → Runner 返回 RunResult
```

当以后加入工具时，Runner 管理的循环会变成：

```text
调用模型
  → 模型请求工具
  → 应用中的工具执行
  → 工具结果返回模型
  → 模型继续判断
  → 没有待执行工具并产生最终输出
```

SDK 管理这个循环，但不会替应用决定：

- 工具具体做什么；
- 工具拥有什么权限；
- 密钥如何提供；
- 超时和业务状态如何分类；
- 哪些运行信息可以持久保存；
- 谁负责面向最终用户回答。

## 两个核心对象

### `Agent`

`Agent` 是一份可复用的专业角色定义。M00 只使用：

- `name`：trace 中可辨认的名称；
- `instructions`：该角色的任务和约束；
- `model`：显式指定本次练习使用的模型。

创建 `Agent` 不会发起网络请求。

### `Runner`

`Runner.run(...)` 接收起始 Agent 和本次输入，执行一次完整运行并返回
`RunResult`。它是异步接口，因此 M00 使用 `asyncio.run(...)` 启动程序。

`result.final_output` 是这次运行最终得到的输出。后续模块会继续检查
`new_items`、`raw_responses` 和使用量；M00 暂时不展开。

## 定点阅读

只阅读以下部分：

1. [Quickstart：Create and run your first agent](https://developers.openai.com/api/docs/guides/agents/quickstart#create-and-run-your-first-agent)
2. [Running agents：The agent loop](https://developers.openai.com/api/docs/guides/agents/running-agents#the-agent-loop)
3. [Tracing：Default tracing](https://openai.github.io/openai-agents-python/tracing/#default-tracing)

阅读时找到三个答案：

1. Runner 遇到工具调用时会做什么？
2. 什么情况下 Runner 返回最终结果？
3. 默认 trace 至少记录哪三类事件？

## 动手任务

在 `src/evidence_worker/first_agent.py` 中完成第一个程序：

1. 定义一个只负责解释 Python 概念的 Agent；
2. 调用 `load_learning_model()`，由环境变量 `OPENAI_LEARNING_MODEL` 提供显式
   模型名称；
3. 如果该变量缺失，程序应立即给出清晰错误，不静默使用 SDK 默认模型；
4. 用 `Runner.run` 询问：“Python 的 context manager 解决了什么问题？”；
5. 输出 `result.final_output`；
6. 不添加工具、session、streaming 或异常包装层。

这一题故意很小。目标是观察 SDK 的真实运行形状，不是设计完整应用。

## 验证

正常检查：

```bash
uv run ruff check .
uv run pyright
uv run pytest
```

使用 OpenAI 真实运行前，在当前终端提供：

```bash
export LEARNING_MODEL_PROVIDER=openai
export OPENAI_API_KEY=...
export OPENAI_LEARNING_MODEL=...
```

使用第三方 OpenAI-compatible 端点时提供：

```bash
export LEARNING_MODEL_PROVIDER=openai-compatible
export OPENAI_LEARNING_MODEL=供应商模型ID
export OPENAI_COMPATIBLE_BASE_URL=https://供应商端点
export OPENAI_COMPATIBLE_API_KEY=...
# 默认 chat_completions；供应商明确支持时也可设为 responses
export OPENAI_COMPATIBLE_API=chat_completions
```

MiniMax、DeepSeek 和 GLM 的配置示例见
[README：选择模型供应商](../README.md#选择模型供应商)。如果没有单独用于 OpenAI
tracing 的 `OPENAI_API_KEY`，还应设置：

```bash
export OPENAI_AGENTS_DISABLE_TRACING=1
```

然后运行：

```bash
uv run python -m evidence_worker.first_agent
```

启用 OpenAI tracing 时，运行结束后在 OpenAI Trace viewer 中找到对应 trace，
并确认至少能看到模型调用和最终输出。关闭 tracing 的第三方模型练习可以验证模型
调用，但不能单独满足本节的 trace 验收门。

## 验收问题

不看讲义回答：

1. 为什么创建 `Agent` 时没有产生模型调用？
2. `Agent` 和一次 `Runner.run` 各自代表什么？
3. 如果以后模型连续请求两个工具，谁负责继续调用模型？
4. SDK 管理循环后，为什么应用仍然必须控制工具权限？
5. 为什么练习显式要求模型名，而不依赖默认值？

全部回答清楚、代码检查通过并完成真实 trace 检查后，M00 才能标记为 `passed`。
