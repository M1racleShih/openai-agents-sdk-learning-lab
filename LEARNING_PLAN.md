# OpenAI Agents SDK 最短实战学习路线

## 目标与适用对象

本路线面向熟练使用 Python、理解常见 Agent 概念、但没有 AI 应用开发经验的
工程师。目标不是系统学完 OpenAI Agents SDK，而是在 8–10 小时的专注练习后，
能够独立实现并解释一个供上层运行时调用的、有边界的只读证据 worker。

完成后，学习者应能：

- 解释 `Agent`、`Runner`、模型调用和工具调用组成的运行循环；
- 用 Pydantic 定义输入和机器可读输出；
- 用本地函数工具读取允许的资料并查询只读服务；
- 区分模型上下文与仅供本地代码使用的运行上下文；
- 为工具和整个运行设置边界，诚实处理不完整、超时和失败；
- 查看脱敏 trace，并保留最少的可复查运行记录；
- 用确定性测试覆盖核心逻辑，再完成一次真实模型 smoke run；
- 提供稳定的 JSON-in/JSON-out 入口供另一个运行时调用。

这表示已经具备开发目标 worker 的能力，不表示已经掌握多 Agent、长期记忆、
人工审批或生产级自主 Agent。

## 最终要亲手完成的系统

```text
上层运行时
  → JSON 任务请求
  → 单次 Agents SDK 运行
  → 只读文档工具 / 只读查询工具
  → 结构化 WorkerResult
  → 上层运行时生成最终答复
```

SDK 负责模型与工具之间的循环。应用代码仍负责工具实现、权限边界、超时、结果
契约、记录和对外入口。

## 学习范围

| 必须掌握 | 本轮暂不学习 |
| --- | --- |
| `Agent` 与 `Runner` | handoff 与 agents-as-tools |
| `output_type` 与 Pydantic | sessions 与长期记忆 |
| `RunContextWrapper` | streaming、Realtime 与 voice |
| 本地 `function_tool` | sandbox agents |
| 工具超时与错误传播 | 人工审批与可恢复暂停 |
| `max_turns` 与运行级超时 | 通用多 Agent 框架 |
| `RunResult` 与状态分类 | 完整 eval 平台 |
| tracing 与敏感数据控制 | 自定义 `ModelProvider`、自动路由与故障转移 |
| 确定性测试与一次真实 smoke run | 生产实验执行 |

被推迟的内容不是不重要，而是当前只读 worker 不依赖它们。需要时再按真实需求
增量学习。

## 学习方式

整条路线只维护一个逐步演进的项目，不为每个概念复制一个 demo。

每个模块都采用同一节奏：

1. 10–20 分钟只读当轮需要的官方资料；
2. 运行一个最小示例并观察实际对象或 trace；
3. 学习者亲手完成关键 SDK 接线；
4. 运行自动检查和一个故障场景；
5. 不看笔记解释本轮的边界和失败语义；
6. 通过验收门后做一个里程碑提交。

辅导时，导师提供目标、骨架、测试和逐级提示；学习者完成核心 SDK 代码。卡住
超过 10 分钟就缩小问题或给提示，避免把时间耗在无关细节上。导师不会预先写完
整套答案，否则只能验证代码能运行，不能验证学习者已经会开发。

## 模块与验收门

### M00：跑通一次可观察的 Agent 运行（45 分钟）

学习：

- Agents SDK 与直接使用 Responses API 的职责差异；
- `Agent`、`Runner.run`、一次 turn 和停止条件；
- 默认 trace 中能看到什么。

动手：

- 用显式模型运行一个单 Agent；
- 打印 `final_output`；
- 在 Trace viewer 中找到该次运行。

验收：

- 能画出“模型 → 工具 → 模型 → 最终输出”的循环；
- 能说明为什么上层应用仍然拥有工具、权限和持久状态；
- 代码可重复运行，密钥不进入仓库。

提交：`feat(m00): 跑通首个可追踪的 Agent`

### M01：建立类型化任务与结果契约（60 分钟）

学习：

- `output_type` 如何让最终结果成为 Pydantic 对象；
- 模型输入与本地 `RunContextWrapper` 的区别；
- 为什么下游程序不应解析自由文本。

动手：

- 定义 `TaskRequest`、`Evidence`、`WorkerError` 和 `WorkerResult`；
- 让单 Agent 返回类型化结果；
- 把 logger、允许的资料根目录等依赖放入本地 context。

验收：

- 正常运行返回可直接序列化的 `WorkerResult`；
- 能指出哪些信息模型可见、哪些只在本地代码中；
- 不把凭据、客户端或 logger 拼进 prompt。

提交：`feat(m01): 建立结构化结果与上下文边界`

### M02：只给 Agent 必需的只读能力（90 分钟）

学习：

- Python 类型标注和 docstring 如何形成函数工具 schema；
- 工具 allowlist、参数约束、超时和错误策略；
- 工具返回值如何重新进入模型上下文。

动手：

- 实现一个只能读取 fixture 目录的文本工具；
- 实现一个只读的模拟服务查询工具；
- 为异步工具设置单次超时；
- 直接测试工具的成功、越界路径和底层失败。

验收：

- 工具集合中不存在写操作；
- 路径不能逃出允许根目录；
- 超时或异常不会被伪装成正常数据；
- 不调用模型也能测试工具逻辑。

提交：`feat(m02): 增加有边界的只读函数工具`

### M03：让不完整和失败保持真实（90 分钟）

学习：

- `RunResult`、`final_output` 和运行产生的 items；
- `max_turns`、工具超时、运行级超时和 SDK 异常；
- “SDK 调用成功”与“领域任务完成”的区别。

动手：

