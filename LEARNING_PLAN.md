# OpenAI Agents SDK 最短实战学习路线

[English](LEARNING_PLAN-en.md)

## 目标与适用对象

本路线面向熟练使用 Python、理解常见 Agent 概念、但没有 AI 应用开发经验的工程师。
目标不是系统学完整个 SDK，而是在约 11–13 小时后能够开始开发下面这种最小应用：

```text
用户
  → 薄终端适配器
  → UI 无关的应用用例
  → 一个 OpenAI Agents SDK Agent
  → 已批准的只读资料与只读 CLI/服务工具
  → 类型化应用事件、结构化 RunOutcome 和流式用户回答
```

完成后，学习者应能：

- 解释一次应用 turn 与一次 SDK run 的关系；
- 用一个 `Agent` 和 `Runner` 运行唯一的 Agent loop；
- 显式选择模型，不依赖 SDK 默认值；
- 用 Pydantic 定义请求、来源 provenance、错误和结构化运行结果；
- 实现 fixture 资料、模拟服务与受限 CLI 的只读工具；
- 稳定区分完成、不完整、失败、取消和超时；
- 使用 Session 延续两轮对话，使用 streaming 产生用户回答和工具进度；
- 把 SDK 事件翻译为有限、稳定、UI 无关的应用事件；
- 用 prompt-toolkit 和 Rich 实现交互终端与 plain mode；
- 用假 runner、fake stream 和 fake event source 写默认不联网的测试；
- 完成一次显式真实模型和真实终端 smoke run。

这表示已经具备开始开发最小目标应用的能力，不表示已经达到生产就绪。

## 责任分工

| 层 | 拥有什么 | 不拥有什么 |
| --- | --- | --- |
| Agents SDK | Agent loop、工具编排、Session、streaming、Trace | 业务完成标准、资料批准、终端 UI |
| 应用层 | 用例、命令、类型化事件、失败分类、最少审计元数据 | 第二套 Agent runtime、通用 runtime framework |
| 终端适配器 | 输入、快捷键、批量刷新、Markdown/表格渲染 | 工作流、SDK Session、权威运行状态 |

Session 只保存对话连续性，Trace 只保存可观测路径，终端状态只服务当前展示。权威的
运行结论是应用返回的 `RunOutcome`；必要业务记录必须由应用显式保存。

## 学习范围

| 必须掌握 | 本轮明确不加入 |
| --- | --- |
| `Agent`、`Runner.run`、`Runner.run_streamed` | handoff 与 agents-as-tools |
| `output_type`、Pydantic、应用拥有的 `RunOutcome` | 多 Agent |
| `RunContextWrapper` 与来源 provenance | 人工审批与写操作 |
| 本地只读 `function_tool` | SandboxAgent |
| `RunConfig`、tracing 与脱敏记录 | GUI、Realtime 与 voice |
| SDK Session 与一种 capstone 会话策略 | 通用 runtime abstraction |
| streaming 事件、取消和完成判定 | 自动路由、故障转移与完整 eval 平台 |
| prompt-toolkit、Rich、plain mode | 生产部署与真实私有数据接入 |

工具始终只读。最终双通道采用应用侧确定性组合，不增加专用结果提交工具：自然语言由
Agent 流出，状态、provenance、evidence 和错误由应用从受控工具结果与 settled run 组装。

## 学习方式

整条路线只维护一个逐步演进的项目。教材按“学习结果 → 核心内容 → 习题 → 实战 →
完成标准 → 版本与官方参考”组织。只在行为必须验证时写代码；教材提供最小接口片段、事件
映射示例和测试骨架，不提供 capstone 完整实现。

每章使用 `openai-agents==0.20.0` 的官方文档、源码或 examples 核对接口。第三方端点的
兼容性只能由显式 smoke test 证明，不能由“OpenAI-compatible”这一名称推断。

## 模块与完成标准

### M00：首个可观察 Agent（45 分钟）

学习：

- Agents SDK 与直接使用 Responses API 的责任区别；
- `Agent`、`Runner.run`、Agent loop 和 `RunResult`；
- 一次 run 为什么可能包含多次模型调用；
- trace 能说明什么，以及它为什么不是会话或业务记录。

实战：显式配置模型，运行一个单 Agent，读取 `final_output`，在 Trace viewer 中找到运行。

完成标准：能说明 SDK 推进循环、应用规定能力边界；最终产品只有一个 SDK Agent runtime。

### M01：结构化结果与本地 context（75 分钟）

学习：

- `TaskRequest`、`Evidence`、`WorkerError`、`WorkerResult`；
- `output_type`、严格 JSON Schema 与 `final_output_as`；
- 模型输入与 `RunContextWrapper` 中本地依赖的区别；
- 最终结构化运行结果与用户可见流式回答是两个不同接口问题。

