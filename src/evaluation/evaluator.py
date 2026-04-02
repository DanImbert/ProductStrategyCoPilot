"""Evaluation pipeline used by the API and benchmark script."""

from __future__ import annotations

from ..models import AgentRunMetrics, CriticReview, EvaluationSummary, ProductStrategyDocument
from .metrics import score_completeness, score_consistency, total_cost_from_agent_runs, total_tokens_from_agent_runs


class ResponseEvaluator:
    """Evaluate strategy quality, latency, and estimated cost."""

    def evaluate(
        self,
        *,
        strategy_output: ProductStrategyDocument,
        critic_review: CriticReview,
        agent_runs: list[AgentRunMetrics],
        latency_ms: int,
    ) -> EvaluationSummary:
        """Generate a compact evaluation summary for downstream reporting."""

        completeness = score_completeness(strategy_output)
        consistency = score_consistency(strategy_output)
        critic_blend = (
            critic_review.completeness_score
            + critic_review.consistency_score
            + critic_review.clarity_score
        ) / 3
        quality_score = round(completeness * 0.40 + consistency * 0.30 + critic_blend * 0.30, 3)

        return EvaluationSummary(
            completeness_score=completeness,
            consistency_score=consistency,
            latency_ms=latency_ms,
            estimated_cost_usd=total_cost_from_agent_runs([run.estimated_cost_usd for run in agent_runs]),
            total_tokens=total_tokens_from_agent_runs([run.total_tokens for run in agent_runs]),
            quality_score=quality_score,
        )
