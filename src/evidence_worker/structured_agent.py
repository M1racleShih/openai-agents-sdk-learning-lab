"""M01 practical: single Agent run with structured output and local context."""

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path

from agents import Agent, RunContextWrapper, Runner

from evidence_worker.contracts import TaskRequest, WorkerResult
from evidence_worker.model_provider import load_learning_model


@dataclass
class WorkerContext:
    logger: logging.Logger
    allowed_source_root: Path


def build_instructions(
    wrapper: RunContextWrapper[WorkerContext],
    agent: Agent[WorkerContext],
) -> str:
    wrapper.context.logger.info("building instructions for agent=%s", agent.name)
    return (
        "You are an evidence worker. "
        "Answer the question based on your general knowledge. "
        "Do NOT fabricate evidence or source references. "
        "Return an empty list for `evidence` and `errors`."
    )


async def main() -> None:
    local_context = WorkerContext(
        logger=logging.getLogger("evidence_worker"),
        allowed_source_root=Path("fixtures").resolve(),
    )

    agent = Agent[WorkerContext](
        name="Evidence worker",
        instructions=build_instructions,
        model=load_learning_model(),
        output_type=WorkerResult,
    )

    # Validate caller input with TaskRequest
    request = TaskRequest(
        task_id="ex-001",
        question="What is a Python context manager?",
        requested_source_ids=["src-1", "src-2"],
    )

    # Only expose task_id, question, and source IDs to the model
    model_input = (
        f"Task ID: {request.task_id}\n"
        f"Question: {request.question}\n"
        f"Source IDs: {', '.join(request.requested_source_ids)}"
    )

    result = await Runner.run(agent, model_input, context=local_context)
    output = result.final_output_as(WorkerResult, raise_if_incorrect_type=True)
    print(output.model_dump_json())


if __name__ == "__main__":
    asyncio.run(main())
