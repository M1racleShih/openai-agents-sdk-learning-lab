---
title: M02 · 有边界的只读工具
description: 从 Python 函数生成工具 schema，并限制路径、参数、超时和错误传播。
---

<p class="lesson-kicker">M02 · 105 分钟 · 概念 + 实战</p>

# 有边界的只读工具

<p class="lesson-deck">只把任务需要的读取能力交给模型；越界、超时和底层出错时，让错误直接暴露，而不是装成正常结果。</p>

<div class="lesson-meta" aria-label="课程信息">
  <span>SDK v0.20.0</span>
  <span>14 道巩固题</span>
  <span>3 个只读工具</span>
  <span>全部测试不调用模型</span>
</div>

## 学习结果

学完本章后，你应该能够：

- 用 `function_tool` 把一个带类型标注和 docstring 的 Python 函数变成工具；
- 不调用模型，直接查看生成的工具名称、说明和 `params_json_schema`；
- 只把完成任务必需的工具放进 `Agent.tools`；
- 用 Pydantic `Field` 限制模型能提交的参数；
- 挡住三类逃出资料根目录的路径：`..`、绝对路径和指向根目录外的符号链接；
- 给异步工具设置单次超时；
- 决定工具异常是返回给模型，还是继续抛给应用；
- 说明工具返回值怎样进入下一轮模型输入；
- 用 `source_id`、`revision` 和 `sha256` 记录实际读取的资料是哪一份、哪个版本；
- 用 `asyncio.create_subprocess_exec` 包装一个固定只读的模拟 CLI；
- 限制 CLI 的子命令、参数、环境、时间、stdout 和 stderr；
- 不调用模型，直接测试资料读取、模拟服务和 CLI adapter。

!!! abstract "本章边界"

    本章只添加本地只读函数工具和它们的直接测试。不添加写工具、hosted tool、MCP、
    approval、Session、handoff、通用命令解析器或 sandbox；运行级失败结果的统一定义
    留给 M03。

## 核心内容

### 1. 用 `function_tool` 把 Python 函数变成模型能调用的工具

模型不能直接调用你的 Python 函数。要先把函数交给 `function_tool` 包装成
`FunctionTool`，再放进 `Agent.tools`。`v0.20.0` 从函数本身读取生成工具所需的信息：

```text
函数名                           → 工具名
docstring 第一段                 → 工具说明
参数名与类型标注                 → JSON schema 字段与类型
docstring 中的参数说明           → schema 字段说明
Pydantic Field                  → 长度、范围、格式等约束
```

SDK 用 `inspect` 读取函数签名，用 `griffe` 解析 docstring，再用 Pydantic 生成参数
模型和 JSON schema。默认启用严格 schema（拒绝 schema 之外的多余字段和宽松类型
转换）。

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

装饰之后，`find_public_title` 不再是原来的 Python 函数，而是一个 `FunctionTool`
对象。不用调用模型，就能检查生成的结果：

```python
print(find_public_title.name)
print(find_public_title.description)
print(find_public_title.params_json_schema)
```

注意 `Field` 约束生效的位置：它检查模型提交的参数，发生在函数运行之前。它不能
代替函数内部的权限检查。正则表达式能限制 `source_id` 里出现哪些字符，却判断不了
一条路径解析后落在磁盘的哪个目录——那要靠函数内部的检查（第 4 节）。

### 2. 真正的能力边界：`Agent.tools` 里注册了什么

本章说到"工具 allowlist"，指的就是这次运行实际放进 `Agent.tools` 的工具集合。
判断模型有没有某项能力，看这个集合里注册了什么，不看 instructions 写了什么。只在
instructions 里写"不要修改文件"是不够的：只要写工具还注册在集合里，模型就仍然
可能调用它。

```python
READ_ONLY_TOOLS = [read_public_note, query_public_catalog]

agent = Agent[LessonContext](
    name="Evidence reader",
    instructions="Use only the supplied sources and return concise evidence.",
    tools=READ_ONLY_TOOLS,
)
```

检查 allowlist 时看代码实际做了什么，不看工具叫什么名字：

- `read_public_note` 只用读取模式打开受限目录中的文本；
- `query_public_catalog` 只调用模拟客户端的查询方法；
- 集合里没有创建、修改、删除、上传或执行命令的入口；
- 客户端凭据和资料根目录放在本地 context 里，不出现在工具的参数 schema 中。

