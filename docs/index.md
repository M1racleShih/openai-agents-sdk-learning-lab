---
title: 课程首页
description: 用一个持续演进的项目，掌握单 Agent 只读终端应用的必要能力。
hide:
  - toc
---

<div class="course-hero" markdown>

<p class="hero-kicker">PRACTICAL FIELD GUIDE · SDK v0.20.0</p>

# 从一次真实运行开始

用约 11–13 小时，逐步构建一个单 Agent、只读、UI 无关、可流式交互且返回结构化结果的
终端助手。教材直接讲必需知识；官方资料放在章末用于追溯与升级核对。

[开始 M00](lessons/m00-first-agent.md){ .md-button .md-button--primary }
[查看完整路线](https://github.com/M1racleShih/openai-agents-sdk-learning-lab/blob/main/LEARNING_PLAN.md){ .md-button }

</div>

## 最终架构

```text
用户
  → 薄终端适配器
  → UI 无关的应用用例
  → 一个 Agents SDK Agent
  → 已批准的只读资料与只读 CLI/服务工具
  → 类型化事件 + 流式回答 + 结构化 RunOutcome
```

SDK 拥有 Agent loop、工具编排、Session、streaming 和 Trace；应用层拥有命令、用例、稳定
事件、失败分类和最少审计元数据；终端只拥有输入与展示。Session、Trace 和终端状态都不是
权威业务记录。

## 学习方式

<div class="learning-grid">
  <div class="learning-card">
    <span class="card-index">01</span>
    <h3>核心内容</h3>
    <p>先建立完成最小应用所需的准确心智模型，不系统浏览无关功能。</p>
  </div>
  <div class="learning-card">
    <span class="card-index">02</span>
    <h3>习题与骨架</h3>
    <p>用概念题、接口片段、事件映射和测试骨架检查理解，不复制完整答案。</p>
  </div>
  <div class="learning-card">
    <span class="card-index">03</span>
    <h3>可验证实战</h3>
    <p>默认测试使用 fake runner、stream 和 event source；真实模型与终端运行显式 opt-in。</p>
  </div>
</div>

## 模块地图

| 模块 | 主题 | 状态 |
| --- | --- | --- |
| M00 | 首个可观察 Agent | `in_progress` |
| M01 | 结构化结果与本地 context | `pending` |
| M02 | 只读工具与来源边界 | `pending` |
| M03 | 有界运行与真实失败 | `pending` |
| M04 | Trace、最小元数据与确定性测试 | `pending` |
| M05 | Sessions、streaming 与取消 | `pending` |
| M06 | UI 无关用例与类型化事件 | `pending` |
| M07 | 薄终端适配器 | `pending` |
| M08 | 公开 capstone 与就绪评审 | `pending` |

课程明确不加入 handoff、agents-as-tools、多 Agent、审批、写操作、SandboxAgent、GUI 或
通用 runtime framework。

## 当前模块

<div class="module-panel">
  <div class="module-number" aria-hidden="true">M00</div>
  <div class="module-copy">
    <span class="status-badge">学习中 · IN PROGRESS</span>
    <h3>首个可观察 Agent</h3>
    <p>区分 <code>Agent</code>、<code>Runner.run</code> 与 <code>RunResult</code>，看懂最小
    Agent loop，并在 Trace viewer 中找到第一次真实模型调用。</p>
    <p><strong>45 分钟 · 9 道巩固题 · 1 个编码练习 · 1 次 trace 检查</strong></p>
    <a class="module-link" href="lessons/m00-first-agent/">进入教材 →</a>
  </div>
</div>

## 模型配置

课程从不依赖 SDK 默认模型，统一通过 `load_learning_model()` 读取显式配置。

=== "OpenAI"

    ```bash
    export LEARNING_MODEL_PROVIDER=openai
    export OPENAI_API_KEY=...
    export OPENAI_LEARNING_MODEL=...
    ```

=== "OpenAI-compatible"

    ```bash
    export LEARNING_MODEL_PROVIDER=openai-compatible
    export OPENAI_LEARNING_MODEL=provider-model-id
    export OPENAI_COMPATIBLE_BASE_URL=https://provider-endpoint
    export OPENAI_COMPATIBLE_API_KEY=...
    ```

    第三方默认使用 `chat_completions`。只有供应商明确支持 Responses API 时才设置
    `OPENAI_COMPATIBLE_API=responses`。

!!! info "模型调用与 tracing 是独立链路"

    第三方兼容模型只连接其配置的模型端点。课程把 trace 保存在本地 MLflow SQLite
    数据库中，不需要 `OPENAI_API_KEY`、代理或外部 tracing 服务。

运行练习后，用 `uv run mlflow server --backend-store-uri sqlite:///$PWD/.mlflow/mlflow.db`
启动本地 Trace viewer，再打开 `http://127.0.0.1:5000`。

## 本地打开教材站

```bash
uv sync
uv run mkdocs serve
```

发布前运行 `uv run mkdocs build --strict`。完整说明见[教材站使用说明](site-guide.md)。
