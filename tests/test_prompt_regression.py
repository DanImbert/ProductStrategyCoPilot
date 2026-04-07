"""Tests for prompt regression utilities."""

from __future__ import annotations

import asyncio

from scripts.prompt_regression import evaluate_case, load_cases, run_regression_suite
from src.core.config import Settings
from src.models import ProductIdeaInput
from src.services.copilot_service import CopilotService


def test_regression_suite_passes_in_mock_mode() -> None:
    settings = Settings(llm_provider="mock", enable_file_logging=False)

    results = asyncio.run(run_regression_suite(settings=settings))

    assert results
    assert all(result.passed for result in results)


def test_evaluate_case_reports_missing_required_risk_categories() -> None:
    settings = Settings(llm_provider="mock", enable_file_logging=False)
    service = CopilotService(settings=settings)
    case = load_cases()[0]
    response = asyncio.run(
        service.generate_strategy(
            payload=ProductIdeaInput(
                concept=case.concept,
                additional_context=case.additional_context,
            ),
            request_id="regression-risk-check",
        )
    )
    downgraded = response.model_copy(
        update={
            "strategy_output": response.strategy_output.model_copy(
                update={"monetization_risk_notes": response.strategy_output.monetization_risk_notes[:1]}
            )
        }
    )

    result = evaluate_case(case, downgraded)

    assert not result.passed
    assert any("missing required risk categories" in failure for failure in result.failures)
