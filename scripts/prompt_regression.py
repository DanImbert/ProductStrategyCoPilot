"""Run prompt regression assertions against fixed portfolio cases."""

from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Sequence

from src.core.config import Settings
from src.models import ProductIdeaInput, StrategyResponse
from src.services.copilot_service import CopilotService

CASES_PATH = Path("scripts/regression_cases.json")
RESULTS_PATH = Path("artifacts/prompt_regression_results.json")
SUMMARY_PATH = Path("artifacts/prompt_regression_summary.md")
REQUIRED_PROMPT_NAMES = {"planner_strategy", "critic_strategy_review"}


@dataclass(frozen=True)
class RegressionCase:
    """A fixed scenario with minimum acceptable output thresholds."""

    case_id: str
    concept: str
    additional_context: str | None = None
    expected_product_name: str | None = None
    expected_category: str | None = None
    required_risk_categories: tuple[str, ...] = ()
    min_quality_score: float = 0.0
    min_completeness_score: float = 0.0
    min_consistency_score: float = 0.0
    min_task_count: int = 0
    min_question_count: int = 0
    require_ready_for_delivery: bool = False
    require_safety_notes: bool = False


@dataclass(frozen=True)
class RegressionResult:
    """Result of evaluating one regression case."""

    case_id: str
    passed: bool
    quality_score: float
    completeness_score: float
    consistency_score: float
    model_provider: str
    model_name: str
    failures: list[str] = field(default_factory=list)


def load_cases(path: Path = CASES_PATH) -> list[RegressionCase]:
    """Load fixed regression cases from JSON."""

    raw_cases = json.loads(path.read_text(encoding="utf-8"))
    cases: list[RegressionCase] = []
    for raw_case in raw_cases:
        cases.append(
            RegressionCase(
                case_id=raw_case["case_id"],
                concept=raw_case["concept"],
                additional_context=raw_case.get("additional_context"),
                expected_product_name=raw_case.get("expected_product_name"),
                expected_category=raw_case.get("expected_category"),
                required_risk_categories=tuple(raw_case.get("required_risk_categories", [])),
                min_quality_score=raw_case.get("min_quality_score", 0.0),
                min_completeness_score=raw_case.get("min_completeness_score", 0.0),
                min_consistency_score=raw_case.get("min_consistency_score", 0.0),
                min_task_count=raw_case.get("min_task_count", 0),
                min_question_count=raw_case.get("min_question_count", 0),
                require_ready_for_delivery=raw_case.get("require_ready_for_delivery", False),
                require_safety_notes=raw_case.get("require_safety_notes", False),
            )
        )
    return cases


def resolve_settings(args: argparse.Namespace) -> Settings:
    """Build settings from the environment with optional CLI overrides."""

    settings = Settings(enable_file_logging=False)
    updates: dict[str, str] = {}
    if args.provider != "configured":
        updates["llm_provider"] = args.provider
    if args.model:
        if (updates.get("llm_provider") or settings.llm_provider) == "local":
            updates["local_model"] = args.model
        else:
            updates["openai_model"] = args.model
    return settings.model_copy(update=updates)


