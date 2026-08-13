---
title: M08 · 公开 capstone 与就绪评审
description: 用公开合成维护记录完成单 Agent、只读、流式终端助手，并通过跨层就绪评审。
---

<p class="lesson-kicker">M08 · 75 分钟评审 + 学习者实战</p>

# 公开 capstone 与就绪评审

<p class="lesson-deck">把前八章连成一个用户直接使用的最小应用，并证明每层状态、数据边界和失败语义都成立。</p>

<div class="lesson-meta" aria-label="课程信息">
  <span>SDK v0.20.0</span>
  <span>12 项验收</span>
  <span>1 个 Agent</span>
  <span>只读公开合成资料</span>
</div>

## 学习结果

完成本章后，你应该能够：

- 把 M00–M07 的最小能力连接成可直接使用的终端助手；
- 用公开合成设备维护资料演示来源 allowlist、provenance 与按需只读查询；
- 同时交付流式自然语言回答和结构化 `RunOutcome`；
- 证明 Session 连续性、Trace 路径、应用结果和终端状态彼此相关但不等价；
- 用默认离线测试与显式真实 smoke run 提供不同层级的证据；
- 在 15 分钟内讲清架构，并独立完成一项小型跨层修改。

!!! abstract "本章边界"

    Capstone 是学习者实战，不是教材附带答案。本章只给任务、架构约束、验收清单和评审
    方法；不提交完整 agent instructions、用例、renderer 或端到端实现。所有名称、资料和
    数据均为公开合成内容。

## 核心内容

### 1. 任务：检查虚构设备的公开维护记录

建立一组小型合成 fixture，例如公共花园灌溉设备：

- `pump-a17`：手册 revision `2026.1`、两条维护记录；
- `sensor-b04`：手册 revision `2025.3`、一条校准记录；
- `valve-c12`：allowlist 中存在，但故意缺少最近检查记录；
- 一个固定的模拟只读 CLI，只允许 `list-records` 和 `show-record`；
- 每份资料有 `source_id`、revision/version 与 SHA-256 checksum。

用户可以问：“哪些设备的最近维护记录提示需要后续检查？请给出引用。”Agent 只能按需读取
allowlist 中的最少资料并调用只读工具。缺资料时必须诚实返回 `incomplete`，不能补造记录。

这些 fixture 不能借用真实组织、项目、服务、地址或数据。模拟 CLI 也使用公开通用名称，
固定 executable 与只读子命令；它不是通用 shell、sandbox 或命令框架。

### 2. 最终架构只有一个 Agent runtime

```text
user
  → thin terminal adapter (interactive or plain)
  → UI-independent application use case
  → one OpenAI Agents SDK Agent
  → approved fixture documents + mock read-only CLI/query tools
  → typed application events + settled RunOutcome
```

责任不能漂移：

| 层 | 拥有 | 不拥有 |
| --- | --- | --- |
| terminal | 输入、快捷键、batching、显示 | workflow、SDK event、Session 真相、结果分类 |
| application | Submit/Cancel、事件翻译、ID、超时/失败、审计最小字段 | Agent loop、工具编排算法 |
| Agents SDK | 单 Agent loop、工具编排、Session、streaming、Trace | 权威业务记录、UI transcript |
| tools | allowlist 内只读读取与 provenance | 写操作、任意命令、凭据外泄 |

SDK Session 是对话连续性存储；Trace 是运行路径；RunOutcome 是调用方协议；终端状态是当前
presentation 生命周期。任何一个都不能代替另外三个。

### 3. 十二项 capstone 验收

1. 交互终端提交问题并获得小批次刷新的流式自然语言回答；
2. 同一应用用例在 settle 后产生结构化 `RunOutcome`；
3. SDK Session 支持同一 session 的连续两轮对话；
4. 只加载 allowlist 中完成问题所需的最少资料；
5. 模拟只读 CLI/查询工具只在需要时调用，并满足参数、环境、超时和输出上限；
6. `RunRecord` 记录实际使用的 source/skill provenance；未使用 skill 时显式为空；
7. trace ID 与脱敏 application session/run 元数据可双向关联；
8. 正常、缺资料、工具失败、模型失败、超时、取消和不完整结果无需解析日志即可区分；
9. plain 与 interactive 模式使用同一个应用用例并表达相同结果；
10. 不存在写工具、handoff、多 Agent、审批、GUI 或通用 runtime framework；
11. 默认测试不联网、不打开真实 TTY，也不依赖 API key；
12. 显式完成一次真实模型 smoke run 和一次真实终端运行，并记录脱敏证据。

第 8 项中“缺资料”通常是 `incomplete/SOURCE_MISSING`，工具/模型异常是 `failed`，时间边界是
`timed_out`，用户中止是 `cancelled`。不要把多个不同场景都压成一个 `error` 字符串。

### 4. 测试矩阵先证明协议，再证明真实连接

| 层级 | 输入 | 关键断言 |
| --- | --- | --- |
| contract/unit | 固定模型对象 | 五种状态不变量、provenance、事件 union |
| tool | fixture + fake subprocess/service | allowlist、无 shell、超时、输出上限、checksum |
| use case | fake stream + fake Session | 事件顺序、两轮、所有异常、active Cancel |
| terminal | fake events + writer/clock | batching、append-only、plain 无 ANSI、Ctrl-C |
| opt-in smoke | 显式模型 + 合成 fixture | streamed answer、工具路径、RunOutcome、trace |
| manual terminal | 真实 TTY | 历史、快捷键、Ctrl-C、完成显示、plain 重定向 |

