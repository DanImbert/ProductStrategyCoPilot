"""Heuristic evaluation metrics for strategy quality and operational cost."""

from __future__ import annotations

import re

from ..models import Priority, ProductStrategyDocument

PRIORITY_ORDER = {
    Priority.HIGH: 0,
    Priority.MEDIUM: 1,
    Priority.LOW: 2,
}


def _has_placeholder(text: str) -> bool:
    """Check whether a string still contains obvious placeholder language."""

    return bool(re.search(r"\b(tbd|unknown|placeholder|lorem)\b", text, re.IGNORECASE))


def score_completeness(document: ProductStrategyDocument) -> float:
    """Score whether all expected sections are present and filled in."""

    brief = document.product_brief
    brief_fields = [
        brief.product_name,
        brief.category,
        brief.target_user,
        brief.core_problem,
        brief.solution_summary,
        brief.primary_platform,
        brief.monetization_model,
        brief.differentiator,
    ]

    brief_score = sum(1 for field in brief_fields if field and not _has_placeholder(field)) / len(brief_fields)
    loops_score = min(len(document.user_journey_loops), 3) / 3
    notes_score = min(len(document.monetization_risk_notes), 4) / 4
    tasks_score = min(len(document.task_list), 6) / 6
    questions_score = min(len(document.follow_up_questions), 4) / 4

    return round(
        brief_score * 0.40
        + loops_score * 0.20
        + notes_score * 0.15
        + tasks_score * 0.15
        + questions_score * 0.10,
        3,
    )


def score_consistency(document: ProductStrategyDocument) -> float:
    """Score internal consistency across target user, plan, and lifecycle loops."""

    task_ids = {task.id for task in document.task_list}
    dependency_checks: list[bool] = []
    for task in document.task_list:
        for dependency in task.dependencies:
            dependency_checks.append(dependency in task_ids and dependency != task.id)

    dependencies_score = 1.0 if not dependency_checks else sum(dependency_checks) / len(dependency_checks)
    loop_quality_score = (
        sum(1 for loop in document.user_journey_loops if loop.time_to_value and len(loop.user_steps) >= 2)
        / max(1, len(document.user_journey_loops))
    )
    specificity_texts = [
        text
        for text in (
            document.product_brief.core_problem,
            document.product_brief.solution_summary,
            document.product_brief.differentiator,
            *(note.note for note in document.monetization_risk_notes),
            *(task.rationale for task in document.task_list),
        )
    ]
    specificity_score = sum(not _has_placeholder(text) for text in specificity_texts) / max(1, len(specificity_texts))

    priorities = [PRIORITY_ORDER[task.priority] for task in document.task_list]
    ordering_score = 1.0 if priorities == sorted(priorities) else 0.7

    return round(
        dependencies_score * 0.35
        + loop_quality_score * 0.20
        + specificity_score * 0.25
        + ordering_score * 0.20,
        3,
    )


def total_tokens_from_agent_runs(agent_runs_total_tokens: list[int | None]) -> int:
    """Sum total tokens while tolerating missing provider usage."""

    return sum(token_count or 0 for token_count in agent_runs_total_tokens)


def total_cost_from_agent_runs(agent_run_costs: list[float]) -> float:
    """Sum agent costs in USD."""

    return round(sum(agent_run_costs), 6)
