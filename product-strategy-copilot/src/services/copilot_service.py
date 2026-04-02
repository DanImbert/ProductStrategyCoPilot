"""Service layer orchestrating planner, critic, and evaluation."""

from __future__ import annotations

import logging
from functools import lru_cache
from time import perf_counter
from uuid import uuid4

from ..agents.critic import CriticAgent
from ..agents.planner import PlannerAgent
from ..core.config import Settings, get_settings
from ..core.llm_client import get_llm_adapter
from ..core.prompt_registry import prompt_versions
from ..evaluation.evaluator import ResponseEvaluator
from ..models import ProductIdeaInput, StrategyResponse, StrategyReviewRequest, StrategyReviewResponse

logger = logging.getLogger(__name__)


class CopilotService:
    """High-level application service for product strategy generation."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        llm_adapter = get_llm_adapter(self.settings)
        self.planner = PlannerAgent(llm_adapter=llm_adapter)
        self.critic = CriticAgent(llm_adapter=llm_adapter)
        self.evaluator = ResponseEvaluator()

    async def generate_strategy(self, payload: ProductIdeaInput, request_id: str | None = None) -> StrategyResponse:
        """Run planner then critic and attach evaluation metadata."""

        active_request_id = request_id or str(uuid4())
        started = perf_counter()

        planner_run = await self.planner.run(payload, request_id=active_request_id)
        critic_run = await self.critic.run(payload, planner_run.output, request_id=active_request_id)

        total_latency_ms = round((perf_counter() - started) * 1000)
        agent_runs = [planner_run.execution, critic_run.execution]
        evaluation = self.evaluator.evaluate(
            strategy_output=planner_run.output,
            critic_review=critic_run.output,
            agent_runs=agent_runs,
            latency_ms=total_latency_ms,
        )

        response = StrategyResponse(
            request_id=active_request_id,
            input=payload,
            strategy_output=planner_run.output,
            critic_review=critic_run.output,
            evaluation=evaluation,
            agent_runs=agent_runs,
            prompt_versions=prompt_versions(),
            editable_json=planner_run.output.model_dump(mode="json"),
        )

        logger.info(
            "generation_completed",
            extra={
                "event": {
                    "request_id": active_request_id,
                    "latency_ms": total_latency_ms,
                    "quality_score": evaluation.quality_score,
                    "estimated_cost_usd": evaluation.estimated_cost_usd,
                }
            },
        )

        return response

    async def review_strategy(self, payload: StrategyReviewRequest, request_id: str | None = None) -> StrategyReviewResponse:
        """Review a user-edited strategy document without re-running the planner."""

        active_request_id = request_id or str(uuid4())
        started = perf_counter()

        critic_run = await self.critic.run(
            source_input=payload.original_input,
            strategy_output=payload.edited_output,
            request_id=active_request_id,
        )
        total_latency_ms = round((perf_counter() - started) * 1000)
        agent_runs = [critic_run.execution]
        evaluation = self.evaluator.evaluate(
            strategy_output=payload.edited_output,
            critic_review=critic_run.output,
            agent_runs=agent_runs,
            latency_ms=total_latency_ms,
        )

        return StrategyReviewResponse(
            request_id=active_request_id,
            critic_review=critic_run.output,
            evaluation=evaluation,
            agent_runs=agent_runs,
            prompt_versions=prompt_versions(),
            editable_json=payload.edited_output.model_dump(mode="json"),
        )


@lru_cache
def get_copilot_service() -> CopilotService:
    """FastAPI dependency for the shared service instance."""

    return CopilotService(settings=get_settings())