工具函数还能通过第一个参数拿到本地 context：SDK 注入它，模型看不到它，也填不了
它。写法和原理见第 4 节的工具包装示例；这两个工具本身也分别在第 4 节和第 5 节
定义，本节只用到它们的名字。

### 3. 每份资料都要能查证：是哪一份、哪个版本、有没有被改过

"路径在允许目录里"只回答了能不能读，还没回答两个更关键的问题：读到的是哪个
版本？内容和批准时一致吗？所以每份资料都要留下能复查的记录。做法分两步：应用先
维护一份最小的批准清单，登记每份允许读取的资料；读取时，把模型提交的 `source_id`
换成清单里登记的固定路径和完整性信息。

```python
from pydantic import BaseModel


class ApprovedSource(BaseModel):
    source_id: str
    relative_path: str
    revision: str
    sha256: str


class SourceProvenance(BaseModel):
    source_id: str
    revision: str
    sha256: str
```

两个模型分工不同：`ApprovedSource` 属于应用配置，保存本地的相对路径；
`SourceProvenance` 属于结果和最小记录，不暴露路径。读取流程按固定顺序执行：

```text
模型提交 source_id
  → 应用在批准清单中查找 ApprovedSource
  → 解析并检查路径仍在 fixture 根目录
  → 有界读取 bytes，计算 sha256
  → 与批准 checksum 比较
  → 解码并返回最小文本 + SourceProvenance
```

版本号可以用公开 fixture 的修订号、发布日期或合成的版本标识；同一项目里选一种
含义并固定下来。checksum 必须算在工具实际读到的 bytes 上。资料发生变化时，先
更新批准清单和对应测试，不要在运行中接受模型报上来的新 checksum。清单里查不到
来源、revision 对不上、checksum 对不上——这三种情况都按失败处理，不能返回空
字符串或旧内容顶替。

### 4. 先检查路径边界，再打开文件

下面的普通函数展示最小的路径检查。它要求调用方提供相对路径，解析掉 `..` 和符号
链接，确认最终路径仍在允许根目录里，然后才打开文件。

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

不要用字符串 `startswith` 判断目录归属：`/fixtures-old` 同样以 `/fixtures` 开头，
却不是它的子目录。`Path.resolve()` 加 `relative_to()` 检查的是解析后路径的组成
部分，指向根目录外的符号链接也会在这一步被发现。

这个检查有一个前提：fixture 目录由应用管理，任务执行期间没有不受信任的进程会
改动它。如果其他进程可能同时替换文件或符号链接，就需要操作系统级的隔离，或基于
目录描述符的安全打开方式；这些超出本课程的本地 fixture 场景。

工具包装层要保持薄：从本地 context 取出允许根目录，其余逻辑都交给上面的普通
函数。

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

先看签名里的第一个参数。`RunContextWrapper[LessonContext]` 就是第 2 节说过的
context 注入入口：SDK 在调用工具时把它注入给本地函数；它不出现在模型可见的参数
schema 里，模型只填写其余参数（这里只有 `relative_path`）。所以工具函数的参数有
两个来源：ctx 走"应用 → SDK → 函数"这条本地通道，`relative_path` 走"模型 →
SDK 校验 → 函数"这条通道。

这里显式传入 `failure_error_function=None`。文件不存在或路径越界时，异常会原样
抛出，不会被改写成一段看起来像正常数据的工具结果。

最后是示例里悬着的 `catalog: "PublicCatalog"`：这个字段的类型 `PublicCatalog`
在下一节定义；本节的路径检查不依赖它。

### 5. 异步工具要有超时，错误要继续往上抛

外部查询即使只读，也可能一直不返回。`v0.20.0` 允许给异步函数工具设置单次
`timeout`。本课程选择 `timeout_behavior="raise_exception"`：超时抛出
`ToolTimeoutError` 并结束运行，M03 的应用包装层再把它转换成稳定的 `WorkerResult`。

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

这段代码只展示连接方式；`LessonContext.catalog` 和模拟客户端留到实战补齐。

一个容易踩的命名坑：装饰器的关键字参数叫 `timeout`，生成的工具对象上对应的属性
却叫 `timeout_seconds`——第 8 节的工具包装检查查的就是这个属性（例如
`query_public_catalog.timeout_seconds == 2.0`）。

