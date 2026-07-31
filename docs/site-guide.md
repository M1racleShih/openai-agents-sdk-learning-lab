---
title: 教材站使用说明
description: 说明如何运行、编辑、检查和交接本项目的 MkDocs 教材站。
---

<p class="lesson-kicker">SITE GUIDE · READ · EDIT · VERIFY</p>

# 把 Markdown 教材变成网站

本页写给第一次进入仓库的读者、维护者和 coding agent。读完后，你应该能够独立完成
四件事：启动教材站、修改教材、维护中英文版本，以及验证生成结果。

## 1. MkDocs 在这里做什么

MkDocs 是一个静态文档网站生成器。它读取 Markdown、站点配置和样式文件，生成可以在
浏览器中打开的 HTML、CSS 和 JavaScript。

```text
docs/ 中的 Markdown 教材
          +
mkdocs.yml 中的导航和插件配置
          +
自定义 CSS 与 JavaScript
          ↓
        MkDocs
          ↓
site/ 中的静态网站
```

本项目在 MkDocs 上增加了三层能力：

| 组成 | 作用 |
| --- | --- |
| Material for MkDocs | 提供导航、搜索、代码复制、深浅色和响应式页面 |
| `mkdocs-static-i18n` | 生成中文和英文站点，并在同一页面之间切换语言 |
| 自定义样式与脚本 | 提供当前教材的配色、排版、课程卡片和阅读进度条 |

!!! tip "最重要的规则"

    编辑 `docs/` 中的 Markdown 和资源，不要编辑 `site/`。`site/` 是每次构建重新生成的
    结果，其中的手工修改会丢失。

## 2. 先认识项目中的文件

| 位置 | 用途 | 是否手工编辑 |
| --- | --- | --- |
| `mkdocs.yml` | 站点名称、导航、主题、语言、Markdown 扩展 | 是 |
| `docs/` | 教材的 Markdown 源文件 | 是 |
| `docs/assets/stylesheets/extra.css` | 教材视觉样式 | 是 |
| `docs/assets/javascripts/reading-progress.js` | 阅读进度条 | 是 |
| `pyproject.toml`、`uv.lock` | MkDocs 和插件的锁定版本 | 升级依赖时才编辑 |
| `site/` | 构建生成的静态网站，已被 Git 忽略 | 否 |

## 3. 第一次运行

在仓库根目录执行：

```bash
uv sync
uv run mkdocs serve
```

`uv sync` 安装项目锁定的依赖。`mkdocs serve` 启动本地开发服务器并监视文件变化。
终端会打印实际访问地址，通常类似：

```text
http://127.0.0.1:8000/openai-agents-sdk-learning-lab/
```

以终端打印的地址为准。打开后，修改 Markdown 或样式文件，MkDocs 会重新构建，浏览器
通常会自动刷新。

如果需要指定端口，可以运行：

```bash
uv run mkdocs serve --dev-addr 127.0.0.1:8123
```

端口必须未被其他程序占用。停止服务器时，在运行它的终端按 `Ctrl+C`。

## 4. 日常编辑流程

一次普通的教材修改只需要以下步骤：

1. 在 `docs/` 中找到对应的 Markdown 源文件；
2. 同步修改中文和英文版本；
3. 保持 `uv run mkdocs serve` 运行，在浏览器中检查排版和链接；
4. 完成后运行严格构建；
5. 查看 Git diff，确认没有修改生成目录或无关文件。

严格构建命令是：

```bash
uv run mkdocs build --strict
```

这个命令重新生成 `site/`。无效配置、无法解析的页面或 MkDocs warning 会让严格构建
失败，因此它比只看浏览器更适合作为交接前检查。

## 5. 中英文文件规则

站点使用 suffix 结构。中文是默认版本，英文在文件名中增加 `.en`：

```text
docs/topic.md
docs/topic.en.md
```

每对文档应保持相同的代码、命令、链接目标、状态、数字和完成标准。专业术语可以在
中文中保留英文，不必为了翻译改变接口名称。

在 `mkdocs.yml` 的主导航中只写默认文件名：

```yaml
nav:
  - 新页面: topic.md
```

再为英文导航标题增加翻译：

```yaml
nav_translations:
  新页面: New page
```

站内 Markdown 链接也优先指向默认文件名，例如：

```markdown
[M00](lessons/m00-first-agent.md)
```

构建英文站点时，i18n 插件会选择对应的 `.en.md` 页面。链接到章节锚点时，中文和英文
标题产生的锚点可能不同，应分别检查两个页面。

## 6. 新增一个教材页面

按以下顺序操作：

1. 新建中文 `docs/<name>.md`；
2. 新建英文 `docs/<name>.en.md`；
3. 在两份文件中写入相同范围的内容和完成标准；
4. 在 `mkdocs.yml` 的 `nav` 中加入默认文件；
5. 在英文语言配置的 `nav_translations` 中加入导航翻译；
6. 在浏览器中分别打开中文和英文页面，测试语言切换和站内链接；
7. 运行 `uv run mkdocs build --strict`。

如果页面只存在于一种语言，插件可以回退到默认版本，但本项目的用户文档不使用这种
回退作为常规做法。

## 7. 检查与交接

只修改教材时，至少运行：

```bash
uv run mkdocs build --strict
```

交接完整仓库改动前，再运行：

```bash
uv run ruff check .
uv run pyright
uv run pytest
```

最后确认：

- 中文和英文页面都能打开；
- 语言切换停留在同一章节；
- 代码块、表格、提示框和折叠答案正常显示；
- 没有失效的本地链接；
- `site/` 没有进入 Git；
- 文档和截图中没有 API key 或其他敏感数据。

## 8. 常见问题

### 找不到 `mkdocs` 命令

不要全局安装一个不同版本。先在仓库根目录运行：

```bash
uv sync
```

然后始终通过 `uv run mkdocs ...` 使用项目锁定版本。

### 端口已经被占用

换一个未占用端口：

```bash
uv run mkdocs serve --dev-addr 127.0.0.1:8124
```

### 修改后页面没有变化

确认修改的是 `docs/` 中的源文件，而不是 `site/`。查看运行服务器的终端是否完成重新
构建，然后刷新浏览器；仍无变化时，停止并重新运行 `uv run mkdocs serve`。

### 英文页面缺失或语言切换跳回首页

确认英文文件使用 `.en.md` 后缀，两个文件的相对位置和默认文件名一致，然后运行严格
构建查看具体错误。

### 构建输出一段公告或警告

先看命令最终退出状态。项目锁定的工具有时会输出上游项目公告；公告本身不等于构建
失败。真正的 warning 在 `--strict` 模式下会返回非零状态，应根据具体信息修复。

## Agent 操作清单

维护教材站的 agent 应遵守以下顺序：

1. 先阅读 `mkdocs.yml`、本页和相关教材源文件；
2. 查看 Git 状态，保留用户已有改动；
3. 只修改完成任务必需的 Markdown、配置或资源；
4. 同步维护中英文文件，不编辑 `site/`；
5. 运行严格构建，并在浏览器中检查受影响页面；
6. 检查本地链接、语言切换和敏感数据；
7. 交接时列出修改位置、运行命令和验证结果。

## 参考

- [MkDocs user guide](https://www.mkdocs.org/user-guide/)
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/)
- [MkDocs static i18n quick start](https://ultrabug.github.io/mkdocs-static-i18n/getting-started/quick-start/)
