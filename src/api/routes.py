"""API routes for strategy generation and review."""

from __future__ import annotations

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

from ..core.config import Settings, get_settings
from ..core.prompt_registry import prompt_versions
from ..models import ProductIdeaInput, StrategyResponse, StrategyReviewRequest, StrategyReviewResponse
from ..services.copilot_service import CopilotService, get_copilot_service

router = APIRouter(prefix="/api/v1", tags=["copilot"])
logger = logging.getLogger(__name__)


def _service_unavailable(detail: str, *, request_id: str | None, exc: Exception) -> HTTPException:
    """Log provider or configuration issues without leaking internals to clients."""

    logger.warning(
        "request_unavailable",
        extra={
            "event": {
                "request_id": request_id,
                "error_type": type(exc).__name__,
                "detail": detail,
            }
        },
        exc_info=exc,
    )
    return HTTPException(status_code=503, detail=detail)


def _internal_error(detail: str, *, request_id: str | None, exc: Exception) -> HTTPException:
    """Log unexpected failures and return a generic client-safe error."""

    logger.exception(
        "request_failed",
        extra={
            "event": {
                "request_id": request_id,
                "error_type": type(exc).__name__,
                "detail": detail,
            }
        },
    )
    return HTTPException(status_code=500, detail=detail)


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

    request_id = getattr(request.state, "request_id", None)
    try:
        return await service.generate_strategy(payload, request_id=request_id)
    except (ValueError, httpx.HTTPError) as exc:
        raise _service_unavailable(
            "Strategy generation is temporarily unavailable.",
            request_id=request_id,
            exc=exc,
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise _internal_error(
            "Strategy generation failed.",
            request_id=request_id,
            exc=exc,
        ) from exc


@router.post("/strategies/review", response_model=StrategyReviewResponse)
async def review_strategy(
    payload: StrategyReviewRequest,
    request: Request,
    service: CopilotService = Depends(get_copilot_service),
) -> StrategyReviewResponse:
    """Review a user-edited strategy document."""

    request_id = getattr(request.state, "request_id", None)
    try:
        return await service.review_strategy(payload, request_id=request_id)
    except (ValueError, httpx.HTTPError) as exc:
        raise _service_unavailable(
            "Strategy review is temporarily unavailable.",
            request_id=request_id,
            exc=exc,
        ) from exc
    except Exception as exc:  # pragma: no cover - defensive API boundary
        raise _internal_error(
            "Strategy review failed.",
            request_id=request_id,
            exc=exc,
        ) from exc
