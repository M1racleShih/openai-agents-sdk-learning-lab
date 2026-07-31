# OpenAI Agents SDK Learning Lab

[English](README-en.md)

一个面向资深 Python 工程师的短周期实战项目：通过逐步构建有边界的只读证据
worker，掌握开发真实 OpenAI Agents SDK 应用所需的最小知识。

## 学习结果

完成全部模块后，学习者应能独立实现并解释：

- 单个 `Agent` 与 `Runner` 的运行循环；
- Pydantic 结构化输入和输出；
- 只读函数工具及本地运行上下文；
- 超时、turn 上限、不完整结果和失败传播；
- 脱敏 tracing、确定性测试和真实 smoke run；
- 供另一个运行时调用的 JSON-in/JSON-out worker。

完整路线见 [LEARNING_PLAN.md](LEARNING_PLAN.md)，进度和验证证据见
[LEARNING_LOG.md](LEARNING_LOG.md)。

## 学习方式

教材会先讲清本章必须掌握的概念，再给出经过删减或改写的官方示例。学习者只需
阅读教材；官方文档放在文末，供追溯来源和升级 SDK 时核对。

学习顺序很简单：

1. 阅读核心内容和示例；
2. 完成概念题、代码阅读题或判断题；
3. 在需要实际验证时完成编码练习；
4. 运行检查并记录结果。

编码练习不要求每章都有。几个连续章节可以共用一次实战，避免为了流程重复写
demo。课程中的示例优先取自项目锁定版本的官方 examples，并删掉与当前目标无关
的功能。

本项目不预先教授 handoff、sessions、streaming、Realtime、voice、sandbox
agents 或通用多 Agent 框架。

## 环境

- Python 3.12
- `uv`
- `openai-agents` 0.19.1

初始化：

```bash
uv sync
```

运行仓库检查：

```bash
uv run ruff check .
uv run pyright
uv run pytest
```

### 打开教材站

教材使用 Markdown 编写，并由 MkDocs Material 生成 HTML 页面：

```bash
uv run mkdocs serve
```

发布前运行严格构建检查：

```bash
uv run mkdocs build --strict
```

完整的运行、编辑、双语维护和故障排查流程见
[教材站使用说明](docs/site-guide.md)。

### 选择模型供应商

所有真实模型练习都要求显式设置 `OPENAI_LEARNING_MODEL`。默认使用 OpenAI：

```bash
export LEARNING_MODEL_PROVIDER=openai
export OPENAI_API_KEY=...
export OPENAI_LEARNING_MODEL=...
```

也可以接入任意提供 OpenAI-compatible 端点的模型服务：

```bash
export LEARNING_MODEL_PROVIDER=openai-compatible
export OPENAI_LEARNING_MODEL=provider-model-id
export OPENAI_COMPATIBLE_BASE_URL=https://provider-endpoint
export OPENAI_COMPATIBLE_API_KEY=...
```

第三方默认使用兼容范围更广的 Chat Completions API。只有供应商明确支持
Responses API 时才切换：

```bash
export OPENAI_COMPATIBLE_API=responses
```

常见配置示例：

| 服务 | `OPENAI_COMPATIBLE_BASE_URL` | 模型 ID 示例 | API 形状 |
| --- | --- | --- | --- |
| [MiniMax（中国区）](https://platform.minimaxi.com/docs/guides/text-generation) | `https://api.minimaxi.com/v1` | `MiniMax-M2.7` | `chat_completions` |
| [DeepSeek](https://api-docs.deepseek.com/guides/multi_round_chat) | `https://api.deepseek.com` | `deepseek-v4-flash` | `chat_completions` |
| [智谱 GLM](https://docs.bigmodel.cn/cn/guide/develop/openai/introduction) | `https://open.bigmodel.cn/api/paas/v4` | `glm-5.2` | `chat_completions` |

例如，复用已有的供应商专用环境变量时，不需要复制或改名原密钥：

```bash
export LEARNING_MODEL_PROVIDER=openai-compatible
export OPENAI_COMPATIBLE_API_KEY="$MINIMAX_API_KEY"
export OPENAI_COMPATIBLE_BASE_URL=https://api.minimaxi.com/v1
export OPENAI_LEARNING_MODEL=MiniMax-M3
export OPENAI_COMPATIBLE_API=responses
```

将上面的密钥变量、Base URL、模型 ID 和 API 形状替换后，同一加载器也适用于
DeepSeek、GLM、其他云服务或本地兼容端点。

课程代码通过 `load_learning_model()` 取得模型，因此 Agent 与 Runner 的练习不需要
包含供应商判断：

```python
from evidence_worker.model_provider import load_learning_model

agent = Agent(..., model=load_learning_model())
```

第三方模型请求和 OpenAI tracing 使用不同密钥。没有 OpenAI API key 时，运行前关闭
tracing：

```bash
export OPENAI_AGENTS_DISABLE_TRACING=1
```

如果仍需在 OpenAI Trace viewer 中验收，则保留独立的 `OPENAI_API_KEY`，并且不要
关闭 tracing。Trace 可能包含模型输入和输出，练习中不要使用敏感数据。

“OpenAI-compatible”不表示完整支持 OpenAI 的所有能力。不同端点对工具调用、结构化
输出、流式事件和 Responses API 的兼容程度可能不同；进入相关课程模块前，应针对所需
能力做一次真实 smoke test。

不要把任何密钥写入仓库、测试 fixture、学习日志或 shell 历史。

## 当前进度

M00 正在学习：阅读 [中文教材](docs/lessons/m00-first-agent.md) 或
[English lesson](docs/lessons/m00-first-agent.en.md)，完成习题和第一次可追踪的 Agent
运行。
