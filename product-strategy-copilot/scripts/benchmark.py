"""Run a small benchmark suite and emit CSV plus Markdown summaries."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.config import Settings
from src.models import BenchmarkResult, ProductIdeaInput
from src.services.copilot_service import CopilotService

INPUT_PATH = Path("scripts/example_inputs.json")


def load_cases() -> list[dict[str, str]]:
    """Load benchmark cases from JSON."""

    return json.loads(INPUT_PATH.read_text(encoding="utf-8"))


def resolve_settings(args: argparse.Namespace) -> Settings:
    """Build settings from environment with optional benchmark overrides."""

    settings = Settings()
    updates: dict[str, str] = {}
    if args.provider != "configured":
        updates["llm_provider"] = args.provider
    if args.model:
        if (updates.get("llm_provider") or settings.llm_provider) == "local":
            updates["local_model"] = args.model
        else:
            updates["openai_model"] = args.model
    return settings.model_copy(update=updates)


def measurement_mode(provider: str) -> str:
    """Describe whether benchmark metrics come from live model calls or offline heuristics."""

    return "synthetic" if provider == "mock" else "live"


async def run_benchmark(settings: Settings, limit: int | None = None) -> list[BenchmarkResult]:
    """Run benchmark cases directly against the service layer."""

    service = CopilotService(settings=settings)
    results: list[BenchmarkResult] = []
    provider = settings.llm_provider
    model_name = settings.active_model_name
    cases = load_cases()[:limit] if limit else load_cases()

    for case in cases:
        try:
            response = await service.generate_strategy(
                ProductIdeaInput(
                    concept=case["concept"],
                    additional_context=case.get("additional_context"),
                ),
                request_id=case["case_id"],
            )
            results.append(
                BenchmarkResult(
                    case_id=case["case_id"],
                    concept=case["concept"],
                    success=True,
                    provider=provider,
                    model_name=model_name,
                    measurement_mode=measurement_mode(provider),
                    latency_ms=response.evaluation.latency_ms,
                    completeness_score=response.evaluation.completeness_score,
                    consistency_score=response.evaluation.consistency_score,
                    quality_score=response.evaluation.quality_score,
                    estimated_cost_usd=response.evaluation.estimated_cost_usd,
                    total_tokens=response.evaluation.total_tokens,
                )
            )
        except Exception as exc:  # pragma: no cover - benchmark error path
            results.append(
                BenchmarkResult(
                    case_id=case["case_id"],
                    concept=case["concept"],
                    success=False,
                    provider=provider,
                    model_name=model_name,
                    measurement_mode=measurement_mode(provider),
                    latency_ms=0,
                    estimated_cost_usd=0.0,
                    total_tokens=0,
                    notes=str(exc),
                )
            )

    return results


def write_csv(results: list[BenchmarkResult], output_path: Path) -> None:
    """Write flat benchmark metrics to CSV."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "case_id",
                "success",
                "provider",
                "model_name",
                "measurement_mode",
                "latency_ms",
                "completeness_score",
                "consistency_score",
                "quality_score",
                "estimated_cost_usd",
                "total_tokens",
                "notes",
            ]
        )
        for result in results:
            writer.writerow(
                [
                    result.case_id,
                    result.success,
                    result.provider,
                    result.model_name,
                    result.measurement_mode,
                    result.latency_ms,
                    result.completeness_score,
                    result.consistency_score,
                    result.quality_score,
                    result.estimated_cost_usd,
                    result.total_tokens,
                    result.notes or "",
                ]
            )


def write_markdown(results: list[BenchmarkResult], output_path: Path) -> None:
    """Write a human-readable benchmark summary."""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    successes = [result for result in results if result.success]
    average_latency = round(sum(result.latency_ms for result in successes) / max(1, len(successes)), 1)
    average_quality = round(sum((result.quality_score or 0.0) for result in successes) / max(1, len(successes)), 3)
    average_cost = round(sum(result.estimated_cost_usd for result in successes) / max(1, len(successes)), 6)
    provider = results[0].provider if results else "unknown"
    model_name = results[0].model_name if results else "unknown"
    mode = results[0].measurement_mode if results else "unknown"

    lines = [
        "# Benchmark Summary",
        "",
        f"- Cases: {len(results)}",
        f"- Successful runs: {len(successes)}",
        f"- Provider: {provider}",
        f"- Model: {model_name}",
        f"- Measurement mode: {mode}",
        f"- Average latency (ms): {average_latency}",
        f"- Average quality score: {average_quality}",
        f"- Average estimated cost (USD): {average_cost}",
        "",
        "| Case | Success | Latency (ms) | Completeness | Consistency | Quality | Cost (USD) | Mode |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for result in results:
        lines.append(
            f"| {result.case_id} | {result.success} | {result.latency_ms} | "
            f"{'' if result.completeness_score is None else result.completeness_score} | "
            f"{'' if result.consistency_score is None else result.consistency_score} | "
            f"{'' if result.quality_score is None else result.quality_score} | "
            f"{result.estimated_cost_usd:.6f} | {result.measurement_mode} |"
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    """Parse CLI flags for benchmark runs."""

    parser = argparse.ArgumentParser(description="Run the Product Strategy Copilot benchmark suite.")
    parser.add_argument(
        "--provider",
        choices=["configured", "mock", "local", "openai"],
        default="configured",
        help="Benchmark provider. 'configured' uses the current environment. Default keeps the project zero-cost.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional model override for the selected provider.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional number of benchmark cases to run.",
    )
    return parser.parse_args()


async def main() -> None:
    """Run the benchmark and write artifacts."""

    args = parse_args()
    settings = resolve_settings(args)
    results = await run_benchmark(settings=settings, limit=args.limit)
    artifacts_dir = Path("artifacts")
    write_csv(results, artifacts_dir / "benchmark_results.csv")
    write_markdown(results, artifacts_dir / "benchmark_summary.md")

    successful_runs = sum(1 for result in results if result.success)
    print(
        f"Benchmark completed: {successful_runs}/{len(results)} successful runs using "
        f"{settings.llm_provider}:{settings.active_model_name}. "
        "Outputs written to artifacts/benchmark_results.csv and artifacts/benchmark_summary.md"
    )


if __name__ == "__main__":
    asyncio.run(main())