- 定义 `completed`、`incomplete`、`failed` 三种状态；
- 在应用包装层统一处理超时、turn 上限、工具失败和无效最终输出；
- 保证异常路径仍能向调用者返回机器可读错误；
- 覆盖资料缺失、工具失败、超时和结果不完整。

验收：

- 四种非正常场景都有稳定、可断言的结果；
- `completed` 不能同时包含阻止任务完成的错误；
- 上层调用者不需要解析日志才能判断任务是否完成。

提交：`feat(m03): 建立有界运行与真实失败语义`

### M04：用 trace 和测试看清实际发生了什么（75 分钟）

学习：

- 默认 trace 的 run、model 和 function-tool spans；
- `trace_include_sensitive_data` 的默认行为和风险；
- 单元测试、集成测试和真实 smoke run 的不同证据。

动手：

- 给 workflow 指定稳定名称和关联标识；
- 关闭敏感输入与工具内容的 trace 捕获；
- 保存一份仅含状态、证据引用、错误分类和运行标识的本地记录；
- 通过依赖注入替换 runner 边界，写无真实模型调用的确定性测试；
- 保留一项显式标记的真实模型 smoke test。

验收：

- 能从 trace 解释一次运行调用了哪些工具以及在哪里失败；
- 仓库、测试输出和本地记录都不含密钥或原始私有数据；
- 默认测试不会意外产生真实 API 调用。

提交：`test(m04): 增加脱敏观测与确定性验证`

### M05：完成 JSON-in/JSON-out 证据 worker（120 分钟）

动手完成最终 capstone：

- 从标准输入或文件接收一个任务请求；
- worker 自己读取允许的资料并按需调用只读查询工具；
- 标准输出只写一个 `WorkerResult` JSON；
- 日志写到标准错误；
- 正常、不完整和失败有明确状态与退出行为；
- 调用者只收到整理结果，不需要收到全部源文档；
- 自动检查覆盖正常、缺少资料、工具失败、超时和不完整结果；
- 完成一次真实模型端到端运行。

验收：

- 一个全新的调用方只依赖 JSON schema 就能正确调用；
- 运行过程可复查，但不会无限保存工具原始输出；
- 没有 sessions、handoff、写工具或通用框架；
- 学习者可以不看现成实现，重新写出核心骨架。

提交：`feat(m05): 完成有边界的只读证据 worker`

### M06：目标项目就绪评审（45 分钟）

学习者完成一次 15 分钟讲解和一次小改动：

- 从上层调用到结构化返回，逐层解释数据和控制权；
- 解释每个失败场景由哪一层识别；
- 现场增加一个新的只读字段或工具，并补测试；
- 写出把通用 worker 接到目标项目时需要替换的边界清单。

只有讲解、小改动、自动检查和真实 smoke run 都通过，才判定“具备开始目标功能
开发的能力”。

提交：`docs(m06): 记录 worker 就绪证据与剩余问题`

## 建议日程

用两个相邻的专注时段完成：

- 第一段约 4 小时：M00–M02；
- 第二段约 5 小时：M03–M06。

可以压缩到一天，但仍应在第二天用 20 分钟不看代码重建 M05 骨架。若重建失败，
只复习暴露出的模块，不重学整套课程。

## Git 管理方式

使用独立仓库 `M1racleShih/openai-agents-sdk-learning-lab`：

- 初始为 private，完成公开安全检查后再改为 public；
- `main` 上保留一个不断演进的 capstone；
- 每个模块一个可运行的 Conventional Commit，不使用分支或 PR 制造额外流程；
- `LEARNING_LOG.md` 只记录完成时间、验证证据、纠正的一个误解和一个未决问题；
- 完成 M06 后打 `v0.1-learning-complete` 标签；
- 不放入公司名称、内部系统名、私有文档、真实服务地址、凭据或真实数据。

最小仓库结构：

```text
README.md
LEARNING_PLAN.md
LEARNING_LOG.md
pyproject.toml
uv.lock
src/evidence_worker/
tests/
fixtures/
```

不使用 GitHub Project、课程 issue 列表或每课一份复制代码。Git 历史和学习日志
已经足够追踪过程。

## 版本与环境策略

- 使用 Python 3.12 和 `uv`；
- 首次提交锁定当日确认的 `openai-agents` 版本；
- 模型名称显式配置并记录，不依赖 SDK 默认模型；
- API key 只通过环境变量或本机密钥设施提供；
- `.env.example` 只包含变量名，不包含任何真实值；
- 升级 SDK 时单独提交，并重新运行全部验收场景。

2026-07-30 启动时确认的 SDK 版本是 0.19.1。版本会继续变化，`uv.lock` 才是
这次学习过程的可复现依据。

## 必读资料

只读与当前模块直接相关的官方页面：

- [Agents SDK overview](https://developers.openai.com/api/docs/guides/agents)
- [Quickstart](https://developers.openai.com/api/docs/guides/agents/quickstart)
- [Agent definitions](https://developers.openai.com/api/docs/guides/agents/define-agents)
- [Running agents](https://openai.github.io/openai-agents-python/running_agents/)
- [Results](https://openai.github.io/openai-agents-python/results/)
- [Context management](https://openai.github.io/openai-agents-python/context/)
- [Tools](https://openai.github.io/openai-agents-python/tools/)
- [Tracing](https://openai.github.io/openai-agents-python/tracing/)

不要求先看 cookbook，也不要求通读 API reference。遇到具体接口问题时再进入
相应 reference 页面。

## 开始方式

学习者发送“开始 M00”。导师随后：

1. 初始化私有学习仓库和可复现环境；
2. 给出 M00 的 10 分钟心智模型；
3. 提供最小骨架与验收测试；
4. 由学习者完成关键代码；
5. 共同检查 trace、回答验收问题并准备里程碑提交。