默认 pytest 运行前四层。后两层有网络、费用或真实 TTY 条件，必须显式执行并留下日期、模型
配置名、run ID、trace ID 和结果分类；不得记录凭据、完整 prompt、完整回答或工具原始输出。

### 5. 真实 smoke run 的最小记录

在已显式设置 `OPENAI_LEARNING_MODEL` 和凭据后：

```bash
uv run pytest -o addopts= -m smoke tests/test_smoke.py -q
uv run python -m evidence_worker.terminal --plain
```

命令名只是学习者预期创建的公开课程入口；若实战选择不同模块名，应在 README 记录。真实
交互终端还需手动运行一次，不以重定向代替，检查 PromptSession 历史和 active-run Ctrl-C。

Smoke 记录只需要：SDK/model 配置名、日期、application session/run ID、trace ID、使用的
source IDs/revisions/checksums、工具分类、completion 与 evidence references。不要截图或提交
包含敏感内容的 Trace viewer 页面。

### 6. 就绪评审不是功能演示清单

评审由四部分组成：

1. **15 分钟架构讲解**：沿一次 Submit 讲清命令、Session factory、Agent loop、只读工具、
   event translator、renderer、RunOutcome、RunRecord 与 trace；
2. **不看答案的跨层修改**：评审者现场选择一个小需求，例如给
   `EvidenceFound` 增加允许公开的 `revision`，学习者自行更新 contract、translator、两个
   renderer 和测试；
3. **全部自动检查**：lock、lint、类型、默认测试、严格站点构建与 diff whitespace；
4. **真实证据**：一次显式真实模型 smoke 和一次真实 interactive terminal run。

讲解必须能回答：为什么 SDK Session ID、application run ID、trace ID、`RunOutcome.status`
和终端的 `running/cancelling` 不是同一种状态；为什么 Session 与 Trace 不能作为权威业务
记录；为什么最后一个 visible token 还不是成功。

### 7. 失败评审时怎样定位

- 两轮不连续：先检查 factory 是否复用同一 SDK Session，不要把答案复制到 prompt；
- 文本已显示但没有 Final：检查是否完整消费 stream，并检查 settle 异常；
- Cancel 没有效果：检查 registry 中是否保存当前 result/task，及调用的 run ID；
- plain 输出出现 ANSI：绕过 Rich/TTY 分支，检查 writer 的全部输出；
- trace 找不到：对照 RunRecord 的 trace ID 与 `RunConfig`，不要搜索用户问题文本；
- `completed` 仍缺资料：检查应用 coverage rule，不要相信模型自报状态；
- 测试意外联网：检查默认 marker、fake 注入和显式模型配置，不要提供假 API key。

修复只针对证据显示的边界，不借机添加 retry、多 Agent、写操作或通用框架。

## 习题

1. 为什么这个 capstone 是用户直接使用的终端应用，而不是机器间调用边界？
2. 哪一层拥有 Agent loop，哪一层拥有完成分类？
3. 如何证明只读取了最少 allowlisted 资料？
4. `source provenance` 与 `evidence reference` 各自回答什么问题？
5. 为什么 `incomplete` 仍可以发 Final，而工具失败通常发 Error？
6. Session 数据库为什么不是 RunRecord？
7. plain 与 interactive 为什么必须复用同一用例？
8. 默认测试与真实 smoke 分别能证明什么？
9. 跨层修改为什么必须同时更新 contract、translator、renderer 和测试？
10. 最后一个 visible token 后还要等待什么？

## 实战：由学习者完成 capstone

1. 创建公开合成资料、checksum manifest 和模拟只读 CLI；
2. 完成 M01–M04 的 contract、工具边界、失败分类和 RunRecord；
3. 完成 M05 Session factory、stream 消费、双通道组合与兼容性 spike；
4. 完成 M06 命令、事件、translator、active Cancel 和 use case；
5. 完成 M07 interactive/plain controller、renderer 与 fake 测试；
6. 实现十二项验收对应的离线测试；
7. 运行全部自动检查；
8. 显式运行真实模型 spike/smoke；
9. 在真实终端完成两轮、一次 active Ctrl-C 和一次 plain 重定向；
10. 准备架构讲解并接受未知的小型跨层修改。

完成标准：十二项验收全部有可复查证据，四段就绪评审全部通过，且仓库不含真实组织信息、
私有资料、凭据或完整 capstone 答案模板。

## 术语表

| 术语 | 本课程含义 |
| --- | --- |
| capstone | 学习者自行连接各章的公开合成终端应用 |
| readiness review | 同时检查解释能力、独立修改、自动验证与真实运行 |
| authoritative record | 调用方依赖的应用结果/审计记录，不是 Session、Trace 或 UI 状态 |
| smoke run | 显式、有限、真实模型的端到端连接检查 |

## 版本与官方参考

最后核对：2026-08-11。锁定：`openai-agents==0.20.0`、`prompt-toolkit==3.0.53`、
`rich==15.0.0`。

- [Agents guide](https://developers.openai.com/api/docs/guides/agents)
- [Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents)
- [Results](https://developers.openai.com/api/docs/guides/agents/results)
- [Observability integration](https://developers.openai.com/api/docs/guides/agents/integrations-observability)
- [Streaming](https://openai.github.io/openai-agents-python/streaming/)
- [Sessions](https://openai.github.io/openai-agents-python/sessions/)
- [`openai-agents-python` releases](https://github.com/openai/openai-agents-python/releases)

本章有意只给验收与评审骨架。学习者必须亲自实现 capstone、兼容性 spike、真实 smoke 和
终端运行；教材不提供可直接提交的完整答案。
