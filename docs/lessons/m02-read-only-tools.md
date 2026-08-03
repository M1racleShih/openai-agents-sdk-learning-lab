---
title: M02 · 有边界的只读工具
description: 从 Python 函数生成工具 schema，并限制路径、参数、超时和错误传播。
---

<p class="lesson-kicker">M02 · 90 分钟 · 概念 + 实战</p>

# 有边界的只读工具

<p class="lesson-deck">只注册任务需要的读取能力，并让越界、超时和底层失败直接暴露。</p>

<div class="lesson-meta" aria-label="课程信息">
  <span>SDK v0.19.1</span>
  <span>10 道巩固题</span>
  <span>2 个只读工具</span>
  <span>5 项直接检查</span>
</div>

## 学习结果

学完本章后，你应该能够：

- 用 `function_tool` 把一个带类型标注和 docstring 的 Python 函数变成工具；
- 查看工具名称、说明和 `params_json_schema`；
- 只把完成任务必需的工具放入 `Agent.tools`；
- 用 Pydantic `Field` 限制模型可以提交的参数；
- 阻止相对路径、绝对路径和符号链接逃出允许的资料根目录；
- 给异步工具设置单次超时；
- 选择工具异常是返回给模型，还是继续抛给应用；
- 说明工具返回值怎样进入下一轮模型输入；
- 不调用模型，直接测试读取逻辑和模拟服务逻辑。

!!! abstract "本章边界"

    本章只添加本地只读函数工具及其直接测试。它不添加写工具、hosted tool、MCP、
    approval、session 或 handoff，也不统一定义运行级失败结果；M03 会处理最后一项。

## 核心内容

### 1. `function_tool` 把 Python 接口变成模型可调用的工具

模型不能直接调用任意 Python 函数。应用先用 `function_tool` 创建一个 `FunctionTool`，
再把这个对象放入 `Agent.tools`。`v0.19.1` 会读取函数签名和 docstring：

```text
函数名                           → 工具名
docstring 第一段                 → 工具说明
参数名与类型标注                 → JSON schema 字段与类型
docstring 中的参数说明           → schema 字段说明
Pydantic Field                  → 长度、范围、格式等约束
```

SDK 使用 Python `inspect` 读取签名，用 `griffe` 解析 docstring，再用 Pydantic 生成参数
模型和 JSON schema。默认启用严格 schema。

```python
from typing import Annotated

from agents import function_tool
from pydantic import Field


SourceId = Annotated[
    str,
    Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$"),
]


@function_tool
def find_public_title(source_id: SourceId) -> str:
    """Return the public title for one source.

    Args:
        source_id: Stable identifier of the source to read.
    """
    return {"guide": "Public guide"}[source_id]
```

装饰后，`find_public_title` 是 `FunctionTool`，不是原来的 Python 函数。可以在不调用模型
的情况下检查生成结果：

```python
print(find_public_title.name)
print(find_public_title.description)
print(find_public_title.params_json_schema)
```

类型约束先检查模型生成的调用参数。它们不能代替函数内部的权限检查。例如，正则表达式
可以限制 `source_id` 的字符，却不能判断一条路径最终落在磁盘的哪个目录。

### 2. allowlist 是代码实际注册的工具集合

工具 allowlist 就是这次运行实际交给 Agent 的工具集合。只在 instructions 中写“不要
修改文件”不够；如果 `Agent.tools` 中存在写工具，模型仍然拥有这项能力。

```python
READ_ONLY_TOOLS = [read_public_note, query_public_catalog]

agent = Agent[LessonContext](
    name="Evidence reader",
    instructions="Use only the supplied sources and return concise evidence.",
    tools=READ_ONLY_TOOLS,
)
```

检查 allowlist 时看代码，不看工具名称：

- `read_public_note` 只以读取模式打开受限目录中的文本；
- `query_public_catalog` 只调用模拟客户端的查询方法；
- 集合中没有创建、修改、删除、上传或执行命令的入口；
- 工具拿到的客户端凭据和资料根目录留在本地 context，不出现在 schema 中。

