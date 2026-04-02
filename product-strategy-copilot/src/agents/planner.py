"""Planner agent implementation."""

from __future__ import annotations

import logging
from time import perf_counter

from .base import Agent, AgentRunResult
from ..core.llm_client import BaseLLMAdapter
from ..core.prompt_registry import PLANNER_PROMPT
from ..models import AgentRunMetrics, Priority, ProductIdeaInput, ProductStrategyDocument

logger = logging.getLogger(__name__)

PRIORITY_ORDER = {
    Priority.HIGH: 0,
    Priority.MEDIUM: 1,
    Priority.LOW: 2,
}


class PlannerAgent(Agent[ProductStrategyDocument]):
    """Turns a product idea into a structured strategy artifact."""

    name = "planner"
    version = "1.0.0"

    def __init__(self, llm_adapter: BaseLLMAdapter):
        self.llm_adapter = llm_adapter
        self.prompt = PLANNER_PROMPT

    async def run(self, request: ProductIdeaInput, request_id: str) -> AgentRunResult[ProductStrategyDocument]:
        """Generate a strategy document from plain-English input."""

        started = perf_counter()
        messages = self.prompt.render(
            concept=request.concept,
            additional_context=request.additional_context or "None provided.",
        )
        llm_result = await self.llm_adapter.generate_json(
            prompt_name=self.prompt.name,
            messages=messages,
            temperature=self.prompt.temperature,
            max_tokens=self.prompt.max_tokens,
            metadata={
                "concept": request.concept,
                "additional_context": request.additional_context,
            },
        )

        document = ProductStrategyDocument.model_validate(llm_result.payload)
        document = self._normalize_document(document)
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
            "planner_completed",
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

        return AgentRunResult(output=document, execution=execution)

    def _normalize_document(self, document: ProductStrategyDocument) -> ProductStrategyDocument:
        """Sort tasks into a predictable priority order and strip invalid dependencies."""

        valid_ids = {task.id for task in document.task_list}
        normalized_tasks = []
        for task in document.task_list:
            dependencies = [dependency for dependency in task.dependencies if dependency in valid_ids and dependency != task.id]
            normalized_tasks.append(task.model_copy(update={"dependencies": sorted(set(dependencies))}))

        normalized_tasks.sort(key=lambda task: (PRIORITY_ORDER[task.priority], task.id))

        return document.model_copy(update={"task_list": normalized_tasks})
