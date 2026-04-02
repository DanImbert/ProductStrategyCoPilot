"""Service-layer tests using the mock adapter."""

from __future__ import annotations

import asyncio

from src.core.config import Settings
from src.models import ProductIdeaInput, StrategyReviewRequest
from src.services.copilot_service import CopilotService


def build_service() -> CopilotService:
    """Create a deterministic service instance for tests."""

    settings = Settings(
        llm_provider="mock",
        enable_file_logging=False,
    )
    return CopilotService(settings=settings)


def test_generate_strategy_returns_agent_runs_and_editable_json() -> None:
    service = build_service()
    payload = ProductIdeaInput(
        concept="An AI assistant for boutique agencies that turns messy meeting notes into client-ready next steps and internal task plans.",
        additional_context="Target a small SaaS MVP and optimize for time-to-value.",
    )

    response = asyncio.run(service.generate_strategy(payload, request_id="test-request"))

    assert response.request_id == "test-request"
    assert response.strategy_output.product_brief.product_name
    assert len(response.agent_runs) == 2
    assert response.editable_json["product_brief"]["product_name"] == response.strategy_output.product_brief.product_name
    assert response.evaluation.quality_score > 0


def test_review_strategy_only_runs_critic() -> None:
    service = build_service()
    original_input = ProductIdeaInput(
        concept="A compliance assistant for small clinics that turns policy updates into staff action plans and documentation checklists.",
    )
    generated = asyncio.run(service.generate_strategy(original_input, request_id="seed"))
    edited_output = generated.strategy_output.model_copy(
        update={
            "follow_up_questions": generated.strategy_output.follow_up_questions[:2],
        }
    )

    response = asyncio.run(
        service.review_strategy(
            StrategyReviewRequest(original_input=original_input, edited_output=edited_output),
            request_id="review-request",
        )
    )

    assert response.request_id == "review-request"
    assert len(response.agent_runs) == 1
    assert response.critic_review.completeness_score <= 1.0