`function_tool` 的默认异常策略会把工具异常改写成模型可见的错误消息，让模型有机会
重试或换一个工具；默认超时策略 `error_as_result` 也类似，把超时变成一条明确的
超时消息交给模型。这些策略适合允许模型自行恢复的流程。本课程的应用用例需要稳定
地判断失败，所以让两类异常都继续向上抛。无论选择哪种策略，都不要捕获异常后返回
空字符串、空列表或"没有结果"——那等于把失败伪装成正常数据。

!!! note "超时只适用于异步函数工具"

    `v0.20.0` 只支持给 `async def` 的 function tool handler 设置超时。需要超时的
    服务查询要写成异步函数。

### 6. 工具返回值会进入下一轮模型输入

一次工具调用按以下顺序发生：

```text
模型生成工具名和 JSON 参数
  → SDK 按 params_json_schema 检查参数
  → 本地 Python 函数读取 context 并执行
  → SDK 创建 function_call_output
  → 工具输出进入下一轮模型输入
  → 模型根据资料继续调用工具或生成最终结果
```

工具返回值因此属于模型上下文：下一轮模型调用能看到它的全部内容。所以返回值也要
最小化——只返回完成任务需要的文本；调用方需要来源时，附上稳定的来源标识。不要
返回 logger、客户端、凭据、允许根目录、完整异常堆栈或无关的服务字段。

普通字符串直接成为工具输出；其他普通对象通常会先转成字符串。需要稳定的 JSON
时，由应用显式序列化，不要依赖对象的 `str()`。还要记住：工具 schema 只约束输入
参数；返回值是否正确、是否安全，schema 一概不保证。

### 7. 只读 CLI adapter：程序和语法都写死

"让模型执行一条命令"不是本课程要做的工具。这里只暴露一个公开合成 CLI 的两个
只读动作，例如查询虚构设备的 `status` 或 `history`。可执行程序路径来自本地
context，子命令写在代码的 `Literal`/allowlist 里，设备标识经过长度和字符校验。
模型不能提供命令字符串、可执行程序、工作目录或环境变量。

```python
import asyncio
from typing import Literal


ReadonlySubcommand = Literal["status", "history"]
STDOUT_LIMIT = 32 * 1024
STDERR_LIMIT = 4 * 1024


async def run_readonly_cli(
    executable: str,
    subcommand: ReadonlySubcommand,
    device_id: str,
) -> str:
    argv = [executable, subcommand, "--device-id", device_id]
    process = await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={"LANG": "C.UTF-8", "LC_ALL": "C.UTF-8"},
    )
    stdout, stderr = await communicate_bounded(
        process,
        timeout_seconds=2.0,
        stdout_limit=STDOUT_LIMIT,
        stderr_limit=STDERR_LIMIT,
    )
    if process.returncode != 0:
        raise ReadonlyCliError("READ_ONLY_CLI_FAILED")
    return parse_allowed_fields(stdout)
```

片段故意省略了 `communicate_bounded`、`ReadonlyCliError` 和 `parse_allowed_fields`
的实现。实战里要求最高的部分是有界读取：

- 用两个并发 reader 按固定 chunk 排空 stdout 和 stderr；
- 任何一路超过上限，立即终止子进程并等待回收；
- EOF、退出码和大小三项检查都完成后才返回。

不能先调用无界的 `communicate()` 把全部输出读进内存再检查大小——内存边界在读的
那一刻就已经破了。

其余边界逐项说明：

- 用 `create_subprocess_exec` 的参数列表形式，不使用 shell，也没有 `shell=True`；
- 可执行程序和只读子命令固定；`;`、管道、重定向和额外选项都会被拒绝；
- 子进程环境从空白 allowlist 构造，不复制 `os.environ`，父进程里的凭据因此不会
  传进去；
- 超时后先 kill/terminate，再 `await process.wait()`，不留孤儿进程；
- stderr 只在本地用于错误分类，不连同异常文本交给模型；
- stdout 先做大小和 UTF-8/JSON 校验，再只返回允许的字段，不返回无限制的原始
  输出。

这不是 sandbox。它只让一个已知的合成程序执行两个已知的只读查询。如果真实需求是
执行任意命令或不受信任的程序，本课程方案不适用。

### 8. 先直接测试普通函数，再检查工具包装

