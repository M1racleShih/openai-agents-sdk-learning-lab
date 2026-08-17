# 学习记录

[English](LEARNING_LOG-en.md)

本日志只保留每个模块的状态和验证证据，不记录逐分钟过程。

## 模块状态

| 模块 | 状态 | 完成时间 | 验证证据 |
| --- | --- | --- | --- |
| M00：首个可观察 Agent | in_progress | — | — |
| M01：结构化结果与上下文 | passed | 2026-08-17 | 仓库检查通过；小米 MiMo 端点结构化运行输出 `WorkerResult` JSON；MiniMax 失败已按预期记录 |
| M02：只读工具与来源边界 | pending | — | — |
| M03：有界运行与失败语义 | pending | — | — |
| M04：Trace、最小元数据与确定性测试 | pending | — | — |
| M05：Sessions、streaming 与取消 | pending | — | — |
| M06：UI 无关用例与类型化事件 | pending | — | — |
| M07：薄终端适配器 | pending | — | — |
| M08：公开 capstone 与就绪评审 | pending | — | — |

状态只使用 `pending`、`ready`、`in_progress` 和 `passed`。

## 模块记录模板

每个模块通过后追加一节：

```text
## Mxx

- 完成时间：
- 验证证据：
- 纠正的一个误解：
- 一个未决问题：
```

不要在这里粘贴 API key、完整 prompt、原始模型响应或私有数据。

## M01

- 完成时间：2026-08-17
- 验证证据：
  - `uv run ruff check .` 通过；`uv run pyright` 0 错误；`uv run pytest` 13 项通过；
  - `contracts.py` 四个模型经运行时核验：字段全部必填，`WorkerResult` schema 的
    `required` 覆盖全部四个字段，`TaskRequest` 拒绝缺字段输入；
  - `uv run python -m evidence_worker.structured_agent` 在小米 MiMo 端点
    （`mimo-v2.5`，chat completions + json_schema）连续两次输出单个 `WorkerResult`
    JSON 对象，`evidence` 与 `errors` 均为空列表，`task_id` 正确回显；
  - MiniMax-M3（`.env` 原 `OPENAI_COMPATIBLE_API=responses`）运行同一代码失败：
    `ModelBehaviorError: Invalid JSON when parsing model output`，模型返回自由文本/
    markdown 包裹的 JSON。直连探测同样确认其 chat completions 端点静默忽略
    `response_format=json_schema`。按 M01 课程 tip，这属于"结构化输出不被支持时本章
    运行会失败"的预期行为，不回退自由文本。
- 纠正的一个误解：曾以为 `output_type=WorkerResult` 在任何 OpenAI 兼容端点都会强制
  JSON 输出；实测结构化输出依赖供应商实现，端点可能接受参数而不执行。
- 一个未决问题：MiniMax-M3 的结构化输出兼容性留待 M05 兼容性 spike 复核。

### M01 上下文边界清单

模型可见（进入模型上下文）：

- `build_instructions` 返回的 instructions 字符串（角色说明、不编造证据、空列表要求）；
- `Runner.run` 的 `model_input`：仅由 `TaskRequest` 的 `task_id`、`question`、
  `requested_source_ids` 三个字段拼成；
- `WorkerResult` 的输出 JSON schema（SDK 由 `output_type` 生成并随请求发送）。

仅本地（模型不可见）：

- `WorkerContext.logger`（logging.Logger 对象）；
- `WorkerContext.allowed_source_root`（fixtures 目录绝对路径）；
- `load_learning_model()` 构造的 AsyncOpenAI 客户端、API key 与环境变量。

依据：SDK 只把 instructions、input 和工具结果放进模型上下文；context 仅经
`RunContextWrapper` 供本地 Python 代码读取。本模块没有任何代码把本地对象写进
instructions、模型输入或工具结果。
