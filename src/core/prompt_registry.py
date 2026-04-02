"""Prompt registry with explicit versions for traceability."""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptSpec:
    """Versioned prompt template."""

    name: str
    version: str
    system_prompt: str
    user_template: str
    temperature: float
    max_tokens: int

    def render(self, **kwargs: str) -> list[dict[str, str]]:
        """Render prompt messages for the chat endpoint."""

        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": self.user_template.format(**kwargs)},
        ]


PLANNER_PROMPT = PromptSpec(
    name="planner_strategy",
    version="2026-04-02",
    system_prompt=(
        "You are the Planner agent in a product strategy copilot. "
        "Transform an informal product or startup idea into a concise but credible strategy document. "
        "Return valid JSON only."
    ),
    user_template=(
        "Convert the following product idea into a structured strategy document.\n\n"
        "Concept:\n{concept}\n\n"
        "Additional context:\n{additional_context}\n\n"
        "Return JSON with these top-level keys exactly:\n"
        "product_brief, user_journey_loops, monetization_risk_notes, task_list, follow_up_questions.\n\n"
        "Schema guidance:\n"
        "- product_brief: product_name, category, target_user, core_problem, solution_summary, primary_platform, monetization_model, differentiator\n"
        "- user_journey_loops: 2-3 items with name, objective, user_steps, success_signal, time_to_value\n"
        "- monetization_risk_notes: 4-5 items with category, priority, title, note, mitigation\n"
        "- task_list: 5-7 items with id, title, priority, rationale, estimated_hours, dependencies\n"
        "- follow_up_questions: 3-4 items with question, category, reason\n\n"
        "Requirements:\n"
        "- Write for a non-technical founder or operator.\n"
        "- Keep scope realistic for a small team.\n"
        "- Make tradeoffs explicit instead of hand-wavy.\n"
        "- Do not mention AI unless it is central to the concept itself.\n"
    ),
    temperature=0.3,
    max_tokens=1800,
)


CRITIC_PROMPT = PromptSpec(
    name="critic_strategy_review",
    version="2026-04-02",
    system_prompt=(
        "You are the Critic agent in a product strategy copilot. "
        "Review the planner output for completeness, clarity, consistency, and safety or compliance gaps. "
        "Return valid JSON only."
    ),
    user_template=(
        "Review this product idea and its current strategy output.\n\n"
        "Original idea:\n{concept}\n\n"
        "Current strategy output:\n{strategy_output}\n\n"
        "Return JSON with these top-level keys exactly:\n"
        "ready_for_delivery, completeness_score, clarity_score, consistency_score, safety_notes, issues, recommended_revisions.\n\n"
        "Scoring rules:\n"
        "- Scores must be between 0.0 and 1.0.\n"
        "- completeness_score evaluates whether all expected sections are specific enough to act on.\n"
        "- clarity_score evaluates readability and lack of vague phrasing.\n"
        "- consistency_score evaluates whether user loops, target user, monetization choices, and task plan fit together.\n"
        "- ready_for_delivery should be true only if the draft is coherent enough for a product discussion.\n"
    ),
    temperature=0.1,
    max_tokens=1200,
)


PROMPT_REGISTRY = {
    PLANNER_PROMPT.name: PLANNER_PROMPT,
    CRITIC_PROMPT.name: CRITIC_PROMPT,
}


def prompt_versions() -> dict[str, str]:
    """Return the current prompt versions for API metadata."""

    return {name: prompt.version for name, prompt in PROMPT_REGISTRY.items()}


def render_strategy_output_for_prompt(strategy_output: dict) -> str:
    """Format JSON consistently before passing it to the critic prompt."""

    return json.dumps(strategy_output, indent=2, sort_keys=True)