`RunContextWrapper[LessonContext]` 可以作为函数的第一个参数。SDK 会把它传给本地函数，
但不会把它放入模型可见的参数 schema。其余参数才由模型填写。

### 3. 路径边界必须在打开文件前检查

下面的普通函数展示最小路径检查。它要求调用方提供相对路径，解析 `..` 和符号链接，
再确认最终路径仍在允许根目录中。

```python
from pathlib import Path


def read_text_from_root(root: Path, relative_path: str) -> str:
    """Read one UTF-8 text file below root."""
    requested = Path(relative_path)
    if requested.is_absolute():
        raise ValueError("path must be relative")

    allowed_root = root.resolve()
    candidate = (allowed_root / requested).resolve()
    try:
        candidate.relative_to(allowed_root)
    except ValueError as exc:
        raise ValueError("path is outside the allowed source root") from exc

    if candidate.suffix != ".txt" or not candidate.is_file():
        raise ValueError("path must name an existing .txt file")
    return candidate.read_text(encoding="utf-8")
```

不要用字符串 `startswith` 判断目录。`/fixtures-old` 会以 `/fixtures` 开头，却不是它的
子目录。`Path.resolve()` 加 `relative_to()` 检查的是解析后的路径组成部分，也能发现指向
根目录外的符号链接。

这个检查假设 fixture 目录由应用管理，任务执行期间不会被不受信任的进程改动。若其他
进程可以同时替换文件或符号链接，还需要操作系统级隔离或基于目录描述符的安全打开方式；
这些内容不属于本课程的本地 fixture 场景。

工具包装应该很薄：从本地 context 取出允许根目录，再调用上面的普通函数。

```python
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

from agents import RunContextWrapper, function_tool
from pydantic import Field


@dataclass
class LessonContext:
    allowed_source_root: Path
    catalog: "PublicCatalog"


RelativePath = Annotated[str, Field(min_length=1, max_length=160)]


@function_tool(failure_error_function=None)
def read_public_note(
    ctx: RunContextWrapper[LessonContext],
    relative_path: RelativePath,
) -> str:
    """Read one UTF-8 public note from the allowed source directory.

    Args:
        relative_path: Relative path of the text file below the allowed root.
    """
    return read_text_from_root(ctx.context.allowed_source_root, relative_path)
```

这里显式传入 `failure_error_function=None`。文件不存在或路径越界时，异常不会被改写成
一段看似正常的工具数据。

### 4. 异步工具需要单次超时和明确的错误策略

外部查询即使只读，也可能一直等待。`v0.19.1` 的异步函数工具可以设置 `timeout`。本课程
选择 `timeout_behavior="raise_exception"`，让 `ToolTimeoutError` 结束运行，再由 M03 的
应用包装层转换成稳定的 `WorkerResult`。

```python
from typing import Annotated, Protocol

from agents import RunContextWrapper, function_tool
from pydantic import Field


class PublicCatalog(Protocol):
    async def fetch(self, source_id: str) -> str: ...


async def fetch_public_entry(client: PublicCatalog, source_id: str) -> str:
    return await client.fetch(source_id)


CatalogId = Annotated[
    str,
    Field(min_length=1, max_length=64, pattern=r"^[a-z0-9_-]+$"),
]


@function_tool(
    failure_error_function=None,
    timeout=2.0,
    timeout_behavior="raise_exception",
)
async def query_public_catalog(
    ctx: RunContextWrapper[LessonContext],
    source_id: CatalogId,
) -> str:
    """Query one entry from the read-only public catalog.

    Args:
        source_id: Stable identifier of the catalog entry.
    """
    return await fetch_public_entry(ctx.context.catalog, source_id)
```

这段代码只展示连接方式；为了让片段保持最小，`LessonContext.catalog` 和模拟客户端留给
实战补齐。

`function_tool` 的默认异常策略会把工具异常改成模型可见的错误消息，让模型有机会恢复。
默认超时策略 `error_as_result` 也会返回明确的超时消息。这些策略适合允许模型重试或改用
其他工具的流程。本课程的 worker 需要由上层程序稳定判断失败，所以让两类异常继续抛出。
不要捕获异常后返回空字符串、空列表或“没有结果”；这些值会把失败伪装成正常数据。

