"""LLM adapters for API models, local OpenAI-compatible models, and mock runs."""

from __future__ import annotations

import json
import logging
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, cast

import httpx
from tenacity import AsyncRetrying, retry_if_exception_type, stop_after_attempt, wait_exponential

from .config import Settings

logger = logging.getLogger(__name__)

STOPWORDS = {
    "a",
    "an",
    "and",
    "around",
    "as",
    "at",
    "build",
    "for",
    "from",
    "idea",
    "in",
    "into",
    "is",
    "of",
    "on",
    "or",
    "product",
    "service",
    "startup",
    "that",
    "the",
    "to",
    "with",
}


def estimate_tokens(text: str) -> int:
    """Estimate token count with a simple character heuristic."""

    return max(1, len(text) // 4)


def extract_json_payload(text: str) -> dict[str, Any]:
    """Parse JSON from plain text or fenced code blocks."""

    candidate = text.strip()
    fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", candidate, re.DOTALL)
    if fenced_match:
        candidate = fenced_match.group(1)
    else:
        object_match = re.search(r"(\{.*\})", candidate, re.DOTALL)
        if object_match:
            candidate = object_match.group(1)

    payload = json.loads(candidate)
    if not isinstance(payload, dict):
        raise ValueError("Model response did not decode to a JSON object.")
    return cast(dict[str, Any], payload)


def informative_phrase(text: str, limit: int = 10) -> str:
    """Return a short phrase derived from the first few informative words."""

    words = re.findall(r"[A-Za-z0-9']+", text.lower())
    filtered = [word for word in words if word not in STOPWORDS]
    phrase = " ".join(filtered[:limit]).strip()
    return phrase or "the workflow"


def title_case_words(text: str, limit: int = 3) -> str:
    """Build a title-like phrase from informative words."""

    words = re.findall(r"[A-Za-z0-9']+", text.lower())
    filtered = [word for word in words if word not in STOPWORDS]
    if not filtered:
        return "Signal Desk"
    return " ".join(word.capitalize() for word in filtered[:limit])


def infer_platform(concept: str) -> str:
    """Infer the likely delivery surface for the concept."""

    lowered = concept.lower()
    if "mobile" in lowered or "ios" in lowered or "android" in lowered:
        return "Mobile app"
    if "extension" in lowered or "chrome" in lowered:
        return "Browser extension"
    if "marketplace" in lowered:
        return "Web marketplace"
    return "Web app"


def infer_category(concept: str) -> str:
    """Infer a plausible category label from the product idea."""

    lowered = concept.lower()
    if "marketplace" in lowered:
        return "Marketplace"
    if "compliance" in lowered or "documentation" in lowered or "workflow" in lowered:
        return "Workflow SaaS"
    if "coach" in lowered or "assistant" in lowered or "ai" in lowered:
        return "AI assistant"
    if "subscription" in lowered or "meal" in lowered or "fitness" in lowered:
        return "Consumer subscription"
    if "analytics" in lowered or "dashboard" in lowered:
        return "Analytics product"
    return "Productivity SaaS"


def infer_target_user(concept: str) -> str:
    """Infer a likely customer profile."""

    lowered = concept.lower()
    if "agency" in lowered:
        return "Small agencies that need to move faster without growing headcount"
    if "clinic" in lowered or "health" in lowered:
        return "Operations managers in small healthcare teams with compliance overhead"
    if "parent" in lowered or "family" in lowered:
        return "Busy consumers looking for convenience and consistency"
    if "freelancer" in lowered or "creator" in lowered:
        return "Independent professionals who need lightweight business tooling"
    if "repair" in lowered or "contractor" in lowered:
        return "Service buyers and local operators coordinating offline work"
    return "Time-constrained professionals who want a clear outcome with low setup effort"


def infer_monetization_model(concept: str) -> str:
    """Infer a likely business model for the product."""

    lowered = concept.lower()
    if "marketplace" in lowered:
        return "Transaction take rate with optional promoted listings"
    if "consumer" in lowered or "subscription" in lowered or "meal" in lowered:
        return "Tiered subscription"
    if "enterprise" in lowered or "team" in lowered or "agency" in lowered or "clinic" in lowered:
        return "Per-seat subscription with team plans"
    return "Subscription with a limited free tier"


def infer_product_name(concept: str) -> str:
    """Infer a plausible brand-like name for mock mode."""

    lowered = concept.lower()
    if "meeting" in lowered:
        return "SignalBrief"
    if "meal" in lowered:
        return "Weeknight Flow"
    if "repair" in lowered:
        return "Fixlane"
    if "compliance" in lowered:
        return "TraceLedger"
    if "analytics" in lowered:
        return "Northstar Lens"
    return f"{title_case_words(concept, limit=2)} Hub"


def build_mock_strategy(concept: str, additional_context: str | None = None) -> dict[str, Any]:
    """Create a deterministic but credible strategy document for mock mode."""

    platform = infer_platform(concept)
    category = infer_category(concept)
    naming_context = concept if not additional_context else f"{concept} {additional_context}"
    product_name = infer_product_name(naming_context)
    target_user = infer_target_user(concept)
    monetization_model = infer_monetization_model(concept)
    focus_phrase = informative_phrase(concept, limit=8)
    context_suffix = f" Constraints to respect: {additional_context.strip()}" if additional_context else ""

    product_brief = {
        "product_name": product_name,
        "category": category,
        "target_user": target_user,
        "core_problem": (
            f"Current workflows around {focus_phrase} are fragmented, manual, or too time-consuming for the intended user."
        ),
        "solution_summary": (
            f"{product_name} helps users move from messy inputs to a concrete next step through a guided workflow that prioritizes clarity, speed, and visible value.{context_suffix}"
        ),
        "primary_platform": platform,
        "monetization_model": monetization_model,
        "differentiator": (
            "The product is positioned around a faster first-use experience and a tighter scope than broad all-in-one competitors."
        ),
    }

    user_journey_loops = [
        {
            "name": "Capture the initial need",
            "objective": "Help the user express their job-to-be-done in plain language with minimal setup.",
            "user_steps": [
                "Describe the current task, friction, or objective",
                "Add one or two constraints such as deadline, audience, or budget",
                "Receive a structured starting recommendation immediately",
            ],
            "success_signal": "The user reaches a credible first output without asking for onboarding help.",
            "time_to_value": "Under 5 minutes",
        },
        {
            "name": "Refine into an actionable plan",
            "objective": "Turn the initial output into a concrete plan the user can edit and execute.",
            "user_steps": [
                "Review the generated plan and highlight gaps",
                "Edit the structured output directly",
                "Re-run critique to improve specificity and sequencing",
            ],
            "success_signal": "The user leaves with a plan clear enough to share with a teammate or stakeholder.",
            "time_to_value": "5-15 minutes",
        },
        {
            "name": "Return for repeat work",
            "objective": "Create enough repeatable value that the workflow becomes part of the user's routine.",
            "user_steps": [
                "Save or reuse prior plans",
                "Start from a template or previous context",
                "Track progress across multiple requests",
            ],
            "success_signal": "A meaningful percentage of users create a second plan within the same week.",
            "time_to_value": "Within 7 days",
        },
    ]

    monetization_risk_notes = [
        {
            "category": "monetization",
            "priority": "medium",
            "title": "Price against visible time saved",
            "note": "This concept will convert more easily if the pricing model maps to a clear workflow outcome rather than to generic AI access.",
            "mitigation": "Attach the paid tier to team usage, saved plans, or higher review volume instead of raw prompt count.",
        },
        {
            "category": "delivery",
            "priority": "high",
            "title": "Over-scoping the first release is the main execution risk",
            "note": "The idea can sprawl into templates, collaboration, analytics, and integrations before the core loop is proven.",
            "mitigation": "Ship one narrow workflow first and treat every extra surface as a post-validation decision.",
        },
        {
            "category": "retention",
            "priority": "medium",
            "title": "Retention depends on repeat scenarios, not just a strong first draft",
            "note": "If users only need the product once, acquisition cost will be hard to recover.",
            "mitigation": "Test adjacent repeat use cases and saved-history features early.",
        },
        {
            "category": "go_to_market",
            "priority": "medium",
            "title": "Positioning must be sharper than 'AI assistant'",
            "note": "The market is crowded, so category language alone will not differentiate the product.",
            "mitigation": "Lead with the job-to-be-done, audience, and proof of faster outcomes.",
        },
    ]

    lowered = concept.lower()
    if any(keyword in lowered for keyword in ("health", "clinic", "medical", "compliance", "legal")):
        monetization_risk_notes.append(
            {
                "category": "compliance",
                "priority": "high",
                "title": "Regulated workflows raise trust and policy requirements",
                "note": "Users may expect accuracy, privacy, and auditability beyond what a lightweight assistant can guarantee.",
                "mitigation": "Add review boundaries, data handling rules, and human sign-off steps before claiming workflow fit.",
            }
        )
    else:
        monetization_risk_notes.append(
            {
                "category": "safety",
                "priority": "low",
                "title": "Generated recommendations still need clear ownership",
                "note": "Users should understand where automation ends and judgment begins.",
                "mitigation": "Frame outputs as drafts, keep editability obvious, and preserve source context where possible.",
            }
        )

    task_list = [
        {
            "id": 1,
            "title": "Define the single user workflow this product must solve first",
            "priority": "high",
            "rationale": "A focused job-to-be-done makes prompt design, UX, and positioning meaningfully easier.",
            "estimated_hours": 6.0,
            "dependencies": [],
        },
        {
            "id": 2,
            "title": "Write the structured output schema and critique rubric",
            "priority": "high",
            "rationale": "The schema is the contract between prompt design, evaluation, and the frontend/API.",
            "estimated_hours": 8.0,
            "dependencies": [1],
        },
        {
            "id": 3,
            "title": "Build a vertical slice from input to editable JSON",
            "priority": "high",
            "rationale": "The product needs one end-to-end happy path before additional features matter.",
            "estimated_hours": 20.0,
            "dependencies": [2],
        },
        {
            "id": 4,
            "title": "Interview five target users on output usefulness",
            "priority": "medium",
            "rationale": "User feedback should confirm whether the generated plan is actually decision-ready.",
            "estimated_hours": 10.0,
            "dependencies": [3],
        },
        {
            "id": 5,
            "title": "Decide pricing and packaging for the first paid offer",
            "priority": "medium",
            "rationale": "Business model choices influence saved history, collaboration, and access control.",
            "estimated_hours": 6.0,
            "dependencies": [3],
        },
        {
            "id": 6,
            "title": "Add the minimum trust and safety controls for launch",
            "priority": "medium",
            "rationale": "Users need clear expectations around review, privacy, and limits of automation.",
            "estimated_hours": 8.0,
            "dependencies": [3],
        },
    ]

    follow_up_questions = [
        {
            "question": "Who is the first buyer or champion inside the target audience, and what are they using today instead?",
            "category": "user",
            "reason": "This clarifies both positioning and the minimum credible feature set.",
        },
        {
            "question": "Which part of the workflow must feel almost instant for the product to seem worth trying?",
            "category": "workflow",
            "reason": "Fast time-to-value is likely the main adoption lever for this kind of assistant.",
        },
        {
            "question": "Should pricing optimize for individual experimentation or small-team rollout first?",
            "category": "pricing",
            "reason": "This changes plan limits, account model, and retention strategy.",
        },
        {
            "question": "What data or user context must be available for the output to be decision-ready rather than generic?",
            "category": "data",
            "reason": "The answer determines both prompt quality and integration needs.",
        },
    ]

    return {
        "product_brief": product_brief,
        "user_journey_loops": user_journey_loops,
        "monetization_risk_notes": monetization_risk_notes,
        "task_list": task_list,
        "follow_up_questions": follow_up_questions,
    }


def build_mock_review(concept: str, strategy_output: dict[str, Any]) -> dict[str, Any]:
    """Create a deterministic critic review for mock mode."""

    loops = strategy_output.get("user_journey_loops", [])
    tasks = strategy_output.get("task_list", [])
    notes = strategy_output.get("monetization_risk_notes", [])
    questions = strategy_output.get("follow_up_questions", [])
    brief = strategy_output.get("product_brief", {})

    filled_brief_fields = sum(
        1
        for key in (
            "product_name",
            "category",
            "target_user",
            "core_problem",
            "solution_summary",
            "primary_platform",
            "monetization_model",
            "differentiator",
        )
        if brief.get(key)
    )
    completeness = min(
        1.0,
        round(
            (filled_brief_fields / 8) * 0.45
            + min(len(loops), 3) / 3 * 0.2
            + min(len(tasks), 6) / 6 * 0.2
            + min(len(questions), 4) / 4 * 0.15,
            3,
        ),
    )

    placeholder_hits = 0
    for value in brief.values():
        if isinstance(value, str) and re.search(r"\b(tbd|unknown|placeholder)\b", value, re.IGNORECASE):
            placeholder_hits += 1

    clarity = max(0.45, round(0.92 - placeholder_hits * 0.12 - (0.05 if len(notes) < 3 else 0.0), 3))

    task_ids = {task.get("id") for task in tasks}
    broken_dependencies = [
        dependency
        for task in tasks
        for dependency in task.get("dependencies", [])
        if dependency not in task_ids
    ]
    loop_quality = [loop for loop in loops if loop.get("time_to_value")]
    consistency = max(0.35, round(0.94 - len(broken_dependencies) * 0.15 - (0.08 if len(loop_quality) < 2 else 0.0), 3))

    lowered = concept.lower()
    safety_notes: list[str] = []
    if any(keyword in lowered for keyword in ("health", "medical", "legal", "finance", "compliance", "clinic")):
        safety_notes.append("If this workflow influences regulated decisions, the product needs human review boundaries and stronger auditability.")
    if any(keyword in lowered for keyword in ("marketplace", "contractor", "repair")):
        safety_notes.append("Marketplace flows usually need dispute handling, trust signals, and provider quality controls.")

    issues: list[str] = []
    if len(loops) < 2:
        issues.append("The draft should define at least two distinct user journey loops to show how adoption and repeat use work.")
    if len(notes) < 3:
        issues.append("Monetization and risk coverage is thin; add at least one more business or delivery note.")
    if broken_dependencies:
        issues.append("One or more task dependencies reference missing task IDs.")
    if "subscription" in brief.get("monetization_model", "").lower() and not any(note.get("category") == "retention" for note in notes):
        issues.append("Subscription products usually need a clearer retention hypothesis in the risk section.")

    recommended_revisions = [
        "Sharpen the target user until one buyer profile clearly owns the problem and budget.",
        "Convert the first high-priority task into a concrete validation milestone with a measurable outcome.",
    ]
    if safety_notes:
        recommended_revisions.append("Add launch-readiness notes covering trust, review, and policy boundaries before external rollout.")

    ready_for_delivery = completeness >= 0.80 and clarity >= 0.78 and consistency >= 0.78 and not broken_dependencies

    return {
        "ready_for_delivery": ready_for_delivery,
        "completeness_score": completeness,
        "clarity_score": clarity,
        "consistency_score": consistency,
        "safety_notes": safety_notes,
        "issues": issues,
        "recommended_revisions": recommended_revisions,
    }


@dataclass
class LLMUsage:
    """Usage data captured per model call."""

    prompt_tokens: int | None
    completion_tokens: int | None
    total_tokens: int | None
    estimated_cost_usd: float


@dataclass
class LLMCallResult:
    """Result returned by an adapter after parsing JSON."""

    payload: dict[str, Any]
    raw_text: str
    model_provider: str
    model_name: str
    usage: LLMUsage
    retries: int


class BaseLLMAdapter(ABC):
    """Interface for model providers."""

    provider_name: str

    def __init__(self, settings: Settings):
        self.settings = settings
        self.model_name = settings.active_model_name

    async def generate_json(
        self,
        *,
        prompt_name: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        metadata: dict[str, Any] | None = None,
    ) -> LLMCallResult:
        """Generate a JSON payload with retry handling."""

        attempt_number = 0
        raw_text = ""
        usage = LLMUsage(prompt_tokens=0, completion_tokens=0, total_tokens=0, estimated_cost_usd=0.0)

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(self.settings.llm_max_retries),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            retry=retry_if_exception_type((httpx.HTTPError, json.JSONDecodeError, ValueError)),
            reraise=True,
        ):
            with attempt:
                attempt_number = attempt.retry_state.attempt_number
                raw_text, usage = await self._request_text(
                    prompt_name=prompt_name,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    metadata=metadata or {},
                )
                payload = extract_json_payload(raw_text)

        return LLMCallResult(
            payload=payload,
            raw_text=raw_text,
            model_provider=self.provider_name,
            model_name=self.model_name,
            usage=usage,
            retries=max(0, attempt_number - 1),
        )

    @abstractmethod
    async def _request_text(
        self,
        *,
        prompt_name: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        metadata: dict[str, Any],
    ) -> tuple[str, LLMUsage]:
        """Return raw text plus usage data."""

    def _estimate_usage(self, prompt_text: str, completion_text: str) -> LLMUsage:
        """Estimate usage and cost if the provider does not report them."""

        prompt_tokens = estimate_tokens(prompt_text)
        completion_tokens = estimate_tokens(completion_text)
        total_tokens = prompt_tokens + completion_tokens
        estimated_cost_usd = (
            prompt_tokens / 1_000_000 * self.settings.input_token_cost_usd_per_million
            + completion_tokens / 1_000_000 * self.settings.output_token_cost_usd_per_million
        )
        return LLMUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=round(estimated_cost_usd, 6),
        )


