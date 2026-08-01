---
title: 课程首页
description: 用一个持续演进的项目，快速掌握 OpenAI Agents SDK 的必要能力。
hide:
  - toc
---

<div class="course-hero" markdown>

<p class="hero-kicker">PRACTICAL FIELD GUIDE · SDK v0.19.1</p>

# 从一次真实运行开始

用一个持续演进的 Python 项目，学会构建有边界、可观察、可测试的只读 evidence worker。
教材直接讲必需知识；官方资料只放在文末用于追溯。

[开始 M00](lessons/m00-first-agent.md){ .md-button .md-button--primary }
[查看完整路线](https://github.com/M1racleShih/openai-agents-sdk-learning-lab/blob/main/LEARNING_PLAN.md){ .md-button }

</div>

## 学习方式

<div class="learning-grid">
  <div class="learning-card">
    <span class="card-index">01</span>
    <h3>核心内容</h3>
    <p>先建立准确、够用的心智模型。教材已经筛掉当前任务不需要的接口和概念。</p>
  </div>
  <div class="learning-card">
    <span class="card-index">02</span>
    <h3>习题</h3>
    <p>用概念问答、流程判断和代码阅读检查理解；答案放在可展开区域中。</p>
  </div>
  <div class="learning-card">
    <span class="card-index">03</span>
    <h3>实战</h3>
    <p>只有需要观察真实行为时才编码。多个概念章节也可以共用一次实战。</p>
  </div>
</div>

## 当前模块

<div class="module-panel">
  <div class="module-number" aria-hidden="true">M00</div>
  <div class="module-copy">
    <span class="status-badge">学习中 · IN PROGRESS</span>
    <h3>第一次运行 Agent</h3>
    <p>区分 <code>Agent</code>、<code>Runner.run</code> 与 <code>RunResult</code>，看懂最小
    agent loop，并在 Trace viewer 中找到第一次真实模型调用。</p>
    <p><strong>45 分钟 · 7 道巩固题 · 1 个编码练习 · 1 次 trace 检查</strong></p>
    <a class="module-link" href="lessons/m00-first-agent/">进入教材 →</a>
  </div>
</div>

## 模型配置

课程代码统一通过 `load_learning_model()` 读取模型。Agent 和 Runner 的练习不需要包含
供应商判断。

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

    第三方端点默认使用 `chat_completions`。只有供应商明确支持 Responses API 时才设置：

    ```bash
    export OPENAI_COMPATIBLE_API=responses
    ```

!!! warning "模型调用与 tracing 是两条独立链路"

    第三方兼容模型可以完成模型调用练习，但 OpenAI Trace viewer 仍需要单独的
    `OPENAI_API_KEY`。没有这个 key 时，应设置 `OPENAI_AGENTS_DISABLE_TRACING=1`；此时
    可以运行练习，但还没有通过 M00 的 trace 检查。

## 在本地打开教材站

教材仍然用 Markdown 编写，MkDocs Material 在本地生成 HTML 页面：

```bash
uv sync
uv run mkdocs serve
```

终端会显示本地地址。修改教材后，浏览器会自动刷新。发布前使用严格构建检查：

```bash
uv run mkdocs build --strict
```

完整的编辑、双语维护和故障排查流程见[教材站使用说明](site-guide.md)。

!!! info "当前范围"

    站点目前开放首页、M00、M01、M02、M03 和 M04。学习路线、进度日志和后续模块仍保留在仓库中，
    后续教材会按既定路线逐步接入。