工具逻辑的测试不需要模型参与。把文件读取和服务查询写成接收普通依赖的函数，测试
就能直接传入临时目录或假的客户端：

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

这些片段故意没有给出 `FailingCatalog`、成功场景和工具包装检查的完整实现，需要你
在实战中补齐。工具包装另做一组小检查：确认名称、schema 约束、`timeout_seconds`、
`timeout_behavior` 和最终 allowlist。CLI 测试另用测试脚本制造超时、超量输出、非零
退出和带凭据的父环境。这样即使没有 API key，也能验证权限边界和错误行为。

## 习题

先完成问题，再展开参考答案。

### 概念与代码阅读

1. `function_tool` 从哪些 Python 信息生成工具名、说明和参数 schema？
2. 为什么 `RunContextWrapper[LessonContext]` 不会成为模型可填写的工具参数？
3. 判断正误：instructions 写了"只读"以后，`Agent.tools` 中可以保留写工具。
4. `Field(pattern=...)` 为什么不能代替文件路径的根目录检查？
5. 为什么字符串 `startswith` 不能可靠判断路径是否位于允许目录？
6. 符号链接指向允许根目录外时，上面的代码在哪一步拒绝它？
7. 工具返回的文本随后会被谁看到？为什么返回值也要最小化？
8. `failure_error_function=None` 对工具 handler 抛出的异常有什么影响？
9. `timeout_behavior="raise_exception"` 与默认的 `error_as_result` 有什么区别？
10. 为什么直接测试 `read_text_from_root` 和 `fetch_public_entry` 比让模型调用工具
    更适合验证边界？
11. 为什么 `source_id`、`revision` 和 `sha256` 缺一项就难以复查实际使用的资料？
12. 为什么 CLI adapter 不能接收一个命令字符串，即使 instructions 写了"只读"？
13. 为什么先无界读取 stdout 再检查长度不算输出大小边界？
14. 为什么不能把完整 `os.environ` 传给合成 CLI？

<details class="exercise-answers">
<summary>参考答案</summary>

1. 默认用函数名作为工具名，用 docstring 第一段作为工具说明，用参数名和类型标注
   生成字段与类型，并从 docstring 参数段和 Pydantic `Field` 补充说明与约束。
2. SDK 识别第一个 `RunContextWrapper` 参数并在本地注入它；模型只填写其余 schema
   参数。
3. 错。真正的能力边界是代码注册的工具集合。写工具存在于 `Agent.tools` 中，就仍然
   可能被模型调用。
4. `Field` 检查字符串形状，不知道目录、`..` 或符号链接解析后的磁盘位置。函数仍要
   在打开文件前检查最终路径。
5. 两个不同目录名可以拥有相同的字符串前缀，例如 `/fixtures` 和 `/fixtures-old`。
6. `resolve()` 先得到符号链接的目标路径，随后 `candidate.relative_to(allowed_root)`
   因目标不在根目录中而抛出 `ValueError`。
7. SDK 把工具输出放入 `function_call_output`，下一轮模型调用会看到它。因此返回值
   也不能包含凭据、本地路径或无关私有数据。
8. SDK 不会把 handler 异常转换成默认的模型可见错误字符串，而是继续抛出异常。
9. 前者抛出 `ToolTimeoutError` 并让运行失败；后者把明确的超时消息作为工具结果
   交给模型，让模型决定是否恢复。
10. 普通函数测试没有模型随机性、网络费用或 API key 依赖，可以精确构造成功、越界
    和底层失败，并直接断言结果或异常；还可以单独检查工具包装的超时配置。
11. `source_id` 说明逻辑身份，`revision` 说明版本，`sha256` 证明实际 bytes。缺少
    任一项都可能把同名但不同内容的资料混为一谈。
12. 命令字符串会重新引入 shell 语法和任意参数组合。代码应固定可执行程序与子命令，
    并把每个参数作为独立 argv 元素传入。
13. 无界读取已经允许子进程消耗任意内存。正确做法是在读取 pipe 的过程中累计
    bytes，超过限制立即终止并回收子进程。
14. 父环境可能包含 API key、代理凭据或其他秘密。合成 CLI 只得到运行所需的最小
    固定环境。

</details>

### 实战：实现三类有边界的只读工具

