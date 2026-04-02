"""FastAPI app factory."""

from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from ..core.config import get_settings
from ..logging_config import configure_logging
from .routes import router


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""

    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Product Strategy Copilot: a small multi-agent FastAPI service that converts plain-English "
            "product ideas into structured strategy briefs, critiques them, and reports quality/cost metrics."
        ),
    )

    origins = [origin.strip() for origin in settings.cors_allow_origins.split(",")] if settings.cors_allow_origins else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def attach_request_id(request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    @app.get("/", tags=["meta"])
    async def root() -> dict[str, str]:
        return {
            "service": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
        }

    app.include_router(router)
    return app


app = create_app()
