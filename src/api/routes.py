"""API routes for strategy generation and review."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from ..core.config import Settings, get_settings
from ..core.prompt_registry import prompt_versions
from ..models import ProductIdeaInput, StrategyResponse, StrategyReviewRequest, StrategyReviewResponse
from ..services.copilot_service import CopilotService, get_copilot_service

router = APIRouter(prefix="/api/v1", tags=["copilot"])


@router.get("/health", tags=["meta"])
async def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    """Simple health endpoint used by deployment platforms."""

    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "provider": settings.llm_provider,
        "model": settings.active_model_name,
    }


@router.get("/prompts", tags=["meta"])
async def list_prompt_versions() -> dict[str, dict[str, str]]:
    """Expose prompt versions for debugging and benchmark reproducibility."""

    return {"prompts": prompt_versions()}


@router.post("/strategies/generate", response_model=StrategyResponse)
async def generate_strategy(
    payload: ProductIdeaInput,
    request: Request,
    service: CopilotService = Depends(get_copilot_service),
) -> StrategyResponse:
    """Generate a structured product strategy and critique it."""

    try:
        return await service.generate_strategy(payload, request_id=getattr(request.state, "request_id", None))
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}") from exc


@router.post("/strategies/review", response_model=StrategyReviewResponse)
async def review_strategy(
    payload: StrategyReviewRequest,
    request: Request,
    service: CopilotService = Depends(get_copilot_service),
) -> StrategyReviewResponse:
    """Review a user-edited strategy document."""

    try:
        return await service.review_strategy(payload, request_id=getattr(request.state, "request_id", None))
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise HTTPException(status_code=500, detail=f"Review failed: {exc}") from exc
