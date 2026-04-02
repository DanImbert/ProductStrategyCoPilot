"""Unit tests for evaluation heuristics."""

from src.evaluation.metrics import score_completeness, score_consistency
from src.models import (
    BuildTaskItem,
    BusinessRiskNote,
    FollowUpQuestion,
    Priority,
    ProductBrief,
    ProductStrategyDocument,
    QuestionCategory,
    RiskCategory,
    UserJourneyLoop,
)


def build_document() -> ProductStrategyDocument:
    """Create a representative strategy document for tests."""

    return ProductStrategyDocument(
        product_brief=ProductBrief(
            product_name="SignalBrief",
            category="AI assistant",
            target_user="Small agencies that need to turn client meetings into follow-up actions quickly.",
            core_problem="Account leads lose time rewriting meeting notes into actionable client follow-ups.",
            solution_summary="The product turns raw meeting notes into structured action plans and client-ready summaries.",
            primary_platform="Web app",
            monetization_model="Per-seat subscription",
            differentiator="It narrows scope to agency delivery workflows instead of acting like a generic writing assistant.",
        ),
        user_journey_loops=[
            UserJourneyLoop(
                name="Capture meeting context",
                objective="Get a rough meeting dump into the product with minimal cleanup.",
                user_steps=["Paste notes", "Select client", "Choose output template"],
                success_signal="The first summary feels usable without heavy editing.",
                time_to_value="Under 5 minutes",
            ),
            UserJourneyLoop(
                name="Approve follow-up plan",
                objective="Turn the generated draft into a final plan that can be shared internally.",
                user_steps=["Review suggestions", "Edit priorities", "Export to task tracker"],
                success_signal="The team sends or saves a final plan in the same session.",
                time_to_value="5-15 minutes",
            ),
        ],
        monetization_risk_notes=[
            BusinessRiskNote(
                category=RiskCategory.MONETIZATION,
                priority=Priority.MEDIUM,
                title="Price against saved coordination time",
                note="The product needs to prove clear time savings to justify per-seat pricing.",
                mitigation="Measure time-to-first-plan and compare against current agency workflows.",
            ),
            BusinessRiskNote(
                category=RiskCategory.DELIVERY,
                priority=Priority.HIGH,
                title="Scope creep risk",
                note="Calendar, CRM, and PM integrations can overwhelm the first release if added too early.",
                mitigation="Start with copy-paste input and one export target before broad integrations.",
            ),
            BusinessRiskNote(
                category=RiskCategory.RETENTION,
                priority=Priority.MEDIUM,
                title="Repeat usage depends on team workflows",
                note="Single-player note generation is less sticky than shared delivery workflows.",
                mitigation="Test shared review and saved templates with early users.",
            ),
            BusinessRiskNote(
                category=RiskCategory.SAFETY,
                priority=Priority.LOW,
                title="Generated plans need human approval",
                note="Users should remain accountable for client-facing outputs.",
                mitigation="Keep edits obvious and require review before sending anything externally.",
            ),
        ],
        task_list=[
            BuildTaskItem(
                id=1,
                title="Define the agency workflow to support first",
                priority=Priority.HIGH,
                rationale="A single repeatable workflow is needed before prompt tuning matters.",
                estimated_hours=6,
                dependencies=[],
            ),
            BuildTaskItem(
                id=2,
                title="Design the structured output schema",
                priority=Priority.HIGH,
                rationale="The schema is the contract between prompts, UI, and evaluation.",
                estimated_hours=8,
                dependencies=[1],
            ),
            BuildTaskItem(
                id=3,
                title="Build the end-to-end planning flow",
                priority=Priority.MEDIUM,
                rationale="A full vertical slice is required to test usefulness with real users.",
                estimated_hours=20,
                dependencies=[2],
            ),
        ],
        follow_up_questions=[
            FollowUpQuestion(
                question="Who actually buys this first: the agency owner, ops lead, or individual account manager?",
                category=QuestionCategory.USER,
                reason="This changes packaging, onboarding, and messaging.",
            ),
            FollowUpQuestion(
                question="What output has to feel nearly perfect on day one for the product to seem worth paying for?",
                category=QuestionCategory.WORKFLOW,
                reason="It reveals the most important quality bar for the first workflow.",
            ),
            FollowUpQuestion(
                question="Will teams expect task exports or collaboration before they will adopt the product?",
                category=QuestionCategory.SCOPE,
                reason="This affects the MVP boundary and retention plan.",
            ),
        ],
    )


def test_completeness_is_high_for_well_formed_document() -> None:
    document = build_document()
    assert score_completeness(document) >= 0.85


def test_consistency_drops_with_invalid_dependencies() -> None:
    document = build_document()
    broken = document.model_copy(
        update={
            "task_list": [
                *document.task_list[:-1],
                document.task_list[-1].model_copy(update={"dependencies": [99]}),
            ]
        }
    )
    assert score_consistency(broken) < score_consistency(document)
