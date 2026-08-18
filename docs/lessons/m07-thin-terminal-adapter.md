---
title: M07 · 薄终端适配器
description: 用 prompt-toolkit 处理输入、用单一输出所有者增量显示回答，并提供无 ANSI 的 plain mode。
---

<p class="lesson-kicker">M07 · 90 分钟 · 终端设计 + 实战</p>

# 薄终端适配器

<p class="lesson-deck">终端只负责输入、快捷键和显示；工作流、会话连续性与失败语义全部留在应用用例。</p>

<div class="lesson-meta" aria-label="课程信息">
  <span>prompt-toolkit 3.0.53</span>
  <span>Rich 15.0.0</span>
  <span>interactive + plain</span>
  <span>默认测试无需 TTY</span>
</div>

## 学习结果

学完本章后，你应该能够：

- 用 `PromptSession.prompt_async()` 读取异步输入、历史与有限快捷键；
- 让同一个终端组件在一次运行期间独占 stdout/cursor；
- 对 token delta 做小批次、append-only（只追加新文本，不重画旧内容）刷新；
- 只让 Rich 渲染已完成 Markdown、表格和有限状态信息；
- 提供无 ANSI 的 `--plain` 模式用于 SSH、重定向和测试；
- 把活动运行期间的 Ctrl-C 翻译为 `Cancel`，空闲时才退出；
- 用 fake event source 测试 renderer、批处理、plain mode 和取消。

!!! abstract "本章边界"

    第一版不是全屏 TUI，不使用 Rich Live，不重绘完整 transcript，也不允许输入组件和输出
    组件同时控制 cursor。终端不拥有 Agent loop、SDK Session、RunOutcome 或 active-run
    registry；它只调用 M06 用例。

## 核心内容

### 1. presentation adapter 的依赖方向

```text
prompt_toolkit input ─┐
                     ├─ Submit / Cancel → application use case
renderer ← events ───┘
```

终端模块可以导入 M06 的命令、事件和用例，但不能导入 Agents SDK event、`Runner`、
`SQLiteSession` 或工具实现。interactive 与 plain 模式必须构造同一个用例；如果两种模式有
两条 workflow，失败和会话语义迟早会分叉。

### 2. PromptSession 只负责输入

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory


def make_prompt_session(history_path: str) -> PromptSession[str]:
    return PromptSession(history=FileHistory(history_path))


async def read_command(session: PromptSession[str]) -> str:
    return await session.prompt_async("maintenance> ")
```

实战应再加入有限快捷键，例如清屏或取消当前输入；不要把业务命令解析塞进 key binding。
历史文件只保存用户已经提交的终端输入，因此真实应用还要公布保留策略；课程测试使用
`tmp_path`。`--plain` 在重定向环境可以关闭持久历史，避免自动化输入被意外保存。

主循环只在没有活动运行时显示 prompt。用户提交后，PromptSession 交出 cursor；renderer
独占输出直到该 turn settle，然后才显示下一个 prompt。

### 3. delta 小批次刷新，而不是每 token 重绘

每个 `MessageDelta` 先进入小 buffer，达到字节阈值或短时间阈值再 flush。例如初始参数可用
64 个字符或 40 ms；它们是 UI 参数，不改变应用事件。flush 只 append 新文本：

```text
delta → buffer → threshold reached → write(new_text) → flush
Final/Error → flush remainder → newline → completed metadata
```

不要在每个 token 上构造完整 transcript，也不要清屏后重画旧内容。这样重定向输出仍是正确
文本，慢速 SSH 不会因 cursor 控制持续闪动。测试注入 fake clock，不用真实 `sleep()` 等待。

流式阶段只追加纯文本，不尝试增量解释 Markdown。Rich 只处理已经闭合的 Markdown 内容、
完成后的 evidence/provenance 表格和有限状态行。已经流式显示的完整答案不得在 Final 时再次
重画；否则 transcript 会重复。

### 4. 一个对象拥有 stdout/cursor

给 renderer 一个很小的输出端口，例如 `write(text)`、`flush()` 和 `isatty()`。interactive
renderer 可以在完成时调用 Rich `Console.print(Markdown(...))` 或 `Table`；plain renderer
只调用文本 writer。两者都由同一个 terminal controller（终端主循环组件）顺序调用。

禁止的第一版结构：

```text
PromptSession 正在编辑输入
  同时 Rich Live 刷新状态
  同时后台 task print token
```

三个组件竞争 cursor 会破坏输入行、测试和重定向。若将来需要并发输入与输出，应作为新的
TUI 设计课题，而不是在当前 adapter 中偷偷加入。

### 5. plain mode 是完整产品路径

`--plain` 必须满足：

- 不输出 ANSI escape sequence；
- 不依赖终端宽度、颜色、cursor movement 或真实 TTY；
- stdin 每行仍转换成 `Submit`，Ctrl-C 规则保持相同；
- 使用与 interactive mode 相同的 application use case；
- `MessageDelta` 保持 append-only，工具和状态使用简短文本行；
- 适用于 SSH、`command | tee output.txt` 和自动测试。

不要只给 Rich Console 设置 `no_color=True` 就声称没有 ANSI。plain renderer 应走独立的纯
文本 writer，并在测试中断言输出不含 `\x1b`。

### 6. Ctrl-C 由运行状态决定含义

```text
no active run + Ctrl-C → exit terminal loop
active run + Ctrl-C    → Cancel(session_id, application_run_id)
                         → wait for cancelled outcome
                         → keep terminal open
