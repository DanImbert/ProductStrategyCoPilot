"""Typed request, response, and domain models for the Product Strategy Copilot."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Priority(str, Enum):
    """Priority labels used across risk notes and task lists."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RiskCategory(str, Enum):
    """Supported note categories surfaced to users."""

    MONETIZATION = "monetization"
    RETENTION = "retention"
    DELIVERY = "delivery"
    SAFETY = "safety"
    COMPLIANCE = "compliance"
    GO_TO_MARKET = "go_to_market"


class QuestionCategory(str, Enum):
    """Question categories used for follow-up clarification."""

    USER = "user"
    WORKFLOW = "workflow"
    PRICING = "pricing"
    SCOPE = "scope"
    DATA = "data"
    DISTRIBUTION = "distribution"


class ProductIdeaInput(BaseModel):
    """User-provided product or startup idea."""

    model_config = ConfigDict(str_strip_whitespace=True)

    concept: str = Field(
        ...,
        min_length=10,
        max_length=1500,
        description="Plain-English description of the product idea.",
    )
    additional_context: str | None = Field(
        default=None,
        max_length=800,
        description="Optional constraints such as customer segment, business model, or team size.",
    )


class ProductBrief(BaseModel):
    """Structured intent extracted by the planner agent."""

    model_config = ConfigDict(str_strip_whitespace=True)

    product_name: str
    category: str
    target_user: str
    core_problem: str
    solution_summary: str
    primary_platform: str
    monetization_model: str
    differentiator: str


class UserJourneyLoop(BaseModel):
    """A repeatable user journey or engagement loop."""

    model_config = ConfigDict(str_strip_whitespace=True)

    name: str
    objective: str
    user_steps: list[str] = Field(default_factory=list)
    success_signal: str
    time_to_value: str


class BusinessRiskNote(BaseModel):
    """Business, safety, or go-to-market note."""

    model_config = ConfigDict(str_strip_whitespace=True)

    category: RiskCategory
    priority: Priority
    title: str
    note: str
    mitigation: str


class BuildTaskItem(BaseModel):
    """Prioritized implementation task."""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: int = Field(..., ge=1)
    title: str
    priority: Priority
    rationale: str
    estimated_hours: float = Field(..., ge=0.5, le=500)
    dependencies: list[int] = Field(default_factory=list)

    @field_validator("dependencies")
    @classmethod
    def normalize_dependencies(cls, value: list[int]) -> list[int]:
        """Deduplicate and sort dependency IDs for stable output."""

        return sorted({dependency for dependency in value if dependency > 0})


class FollowUpQuestion(BaseModel):
    """Question to clarify uncertain strategy choices."""

    model_config = ConfigDict(str_strip_whitespace=True)

    question: str
    category: QuestionCategory
    reason: str


class ProductStrategyDocument(BaseModel):
    """Full strategy artifact returned to the user."""

    product_brief: ProductBrief
    user_journey_loops: list[UserJourneyLoop] = Field(default_factory=list)
    monetization_risk_notes: list[BusinessRiskNote] = Field(default_factory=list)
    task_list: list[BuildTaskItem] = Field(default_factory=list)
    follow_up_questions: list[FollowUpQuestion] = Field(default_factory=list)


class CriticReview(BaseModel):
    """Structured review produced by the critic agent."""

    ready_for_delivery: bool
    completeness_score: float = Field(..., ge=0.0, le=1.0)
    clarity_score: float = Field(..., ge=0.0, le=1.0)
    consistency_score: float = Field(..., ge=0.0, le=1.0)
    safety_notes: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    recommended_revisions: list[str] = Field(default_factory=list)


class AgentRunMetrics(BaseModel):
    """Per-agent execution metadata for observability."""

    agent_name: str
    agent_version: str
    prompt_name: str
    prompt_version: str
    model_provider: str
    model_name: str
    latency_ms: int = Field(..., ge=0)
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)
    retries: int = Field(default=0, ge=0)


class EvaluationSummary(BaseModel):
    """Quality and performance summary for a response."""

    completeness_score: float = Field(..., ge=0.0, le=1.0)
    consistency_score: float = Field(..., ge=0.0, le=1.0)
    latency_ms: int = Field(..., ge=0)
    estimated_cost_usd: float = Field(..., ge=0.0)
    total_tokens: int = Field(..., ge=0)
    quality_score: float = Field(..., ge=0.0, le=1.0)


class StrategyResponse(BaseModel):
    """API response for a generated product strategy."""

    request_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    input: ProductIdeaInput
    strategy_output: ProductStrategyDocument
    critic_review: CriticReview
    evaluation: EvaluationSummary
    agent_runs: list[AgentRunMetrics]
    prompt_versions: dict[str, str]
    editable_json: dict[str, Any]


class StrategyReviewRequest(BaseModel):
    """Request body for re-reviewing edited JSON output."""

    original_input: ProductIdeaInput
    edited_output: ProductStrategyDocument


class StrategyReviewResponse(BaseModel):
    """API response when reviewing a user-edited document."""

    request_id: str
    reviewed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    critic_review: CriticReview
    evaluation: EvaluationSummary
    agent_runs: list[AgentRunMetrics]
    prompt_versions: dict[str, str]
    editable_json: dict[str, Any]


class BenchmarkResult(BaseModel):
    """Single benchmark run entry used for scripts and reporting."""

    case_id: str
    concept: str
    success: bool
    provider: str
    model_name: str
    measurement_mode: str
    latency_ms: int = Field(..., ge=0)
    completeness_score: float | None = Field(default=None, ge=0.0, le=1.0)
    consistency_score: float | None = Field(default=None, ge=0.0, le=1.0)
    quality_score: float | None = Field(default=None, ge=0.0, le=1.0)
    estimated_cost_usd: float = Field(default=0.0, ge=0.0)
    total_tokens: int = Field(default=0, ge=0)
    notes: str | None = None