!!! note "超时只适用于异步函数工具"

    `v0.19.1` 只支持给异步 `function_tool` handler 设置超时。需要超时的服务查询应写成
    `async def`。

### 5. 工具返回值会进入下一轮模型输入

一次工具调用按以下顺序发生：

```text
模型生成工具名和 JSON 参数
  → SDK 按 params_json_schema 检查参数
  → 本地 Python 函数读取 context 并执行
  → SDK 创建 function_call_output
  → 工具输出进入下一轮模型输入
  → 模型根据资料继续调用工具或生成最终结果
```

因此工具返回值属于模型上下文。只返回完成任务需要的文本；调用方需要来源时，再附上
稳定的来源标识。不要返回 logger、客户端、凭据、允许根目录、完整异常堆栈或无关服务
字段。

普通字符串会直接成为工具输出；其他普通对象通常会先转换成字符串。若要稳定的 JSON，
应由应用显式序列化，而不是依赖对象的 `str()`。无论格式怎样，工具 schema 只约束输入，
不会自动证明返回数据正确或安全。

### 6. 直接测试普通逻辑，再检查工具包装

工具逻辑不需要模型参与。把文件读取和服务查询写成接收普通依赖的函数，测试可以直接
传入临时目录或假的客户端：

```python
def test_reader_rejects_parent_escape(tmp_path: Path) -> None:
    allowed_root = tmp_path / "fixtures"
    allowed_root.mkdir()

    with pytest.raises(ValueError, match="outside"):
        read_text_from_root(allowed_root, "../private.txt")


@pytest.mark.asyncio
async def test_catalog_failure_is_not_normal_data() -> None:
    client = FailingCatalog()

    with pytest.raises(ConnectionError):
        await fetch_public_entry(client, "guide")
```

这些片段故意没有给出 `FailingCatalog`、成功场景和工具包装检查的完整实现。实战需要你
自己补齐。工具包装另做小检查：确认名称、schema 约束、`timeout_seconds`、
`timeout_behavior` 和最终 allowlist。这样即使没有 API key，也能验证权限边界和错误行为。

## 习题

先完成问题，再展开参考答案。

### 概念与代码阅读

1. `function_tool` 从哪些 Python 信息生成工具名、说明和参数 schema？
2. 为什么 `RunContextWrapper[LessonContext]` 不会成为模型可填写的工具参数？
3. 判断正误：instructions 写了“只读”以后，`Agent.tools` 中可以保留写工具。
4. `Field(pattern=...)` 为什么不能代替文件路径的根目录检查？
5. 为什么字符串 `startswith` 不能可靠判断路径是否位于允许目录？
6. 符号链接指向允许根目录外时，上面的代码在哪一步拒绝它？
7. 工具返回的文本随后会被谁看到？为什么返回值也要最小化？
8. `failure_error_function=None` 对工具 handler 抛出的异常有什么影响？
9. `timeout_behavior="raise_exception"` 与默认的 `error_as_result` 有什么区别？
10. 为什么直接测试 `read_text_from_root` 和 `fetch_public_entry` 比让模型调用工具更适合
    验证边界？

<details class="exercise-answers">
<summary>参考答案</summary>

1. 默认用函数名作为工具名，用 docstring 第一段作为工具说明，用参数名和类型标注生成
   字段与类型，并从 docstring 参数段和 Pydantic `Field` 补充说明与约束。
2. SDK 识别第一个 `RunContextWrapper` 参数并在本地注入它；模型只填写其余 schema 参数。
3. 错。真正的能力边界是代码注册的工具集合。写工具存在于 `Agent.tools` 中，就仍然可能
   被模型调用。
4. `Field` 检查字符串形状，不知道目录、`..` 或符号链接解析后的磁盘位置。函数仍要在
   打开文件前检查最终路径。
5. 两个不同目录名可以拥有相同的字符串前缀，例如 `/fixtures` 和 `/fixtures-old`。
6. `resolve()` 先得到符号链接的目标路径，随后 `candidate.relative_to(allowed_root)` 因目标
   不在根目录中而抛出 `ValueError`。