实战：完成一次结构化单 Agent 运行，但暂不解决双通道输出。

完成标准：结果可直接序列化；logger、路径、客户端和凭据不会自动进入模型上下文。

### M02：只读工具与来源边界（105 分钟）

学习：

- `function_tool` 的名称、说明、参数 schema 与错误策略；
- `ApprovedSource` / `SourceProvenance` 的 `source_id`、`revision` 和 `sha256`；
- fixture 文件 allowlist、路径解析、校验和与最小返回值；
- 模拟只读服务查询的参数、单次 timeout 和异常边界；
- 只读 CLI adapter 的固定可执行程序、只读子命令、参数、环境、时间和输出大小边界。

实战：实现 fixture 资料工具、模拟查询工具和公开合成 CLI adapter。CLI 使用
`asyncio.create_subprocess_exec`，禁止 `shell=True`，不接收任意命令字符串，不把凭据、
完整环境或无限制原始输出交给模型。

完成标准：工具集没有外部写能力；来源可复查；越界、超时和超限不会伪装成正常数据；
直接测试不调用模型。

### M03：有界运行与真实失败（75 分钟）

学习：

- `RunResult`、`new_items`、`raw_responses` 与领域 `RunOutcome` 的区别；
- 工具 timeout、`max_turns` 和运行级 timeout；
- `completed`、`incomplete`、`failed`、`cancelled`、`timed_out`；
- 稳定 reason/code 与 SDK 异常文本的边界。

实战：为缺资料、工具失败、模型失败、turn 上限、超时和取消建立一致结果。

完成标准：任何失败、取消、超时或不完整路径都不能变成 `completed`；调用方无需解析日志。

### M04：Trace、最小元数据与确定性测试（60 分钟）

学习：

- `workflow_name`、`trace_id`、`group_id` 和 `trace_include_sensitive_data=False`；
- application session ID、application run ID、trace ID 的不同生命周期；
- `RunRecord` 的 provenance、工具开始/结束分类、completion 分类和 evidence references；
- 单元测试、假 runner 集成测试和真实 smoke test 的证据差异。

实战：在调用点注入 runner，保存最小记录，默认排除 `smoke` 测试。

完成标准：Trace 与本地记录可关联；不保存凭据、完整 prompt、完整资料、无限制工具输出
或用户敏感内容。

### M05：Sessions、streaming 与取消（120 分钟）

学习：

- 一次应用 turn 对应一次 `Runner.run_streamed`；
- `to_input_list()`、SDK Session、`previous_response_id` 的取舍；
- capstone 选择可注入 Session factory 与临时 SQLiteSession；
- `ResponseTextDeltaEvent`、`RunItemStreamEvent`、`tool_called`、`tool_output`；
- 持续消费 `stream_events()` 到结束后再读取最终状态；
- `result.cancel()` 与 `result.cancel(mode="after_turn")`。

兼容性 spike：在锁定 SDK 与显式目标模型上记录 `output_type` + raw text delta 的实际形状。
不得把结构化 JSON delta 直接显示给用户，也不得写脆弱的 partial JSON parser。

Capstone 采用一个经过测试的双通道方案：Agent 的最终消息保持自然语言并产生
`message_delta`；应用从受控工具结果、context 累积器、异常映射与 settled final text
确定性组装 `RunOutcome`。整个过程只有一个 Agent、一次 Runner run，没有结果提交工具或
Agent loop 之外的额外模型调用。

完成标准：fake stream 测试覆盖正常 settle、资料覆盖不足、失败、超时和两种取消；真实
模型 spike 与 smoke test 都是显式 opt-in。

### M06：UI 无关的应用用例与类型化事件（105 分钟）

学习：

- `Submit`、`Cancel` 两个命令；
- `MessageDelta`、`ToolStarted`、`ToolFinished`、`EvidenceFound`、
  `RunStateChanged`、`Final`、`Error`；
- 应用层把 SDK raw/high-level events 翻译成稳定事件；
- 用例异步发出事件并返回最终 `RunOutcome`；
- 当前运行任务与取消控制。

实战：实现一个直接依赖 Agents SDK 的用例，不建立通用 runtime interface。终端不得看到
SDK 事件对象；`Cancel` 必须调用当前 `RunResultStreaming`/任务的取消路径，而不是设置一个
无人消费的布尔值。

完成标准：测试事件顺序、正常结束、工具失败、模型失败、超时、取消、不完整结果和同一
session 的连续两轮对话。

### M07：薄终端适配器（90 分钟）

学习：