class OpenAIAdapter(BaseLLMAdapter):
    """OpenAI chat completions adapter."""

    provider_name = "openai"

    async def _request_text(
        self,
        *,
        prompt_name: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        metadata: dict[str, Any],
    ) -> tuple[str, LLMUsage]:
        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")

        url = f"{self.settings.openai_base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.settings.openai_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            body = response.json()

        content = body["choices"][0]["message"]["content"]
        usage_payload = body.get("usage", {})
        prompt_text = "\n".join(message["content"] for message in messages)
        usage = LLMUsage(
            prompt_tokens=usage_payload.get("prompt_tokens") or estimate_tokens(prompt_text),
            completion_tokens=usage_payload.get("completion_tokens") or estimate_tokens(content),
            total_tokens=usage_payload.get("total_tokens")
            or (usage_payload.get("prompt_tokens") or estimate_tokens(prompt_text))
            + (usage_payload.get("completion_tokens") or estimate_tokens(content)),
            estimated_cost_usd=round(
                (
                    (usage_payload.get("prompt_tokens") or estimate_tokens(prompt_text))
                    / 1_000_000
                    * self.settings.input_token_cost_usd_per_million
                )
                + (
                    (usage_payload.get("completion_tokens") or estimate_tokens(content))
                    / 1_000_000
                    * self.settings.output_token_cost_usd_per_million
                ),
                6,
            ),
        )
        return content, usage


