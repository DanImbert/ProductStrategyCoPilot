"""Agent-level tests focused on prompt/version wiring."""

from __future__ import annotations

import asyncio

from src.agents.critic import CriticAgent
from src.agents.planner import PlannerAgent
from src.core.config import Settings
from src.core.llm_client import get_llm_adapter
from src.models import ProductIdeaInput


def test_planner_and_critic_expose_versioned_prompt_metadata() -> None:
    settings = Settings(llm_provider="mock", enable_file_logging=False)
    adapter = get_llm_adapter(settings)
    planner = PlannerAgent(adapter)
    critic = CriticAgent(adapter)

    strategy = asyncio.run(
        planner.run(
            ProductIdeaInput(
                concept="A lightweight analytics assistant for e-commerce operators that explains revenue dips in plain English.",
            ),
            request_id="planner-test",
        )
    )
    review = asyncio.run(
        critic.run(
            ProductIdeaInput(
                concept="A lightweight analytics assistant for e-commerce operators that explains revenue dips in plain English.",
            ),
            strategy.output,
            request_id="critic-test",
        )
    )

    assert strategy.execution.prompt_name == "planner_strategy"
    assert review.execution.prompt_name == "critic_strategy_review"
    assert strategy.execution.prompt_version
    assert review.execution.prompt_version