- `PromptSession.prompt_async()`、历史、快捷键和 Ctrl-C；
- Rich 只渲染已完成 Markdown、表格和有限状态；
- token delta 的小批次 append-only 刷新；
- stdout/cursor 单一所有者；
- 无 ANSI 的 `--plain` 模式。

实战：交互模式和 plain mode 复用 M06 同一个用例。活动运行时 Ctrl-C 转成 `Cancel`；没有
活动运行时才退出。不使用全屏 Rich Live，也不按 token 重绘完整 transcript。

完成标准：fake event source 覆盖 renderer、批处理、plain mode、Ctrl-C 和取消；默认测试
不打开真实 TTY。

### M08：公开 capstone 与就绪评审（75 分钟）

Capstone 是一个用户直接使用的、单 Agent、只读终端助手。公开合成任务是检查一组虚构
设备的维护记录；资料、设备名和模拟 CLI 输出都在仓库 fixture 中生成。

验收：

1. 交互终端提交问题并收到流式自然语言回答；
2. 同一用例产生结构化 `RunOutcome`；
3. SDK Session 支持同一 session 的连续两轮；
4. 只加载 allowlist 中的最少资料；
5. 只读 CLI/查询工具按需调用；
6. 记录 source provenance；
7. trace 与脱敏应用元数据可关联；
8. 正常、缺资料、工具失败、模型失败、超时、取消和不完整结果可区分；
9. plain mode 与交互模式使用同一用例；
10. 没有写工具、handoff、多 Agent、审批、GUI 或通用 runtime framework；
11. 默认测试不联网；
12. 完成一次显式真实模型 smoke run 和一次真实终端运行。

就绪评审：15 分钟架构讲解；不看答案完成一个小型跨层修改；运行全部自动检查；完成真实
模型与终端 smoke run；解释 Session、Trace、应用 `RunOutcome` 和终端状态为什么不同。

教材不给出 capstone 完整实现。学习者必须亲自组合前八章接口并留下验证证据。

## 建议日程

- 第一段约 3 小时 45 分：M00–M02；
- 第二段约 3 小时 15 分：M03–M04 与 M05 前半；
- 第三段约 3 小时 45 分：M05 后半–M07；
- 第四段约 1 小时 15 分：M08。

总计约 12.5 小时。真实模型与终端 smoke run 的等待时间不计入阅读时间。

## 版本与环境策略

- Python 3.12 与 `uv`；
- `openai-agents==0.20.0`、`prompt-toolkit==3.0.53`、`rich==15.0.0`；
- `uv.lock` 是复现依据；
- 模型 ID 必须显式配置；
- API key 只来自环境变量或本机密钥设施；
- 默认 `pytest` 排除真实模型 smoke test；
- SDK 升级后重新核对 Agent、Runner、structured output、function_tool、RunConfig、tracing、
  sessions、streaming、cancel 和事件接口。

0.20.0 的官方发布说明指出隐式默认模型发生变化，并包含 MCP 依赖迁移。课程不依赖默认
模型，也不在当前范围使用 MCP，因此这两项不会改变课程架构。

从上一锁定版本升级后的接口审计确认：课程使用的 `Agent`/`output_type`、`Runner.run`、
`Runner.run_streamed`、`function_tool` timeout、`RunConfig` tracing 字段、`SQLiteSession`、
stream events 与两种 cancel mode 仍可用。`RunConfig` 新增的可选工具名冲突策略不改变本课程
调用；`tests/test_dependency_baseline.py` 固定检查当前依赖版本和这些公开入口。

## 资料来源

本路线最后核对：2026-08-11。锁定版本：`openai-agents==0.20.0`。

- [Agents SDK overview](https://developers.openai.com/api/docs/guides/agents)
- [Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents)
- [Results and state](https://developers.openai.com/api/docs/guides/agents/results)
- [Integrations and observability](https://developers.openai.com/api/docs/guides/agents/integrations-observability)
- [Python SDK streaming](https://openai.github.io/openai-agents-python/streaming/)
- [Python SDK sessions](https://openai.github.io/openai-agents-python/sessions/)
- [Python SDK v0.20.0 source and examples](https://github.com/openai/openai-agents-python/tree/v0.20.0)
- [Official releases](https://github.com/openai/openai-agents-python/releases/tag/v0.20.0)

每章选择完成当章目标所需的最少资料，并记录具体来源；学习者不需要预先通读全部官方
文档。

## 开始方式

从 [M00 中文教材](docs/lessons/m00-first-agent.md) 或
[M00 English lesson](docs/lessons/m00-first-agent.en.md) 开始。M00 保持 `in_progress`，其余
模块只有在学习者亲自完成实战和验证后才能从 `pending` 变更状态。
