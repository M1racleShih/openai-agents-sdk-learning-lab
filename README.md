# OpenAI Agents SDK Learning Lab

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

每个模块都执行同一个闭环：

1. 阅读导师提炼的短讲义；
2. 定点核对少量官方文档；
3. 学习者亲手完成关键 SDK 代码；
4. 运行正常和故障场景；
5. 不看笔记解释设计边界；
6. 通过验收后提交一个里程碑。

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

真实模型练习需要通过本机环境提供 `OPENAI_API_KEY`。不要把密钥写入仓库、测试
fixture、学习日志或 shell 历史。

## 当前进度

M00 已准备：阅读 [第一课讲义](lessons/m00-first-agent.md)，然后在导师引导下
完成首个可追踪的 Agent 运行。
