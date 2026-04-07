"""API tests for the FastAPI surface."""

from __future__ import annotations

import httpx
from fastapi.testclient import TestClient

from src.api.main import create_app
from src.core.config import Settings, get_settings
from src.models import StrategyReviewRequest
from src.services.copilot_service import CopilotService, get_copilot_service


def build_client() -> TestClient:
    """Create an app with the service dependency overridden to mock mode."""

    app = create_app()
    app.dependency_overrides[get_copilot_service] = lambda: CopilotService(
        settings=Settings(llm_provider="mock", enable_file_logging=False)
    )
    return TestClient(app)


def build_client_with_service(service: object) -> TestClient:
    """Create an app with a custom service dependency for failure-path tests."""

    app = create_app()
    app.dependency_overrides[get_copilot_service] = lambda: service
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


def test_generate_route_maps_provider_failures_to_503() -> None:
    class UnavailableService:
        async def generate_strategy(self, payload, request_id=None):  # type: ignore[no-untyped-def]
            raise httpx.ConnectError("could not connect")

    client = build_client_with_service(UnavailableService())
    response = client.post(
        "/api/v1/strategies/generate",
        json={"concept": "A product assistant for consultants that turns notes into project plans."},
    )

    assert response.status_code == 503
    assert response.json()["detail"] == "Strategy generation is temporarily unavailable."


def test_review_route_hides_internal_exception_details() -> None:
    class ExplodingService:
        async def review_strategy(self, payload, request_id=None):  # type: ignore[no-untyped-def]
            raise RuntimeError("super secret stack detail")

    client = build_client_with_service(ExplodingService())
    response = client.post(
        "/api/v1/strategies/review",
        json={
            "original_input": {
                "concept": "A product assistant for consultants that turns notes into project plans.",
            },
            "edited_output": {
                "product_brief": {
                    "product_name": "PlanForge",
                    "category": "Workflow SaaS",
                    "target_user": "Independent consultants",
                    "core_problem": "Project follow-up planning is inconsistent after client meetings.",
                    "solution_summary": "The product turns raw notes into a prioritized project plan.",
                    "primary_platform": "Web app",
                    "monetization_model": "Subscription",
                    "differentiator": "It focuses on post-meeting execution clarity.",
                },
                "user_journey_loops": [],
                "monetization_risk_notes": [],
                "task_list": [],
                "follow_up_questions": [],
            },
        },
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "Strategy review failed."
    assert "super secret stack detail" not in response.text


def test_wildcard_cors_disables_credentials(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "*")

    client = TestClient(create_app())
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert "access-control-allow-credentials" not in response.headers
    get_settings.cache_clear()


def test_explicit_cors_origin_allows_credentials(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("CORS_ALLOW_ORIGINS", "https://example.com")

    client = TestClient(create_app())
    response = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://example.com"
    assert response.headers["access-control-allow-credentials"] == "true"
    get_settings.cache_clear()