def evaluate_case(case: RegressionCase, response: StrategyResponse) -> RegressionResult:
    """Check one response against fixed quality and structure assertions."""

    failures: list[str] = []
    brief = response.strategy_output.product_brief
    evaluation = response.evaluation
    review = response.critic_review

    if case.expected_product_name and brief.product_name != case.expected_product_name:
        failures.append(
            f"expected product_name={case.expected_product_name!r}, got {brief.product_name!r}"
        )
    if case.expected_category and brief.category != case.expected_category:
        failures.append(f"expected category={case.expected_category!r}, got {brief.category!r}")
    if evaluation.quality_score < case.min_quality_score:
        failures.append(
            f"quality_score {evaluation.quality_score:.3f} < {case.min_quality_score:.3f}"
        )
    if evaluation.completeness_score < case.min_completeness_score:
        failures.append(
            "completeness_score "
            f"{evaluation.completeness_score:.3f} < {case.min_completeness_score:.3f}"
        )
    if evaluation.consistency_score < case.min_consistency_score:
        failures.append(
            "consistency_score "
            f"{evaluation.consistency_score:.3f} < {case.min_consistency_score:.3f}"
        )
    if len(response.strategy_output.task_list) < case.min_task_count:
        failures.append(
            f"task_list has {len(response.strategy_output.task_list)} items, expected at least {case.min_task_count}"
        )
    if len(response.strategy_output.follow_up_questions) < case.min_question_count:
        failures.append(
            "follow_up_questions has "
            f"{len(response.strategy_output.follow_up_questions)} items, expected at least {case.min_question_count}"
        )
    if case.require_ready_for_delivery and not review.ready_for_delivery:
        failures.append("critic_review.ready_for_delivery was false")
    if case.require_safety_notes and not review.safety_notes:
        failures.append("critic_review.safety_notes was empty")

    present_categories = {note.category.value for note in response.strategy_output.monetization_risk_notes}
    missing_categories = sorted(set(case.required_risk_categories) - present_categories)
    if missing_categories:
        failures.append(f"missing required risk categories: {', '.join(missing_categories)}")

    present_prompt_names = set(response.prompt_versions)
    missing_prompt_names = sorted(REQUIRED_PROMPT_NAMES - present_prompt_names)
    if missing_prompt_names:
        failures.append(f"missing prompt version keys: {', '.join(missing_prompt_names)}")

    first_agent = response.agent_runs[0]
    return RegressionResult(
        case_id=case.case_id,
        passed=not failures,
        quality_score=evaluation.quality_score,
        completeness_score=evaluation.completeness_score,
        consistency_score=evaluation.consistency_score,
        model_provider=first_agent.model_provider,
        model_name=first_agent.model_name,
        failures=failures,
    )


async def run_regression_suite(
    settings: Settings,
    cases: Sequence[RegressionCase] | None = None,
) -> list[RegressionResult]:
    """Run the full regression suite against the service layer."""

    service = CopilotService(settings=settings)
    results: list[RegressionResult] = []
    for case in cases or load_cases():
        response = await service.generate_strategy(
            ProductIdeaInput(
                concept=case.concept,
                additional_context=case.additional_context,
            ),
            request_id=case.case_id,
        )
        results.append(evaluate_case(case, response))
    return results


def write_results_json(results: Sequence[RegressionResult], output_path: Path = RESULTS_PATH) -> None:
    """Write machine-readable regression output."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(result) for result in results]
    output_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def write_summary_markdown(
    results: Sequence[RegressionResult],
    settings: Settings,
    output_path: Path = SUMMARY_PATH,
) -> None:
    """Write a human-readable regression summary."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    passed = sum(1 for result in results if result.passed)
    failed = len(results) - passed
    lines = [
        "# Prompt Regression Summary",
        "",
        f"- Provider: {settings.llm_provider}",
        f"- Model: {settings.active_model_name}",
        f"- Cases: {len(results)}",
        f"- Passed: {passed}",
        f"- Failed: {failed}",
        "",
        "| Case | Passed | Quality | Completeness | Consistency | Notes |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ]
    for result in results:
        note = "OK" if result.passed else "; ".join(result.failures)
        lines.append(
            f"| {result.case_id} | {result.passed} | {result.quality_score:.3f} | "
            f"{result.completeness_score:.3f} | {result.consistency_score:.3f} | {note} |"
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse CLI flags."""

    parser = argparse.ArgumentParser(description="Run prompt regression checks for Product Strategy Copilot.")
    parser.add_argument(
        "--provider",
        choices=["configured", "mock", "local", "openai"],
        default="configured",
        help="Provider to use for the regression suite. Default uses the current environment.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional model override for local or hosted runs.",
    )
    return parser.parse_args()


async def main() -> None:
    """Run the regression suite and fail fast on prompt drift."""

    args = parse_args()
    settings = resolve_settings(args)
    results = await run_regression_suite(settings=settings)
    write_results_json(results)
    write_summary_markdown(results, settings=settings)

    failed = [result for result in results if not result.passed]
    if failed:
        raise SystemExit(
            "Prompt regression failed for: " + ", ".join(result.case_id for result in failed)
        )

    print(
        f"Prompt regression passed: {len(results)}/{len(results)} cases using "
        f"{settings.llm_provider}:{settings.active_model_name}. "
        "Outputs written to artifacts/prompt_regression_results.json and "
        "artifacts/prompt_regression_summary.md"
    )


if __name__ == "__main__":
    asyncio.run(main())