在上一章的数据模型和本地 context 基础上完成以下任务。你可以新建
`src/evidence_worker/tools.py` 和 `tests/test_tools.py`，但不要复制本章片段作为
完整答案。

1. 在 `fixtures/` 下准备公开练习文本，并为每份资料建立批准清单；每条记录包含
   `source_id`、`revision` 和 `sha256`；
2. 实现一个按 `source_id` 查表的普通读取函数：检查路径在根目录内、校验 checksum，
   再用 `function_tool` 做一层薄包装；
3. 明确拒绝五种输入：绝对路径、`..` 越界、指向根目录外的符号链接、非 `.txt`
   文件、不存在的文件；
4. 实现一个只支持查询的模拟服务客户端，并把它加进 M01 的本地 context；
5. 实现一个接收模拟客户端和资料标识的普通异步查询函数，再做薄工具包装；
6. 给异步工具设置 2 秒单次超时，并让 handler 异常和超时继续往外抛；
7. 给两个模型可填的参数加上必要的长度或格式约束；
8. 实现一个模拟只读 CLI adapter：固定可执行程序，只允许 `status` / `history`
   两个子命令，用 `create_subprocess_exec`，限制参数和环境，2 秒超时，stdout
   上限 32 KiB，stderr 上限 4 KiB；
9. 只把资料读取、服务查询和 CLI 查询这三类入口注册给 Agent，确认没有任何外部
   写操作；
10. 不调用模型，直接测试以下 6 项：文本读取成功、路径边界、checksum 不匹配、
    查询成功、底层查询失败、provenance 往返；路径边界检查要覆盖绝对路径、`..`、
    越界符号链接、非 `.txt` 文件和不存在的文件；
11. CLI 测试覆盖：允许的命令、非法参数、超时、stdout/stderr 超限、非零退出，
    并证明父环境里的假凭据没有进入子进程；
12. 按第 8 节的做法，直接检查生成的工具名称、参数 schema、`timeout_seconds=2.0`、
    `timeout_behavior="raise_exception"` 和最终 allowlist。

先运行工具测试，再运行完整仓库检查：

```bash
uv run pytest tests/test_tools.py -q
uv run ruff check .
uv run pyright
uv run pytest
```

完成标准：

- Agent 的工具集合里只有三类窄的只读入口；
- 提供给工具的任何路径都逃不出允许的 fixture 根目录；
- 实际读取的资料都记录了 `source_id`、`revision` 和 `sha256`；
- 参数不合法、文件缺失、checksum 不符、底层异常、超时、输出超限——都不会变成
  正常数据；
- CLI 不使用 shell，不继承凭据，不接受任意程序、子命令或选项；
- 所有直接检查都不调用模型，也不需要 API key；
- 能说清每个工具返回给模型的字段或文本是什么；
- 仓库检查全部通过。

本章没有给出实战的完整实现。核心内容分别展示了 schema、路径检查、超时和直接测试
的最小片段；你需要自己定义模拟客户端、组合 context、完成两个工具并补齐全部测试。

## 版本与官方参考

本章最后核对日期：2026-08-11。项目锁定版本：`openai-agents==0.20.0`。

- [当前 Agents SDK 指南：工具定位](https://developers.openai.com/api/docs/guides/tools#usage-in-the-agents-sdk)
- [`v0.20.0` Tools：function tools](https://github.com/openai/openai-agents-python/blob/v0.20.0/docs/tools.md#function-tools)
- [`v0.20.0` function schema 源码](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/function_schema.py)
- [`v0.20.0` function tool 与超时源码](https://github.com/openai/openai-agents-python/blob/v0.20.0/src/agents/tool.py)
- [`v0.20.0` 基础工具示例](https://github.com/openai/openai-agents-python/blob/v0.20.0/examples/basic/tools.py)
- [Python `pathlib`：解析路径与 `relative_to`](https://docs.python.org/3.12/library/pathlib.html)
- [Python `asyncio` subprocess](https://docs.python.org/3.12/library/asyncio-subprocess.html)

示例改动：把官方天气工具改成受限文本读取、只读目录服务查询和固定语法的合成 CLI；
加入来源 provenance、本地 context、Pydantic 参数约束、解析后路径检查、显式异常
传播、2 秒单次超时与输出大小限制；把 handler 拆成可直接测试的普通函数；省略完整
Agent 运行、hosted tools、MCP、handoff、approval、sandbox 和实战完整答案。
