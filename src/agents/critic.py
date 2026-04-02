"""Critic agent implementation."""

from __future__ import annotations

import logging
from time import perf_counter

from .base import Agent, AgentRunResult
from ..core.llm_client import BaseLLMAdapter
from ..core.prompt_registry import CRITIC_PROMPT, render_strategy_output_for_prompt
from ..models import AgentRunMetrics, CriticReview, ProductIdeaInput, ProductStrategyDocument

logger = logging.getLogger(__name__)


class CriticAgent(Agent[CriticReview]):
    """Reviews the planner draft for clarity, gaps, and contradictions."""

    name = "critic"
    version = "1.0.0"

    def __init__(self, llm_adapter: BaseLLMAdapter):
        self.llm_adapter = llm_adapter
        self.prompt = CRITIC_PROMPT

    async def run(
        self,
        source_input: ProductIdeaInput,
        strategy_output: ProductStrategyDocument,
        request_id: str,
    ) -> AgentRunResult[CriticReview]:
        """Review a strategy document against the original product idea."""

        started = perf_counter()
        messages = self.prompt.render(
            concept=source_input.concept,
            strategy_output=render_strategy_output_for_prompt(strategy_output.model_dump(mode="json")),
        )
        llm_result = await self.llm_adapter.generate_json(
            prompt_name=self.prompt.name,
            messages=messages,
            temperature=self.prompt.temperature,
            max_tokens=self.prompt.max_tokens,
            metadata={
                "concept": source_input.concept,
                "strategy_output": strategy_output.model_dump(mode="json"),
            },
        )

        review = CriticReview.model_validate(llm_result.payload)
        latency_ms = round((perf_counter() - started) * 1000)
        execution = AgentRunMetrics(
            agent_name=self.name,
            agent_version=self.version,
            prompt_name=self.prompt.name,
            prompt_version=self.prompt.version,
            model_provider=llm_result.model_provider,
            model_name=llm_result.model_name,
            latency_ms=latency_ms,
            prompt_tokens=llm_result.usage.prompt_tokens,
            completion_tokens=llm_result.usage.completion_tokens,
            total_tokens=llm_result.usage.total_tokens,
            estimated_cost_usd=llm_result.usage.estimated_cost_usd,
            retries=llm_result.retries,
        )

        logger.info(
            "critic_completed",
            extra={
                "event": {
                    "request_id": request_id,
                    "agent": self.name,
                    "latency_ms": latency_ms,
                    "model": llm_result.model_name,
                    "retries": llm_result.retries,
                }
            },
        )

        return AgentRunResult(output=review, execution=execution)
