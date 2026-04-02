"""API tests for the FastAPI surface."""

from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.main import create_app
from src.core.config import Settings
from src.models import StrategyReviewRequest
from src.services.copilot_service import CopilotService, get_copilot_service


def build_client() -> TestClient:
    """Create an app with the service dependency overridden to mock mode."""

    app = create_app()
    app.dependency_overrides[get_copilot_service] = lambda: CopilotService(
        settings=Settings(llm_provider="mock", enable_file_logging=False)
    )
    return TestClient(app)


def test_health_route() -> None:
    client = build_client()
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_generate_route_returns_strategy_document() -> None:
    client = build_client()
    response = client.post(
        "/api/v1/strategies/generate",
        json={
            "concept": "A marketplace that helps homeowners compare vetted repair pros and convert quotes into booked jobs faster.",
            "additional_context": "Focus on one city for the MVP and keep trust/safety prominent.",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["strategy_output"]["product_brief"]["product_name"]
    assert len(body["agent_runs"]) == 2


def test_review_route_returns_critic_feedback() -> None:
    client = build_client()
    generate_response = client.post(
        "/api/v1/strategies/generate",
        json={
            "concept": "A workflow assistant for small clinics that turns policy updates into staff action plans and documentation checklists.",
            "additional_context": "Compliance-heavy domain with human review.",
        },
    )
    assert generate_response.status_code == 200
    generated = generate_response.json()

    review_payload = StrategyReviewRequest.model_validate(
        {
            "original_input": generated["input"],
            "edited_output": generated["strategy_output"],
        }
    ).model_dump(mode="json")
    review_response = client.post("/api/v1/strategies/review", json=review_payload)

    assert review_response.status_code == 200
    review_body = review_response.json()
    assert review_body["critic_review"]["completeness_score"] >= 0
    assert len(review_body["agent_runs"]) == 1