class LocalOpenAICompatibleAdapter(BaseLLMAdapter):
    """Adapter for local models that expose an OpenAI-compatible endpoint."""

    provider_name = "local"

    async def _request_text(
        self,
        *,
        prompt_name: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        metadata: dict[str, Any],
    ) -> tuple[str, LLMUsage]:
        url = f"{self.settings.local_api_base.rstrip('/')}/chat/completions"
        payload = {
            "model": self.settings.local_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            body = response.json()

        content = body["choices"][0]["message"]["content"]
        usage_payload = body.get("usage", {})
        prompt_text = "\n".join(message["content"] for message in messages)
        if usage_payload:
            usage = LLMUsage(
                prompt_tokens=usage_payload.get("prompt_tokens"),
                completion_tokens=usage_payload.get("completion_tokens"),
                total_tokens=usage_payload.get("total_tokens"),
                estimated_cost_usd=round(
                    (
                        (usage_payload.get("prompt_tokens") or 0)
                        / 1_000_000
                        * self.settings.input_token_cost_usd_per_million
                    )
                    + (
                        (usage_payload.get("completion_tokens") or 0)
                        / 1_000_000
                        * self.settings.output_token_cost_usd_per_million
                    ),
                    6,
                ),
            )
        else:
            usage = self._estimate_usage(prompt_text, content)
        return content, usage


class MockLLMAdapter(BaseLLMAdapter):
    """Deterministic adapter used for tests, local development, and offline benchmarking."""

    provider_name = "mock"

    async def _request_text(
        self,
        *,
        prompt_name: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        metadata: dict[str, Any],
    ) -> tuple[str, LLMUsage]:
        if prompt_name == "planner_strategy":
            payload = build_mock_strategy(
                concept=str(metadata.get("concept", "")),
                additional_context=metadata.get("additional_context"),
            )
        elif prompt_name == "critic_strategy_review":
            payload = build_mock_review(
                concept=str(metadata.get("concept", "")),
                strategy_output=dict(metadata.get("strategy_output", {})),
            )
        else:
            payload = {"status": "unsupported prompt"}

        raw_text = json.dumps(payload, indent=2)
        prompt_text = "\n".join(message["content"] for message in messages)
        usage = self._estimate_usage(prompt_text, raw_text)
        return raw_text, usage


def get_llm_adapter(settings: Settings) -> BaseLLMAdapter:
    """Factory for the configured LLM adapter."""

    if settings.llm_provider == "openai":
        return OpenAIAdapter(settings)
    if settings.llm_provider == "local":
        return LocalOpenAICompatibleAdapter(settings)
    logger.info("Using mock adapter for deterministic local runs.")
    return MockLLMAdapter(settings)
