# OpenAI Agents SDK Learning Lab

[English](README-en.md)

一套面向熟练 Python 工程师的短周期实战课程。学习者了解 Agent 基础概念，但不需要有
AI 应用开发经验。课程只教授完成一个最小、可观察、可测试的只读终端助手所需的
OpenAI Agents SDK 能力。

## 学习结果

完成约 11–13 小时的 M00–M08 后，学习者应能从头实现并解释：

```text
用户
  → 薄终端适配器
  → UI 无关的应用用例
  → 一个 OpenAI Agents SDK Agent
  → 已批准的只读资料与只读 CLI/服务工具
  → 类型化应用事件、结构化 RunOutcome 和流式用户回答
```

- 一个 `Agent` 和 `Runner` 组成的唯一 Agent runtime；
- Pydantic 结构化结果、本地 context 与来源 provenance；
- 有 allowlist、参数、环境、时间与输出大小边界的只读工具；
- `completed`、`incomplete`、`failed`、`cancelled` 和 `timed_out` 的稳定语义；
- SDK Session、streaming、取消与脱敏 trace；
- UI 无关的 `Submit` / `Cancel` 用例和有限的类型化事件；
- 基于 prompt-toolkit 与 Rich 的交互终端和无 ANSI 的 plain mode；
- 默认不联网的确定性测试，以及显式真实模型和真实终端 smoke run。

完整路线见 [LEARNING_PLAN.md](LEARNING_PLAN.md)，进度和学习证据见
[LEARNING_LOG.md](LEARNING_LOG.md)。

## 职责边界

- SDK 拥有 Agent loop、工具编排、Session、streaming 和 Trace。
- 应用层拥有用例、命令、类型化事件、失败分类和最少审计元数据。
- 终端只负责输入与渲染，不拥有工作流或会话状态。
- Session 保存对话连续性；Trace 保存可观测路径；终端保存短暂展示状态。三者都不是
  权威业务记录。
- 工具只读；模型、工具和资料都由应用显式配置或批准。

课程不加入 handoff、agents-as-tools、多 Agent、人工审批、写操作、SandboxAgent、GUI、
Realtime/voice 或通用 runtime abstraction。最终 capstone 只使用公开合成资料和模拟只读
CLI，不包含公司名称、内部系统、真实服务地址、私有文档或真实数据。

## 学习方式

每章按“学习结果 → 核心内容 → 习题 → 实战 → 完成标准 → 版本与官方参考”组织；需要时
增加术语表。多个章节共同演进一个项目，不为每个概念复制 demo，也不提供最终 capstone
的完整答案。

建议顺序：

1. 阅读核心内容和删减后的官方示例；
2. 先完成概念题，再展开参考答案；
3. 在实战中补齐接口与测试骨架；
4. 运行检查并把证据写入学习日志。

## 环境

- Python 3.12
- `uv`
- `openai-agents==0.20.0`
- `prompt-toolkit==3.0.53`
- `rich==15.0.0`

依赖都记录在 `pyproject.toml` 并由 `uv.lock` 锁定：

```bash
uv sync
```

默认检查不调用真实模型：

```bash
uv lock --check
uv run ruff check .
uv run pyright
uv run pytest
uv run mkdocs build --strict
git diff --check
```

本地打开教材站：

```bash
uv run mkdocs serve
```

完整的站点编辑和双语维护说明见[教材站使用说明](docs/site-guide.md)。

## 显式模型配置

课程从不依赖 SDK 默认模型。每次真实模型练习都必须显式设置
`OPENAI_LEARNING_MODEL`：

```bash
export LEARNING_MODEL_PROVIDER=openai
export OPENAI_API_KEY=...
export OPENAI_LEARNING_MODEL=...
```

使用 OpenAI-compatible 端点时：

```bash
export LEARNING_MODEL_PROVIDER=openai-compatible
export OPENAI_LEARNING_MODEL=provider-model-id
export OPENAI_COMPATIBLE_BASE_URL=https://provider-endpoint
export OPENAI_COMPATIBLE_API_KEY=...
```

第三方端点默认走兼容范围更广的 Chat Completions API。只有供应商明确支持 Responses API
时才设置：

```bash
export OPENAI_COMPATIBLE_API=responses
```

课程代码统一通过 `load_learning_model()` 取得模型，并把 trace 写入仓库内忽略的
`.mlflow/mlflow.db`。模型调用与 tracing 完全分离：第三方模型只使用自己的端点和凭据，
tracing 不需要 `OPENAI_API_KEY`、代理或外部网络。

运行一次练习后，可在另一个终端启动本地 Trace viewer：

```bash
uv run mlflow server --host 127.0.0.1 --port 5000 \
  --backend-store-uri sqlite:///$PWD/.mlflow/mlflow.db \
  --default-artifact-root file://$PWD/.mlflow/artifacts
```

然后打开 `http://127.0.0.1:5000`，进入 `agents-sdk-learning-lab` experiment。

OpenAI-compatible 不表示完整支持工具、JSON Schema、Session 或 streaming。M05 要求对
锁定 SDK 与实际目标模型做一次显式 opt-in 兼容性 spike。不得把密钥写入仓库、fixture、
测试输出、学习日志或 shell 历史。

## 当前进度

M00 保持 `in_progress`；M01–M08 都保持 `pending`。从
[M00 中文教材](docs/lessons/m00-first-agent.md) 或
[M00 English lesson](docs/lessons/m00-first-agent.en.md) 开始。

## 许可与来源

本项目以 MIT 许可发布，详见 [LICENSE](LICENSE)。教材中的 SDK 接口以
`openai-agents==0.20.0`、OpenAI 官方开发者文档和
[openai/openai-agents-python](https://github.com/openai/openai-agents-python) 官方仓库为
事实来源。每章记录实际核对版本、日期和具体链接。本项目与 OpenAI 无隶属关系。