7. SDK 把工具输出放入 `function_call_output`，下一轮模型调用会看到它。因此返回值也不能
   包含凭据、本地路径或无关私有数据。
8. SDK 不会把 handler 异常转换成默认的模型可见错误字符串，而是继续抛出异常。
9. 前者抛出 `ToolTimeoutError` 并让运行失败；后者把明确的超时消息作为工具结果交给模型，
   让模型决定是否恢复。
10. 普通函数测试没有模型随机性、网络费用或 API key 依赖，可以精确构造成功、越界和
    底层失败，并直接断言结果或异常；还可以单独检查工具包装的超时配置。

</details>

### 实战：实现两个有边界的只读工具

在上一章的数据模型和本地 context 基础上完成以下任务。你可以新建
`src/evidence_worker/tools.py` 和 `tests/test_tools.py`，但不要复制本章片段作为完整答案。

1. 在 `fixtures/` 下准备公开练习文本；工具只能读取这个目录中的 UTF-8 `.txt` 文件；
2. 实现一个接收根目录和相对路径的普通读取函数，再用 `function_tool` 做薄包装；
3. 拒绝绝对路径、`..` 越界、指向根目录外的符号链接、非 `.txt` 文件和不存在的文件；
4. 实现一个只支持查询的模拟服务客户端，并把它放入 M01 的本地 context；
5. 实现一个接收模拟客户端和资料标识的普通异步查询函数，再做薄工具包装；
6. 给异步工具设置 2 秒单次超时，并让 handler 异常和超时继续抛出；
7. 给两个模型可填参数加上必要的长度或格式约束；
8. 只把这两个工具注册给 Agent，确认 allowlist 中没有写操作；
9. 不调用模型，直接覆盖以下 4 项：文本读取成功、路径边界、查询成功、底层查询失败；
   路径边界检查应包含绝对路径、`..`、越界符号链接、非 `.txt` 文件和不存在的文件；
10. 第 5 项直接检查生成的工具名称、参数 schema、`timeout_seconds=2.0`、
    `timeout_behavior="raise_exception"` 和最终 allowlist。

先运行工具测试，再运行完整仓库检查：

```bash
uv run pytest tests/test_tools.py -q
uv run ruff check .
uv run pyright
uv run pytest
```

完成标准：

- Agent 的工具集合中只有两个只读入口；
- 任何提供给工具的路径都不能逃出允许的 fixture 根目录；
- 参数不合法、文件缺失、底层异常和超时都不会变成正常数据；
- 5 项直接检查都不调用模型，也不需要 API key；
- 能指出每个工具返回给模型的准确字段或文本；
- 仓库检查全部通过。

本章没有给出实战的完整实现。核心内容分别展示了 schema、路径检查、超时和直接测试的
最小片段；你需要自己定义模拟客户端、组合 context、完成两个工具并补齐全部测试。

## 参考

本章最后核对日期：2026-08-01。项目锁定版本：`openai-agents==0.19.1`。

- [当前 Agents SDK 指南：工具定位](https://developers.openai.com/api/docs/guides/tools#usage-in-the-agents-sdk)
- [`v0.19.1` Tools：function tools](https://github.com/openai/openai-agents-python/blob/v0.19.1/docs/tools.md#function-tools)
- [`v0.19.1` function schema 源码](https://github.com/openai/openai-agents-python/blob/v0.19.1/src/agents/function_schema.py)
- [`v0.19.1` function tool 与超时源码](https://github.com/openai/openai-agents-python/blob/v0.19.1/src/agents/tool.py)
- [`v0.19.1` 基础工具示例](https://github.com/openai/openai-agents-python/blob/v0.19.1/examples/basic/tools.py)
- [Python `pathlib`：解析路径与 `relative_to`](https://docs.python.org/3.12/library/pathlib.html)

示例改动：把官方天气工具改成受限文本读取和只读目录服务查询；加入本地 context、Pydantic
参数约束、解析后路径检查、显式异常传播和 2 秒单次超时；把工具 handler 拆成可直接测试
的普通函数；省略完整 Agent 运行、hosted tools、MCP、handoff、approval 和实战完整答案。
