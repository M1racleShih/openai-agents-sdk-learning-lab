import asyncio

from agents import Agent, Runner

from evidence_worker.local_tracing import configure_local_tracing
from evidence_worker.model_provider import load_learning_model


async def main() -> None:
    configure_local_tracing()

    explain_python_agent = Agent(
        name="Python explainer",
        instructions="Explain one Python concept in plain language.",
        model=load_learning_model(),
    )

    result = await Runner.run(explain_python_agent, "Python 的 context manager 解决了什么问题？")

    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