```

controller 从 M06 得到当前 application run ID，再发 `Cancel`。它不直接调用
`RunResultStreaming.cancel()`。取消期间显示一条有限状态信息即可；不要打印堆栈，也不要
打印已经积累的完整对象。第二次 Ctrl-C 也不应绕过应用状态随意报告成功；实战要定义并
测试稳定行为。

### 7. renderer 只认识应用事件

| 事件 | interactive | plain |
| --- | --- | --- |
| `MessageDelta` | 进入 batching buffer | 进入同一个 batching buffer |
| `ToolStarted` | 简短状态行或 spinner 文本 | `[tool] name started` |
| `ToolFinished` | 完成分类，不显示原始输出 | `[tool] name: outcome` |
| `EvidenceFound` | 完成后汇总到 Rich Table | `evidence: ref` |
| `RunStateChanged` | 有限状态，不重画 transcript | `state: value` |
| `Final` | flush；呈现完成元数据 | flush；纯文本元数据 |
| `Error` | flush；安全错误说明 | `error CODE: safe message` |

使用 `match event.kind` 并让 pyright 覆盖 union。收到未知事件不应悄悄打印 SDK repr；在开发
阶段把它当作程序错误。

### 8. 测试不打开真实 TTY

fake event source 按固定时间或调用顺序送出事件；fake writer 收集每次 `write()`。测试：

1. 多个小 delta 在阈值前不 flush，达到阈值后只写新增片段；
2. Final 与 Error 都先 flush 尾部；
3. 已写内容不会被再次重画；
4. plain mode 完整输出不含 `\x1b`；
5. 工具 raw output 从未到达 writer；
6. active run 的 Ctrl-C 发 Cancel，idle Ctrl-C 退出；
7. 两种模式收到同一事件序列时，语义信息一致。

PromptSession 本身可以用注入的 fake input 或 controller 边界测试，不要求 pytest 连接真实
TTY。Rich 表格测试断言允许字段和基本文本，不断言每个空格或终端宽度。

## 习题

1. 为什么终端不能直接消费 `RunItemStreamEvent`？
2. PromptSession 在一次运行期间为什么要交出 cursor？
3. batching 的字符阈值和时间阈值分别解决什么问题？
4. 为什么增量 Markdown renderer 容易变脆？
5. Rich Live 为什么不适合作为本课程第一版？
6. `no_color=True` 为什么不足以证明 plain mode 无 ANSI？
7. Final 到达时为什么不能重画已经 streaming 的完整答案？
8. active run 的 Ctrl-C 应该发什么应用命令？
9. renderer 为什么只断言允许字段，不比较 SDK repr？
10. fake clock 怎样让 batching 测试更快、更确定？

## 实战：完成两个薄终端模式

1. 用 `PromptSession.prompt_async()` 实现异步输入、测试用历史和有限快捷键；
2. 让 controller 只构造 `Submit`/`Cancel` 并调用 M06 用例；
3. 实现可注入 clock/writer 的 delta buffer；
4. interactive renderer 只用 Rich 呈现已完成 Markdown、表格和有限状态；
5. 不使用全屏 Rich Live，不重画 transcript；
6. 实现 `--plain`，保证完整输出无 ANSI；
7. 实现 active/idle 两种 Ctrl-C 语义；
8. 用 fake event source 覆盖 renderer、batching、plain mode、取消和错误；
9. 断言同一事件序列在两种模式具有相同答案、状态和 evidence references；
10. 默认测试不得读取真实 TTY、API key 或网络。

完成标准：

- PromptSession 管输入，唯一 renderer 管输出；
- delta 小批次 append，不在每 token 重画 transcript；
- Rich 只渲染完成内容和有限元数据；
- plain mode 没有 ANSI，并复用同一用例；
- Ctrl-C 在 active 时取消、idle 时退出；
- fake 测试不需要真实 TTY 或模型。

## 术语表

| 术语 | 本课程含义 |
| --- | --- |
| presentation adapter | 把输入转成命令、把事件转成显示的薄边界 |
| batching | 按短时间或小尺寸合并相邻 delta 后 append |
| append-only | 只写新内容，不重绘既有 transcript |
| plain mode | 无 ANSI、无需 TTY 的等价终端路径 |

## 版本与官方参考

最后核对：2026-08-11。锁定：`prompt-toolkit==3.0.53`、`rich==15.0.0`、
`openai-agents==0.20.0`。

- [prompt-toolkit asynchronous prompts](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html)
- [prompt-toolkit history](https://python-prompt-toolkit.readthedocs.io/en/stable/pages/asking_for_input.html#history)
- [Rich Markdown](https://rich.readthedocs.io/en/stable/markdown.html)
- [Rich tables](https://rich.readthedocs.io/en/stable/tables.html)
- [Python signal handling](https://docs.python.org/3/library/signal.html)

示例改动：只采用 prompt-toolkit 的异步输入/历史能力和 Rich 的完成内容渲染；课程自己定义
单一输出所有者、delta batching、plain mode 与 Ctrl-C 命令翻译。完整终端实现仍由学习者
完成。
