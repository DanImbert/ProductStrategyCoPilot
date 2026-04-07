# Example Inputs And Outputs

These examples show representative API exchanges. They mirror the response shape of the service and include the agent and evaluation metadata returned by the API.

Full checked-in examples are available in:

- [examples/reference_agency_meeting_assistant.json](/Users/scarlettv/Documents/AI-Experiement/examples/reference_agency_meeting_assistant.json)
- [examples/reference_local_repair_marketplace.json](/Users/scarlettv/Documents/AI-Experiement/examples/reference_local_repair_marketplace.json)
- [examples/reference_clinic_compliance_assistant.json](/Users/scarlettv/Documents/AI-Experiement/examples/reference_clinic_compliance_assistant.json)
- [examples/reference_meal_planning_subscription.json](/Users/scarlettv/Documents/AI-Experiement/examples/reference_meal_planning_subscription.json)

## Example 1: Agency Meeting Assistant

Request:

```json
{
  "concept": "An AI assistant for boutique agencies that turns messy meeting notes into client-ready summaries, follow-up emails, and internal task plans.",
  "additional_context": "Optimize for time-to-value within one session."
}
```

Response excerpt:

```json
{
  "strategy_output": {
    "product_brief": {
      "product_name": "SignalBrief",
      "category": "AI assistant",
      "target_user": "Small agencies that need to move faster without growing headcount",
      "core_problem": "Account teams lose time converting rough notes into aligned follow-up work.",
      "solution_summary": "SignalBrief turns messy meeting notes into structured action plans and client-ready drafts.",
      "primary_platform": "Web app",
      "monetization_model": "Per-seat subscription with team plans",
      "differentiator": "It focuses on agency delivery workflow rather than generic writing support."
    },
    "user_journey_loops": [
      {
        "name": "Capture the initial need",
        "objective": "Get rough notes into a usable structured draft quickly.",
        "time_to_value": "Under 5 minutes"
      },
      {
        "name": "Refine into an actionable plan",
        "objective": "Edit the draft into something safe to share internally or with a client.",
        "time_to_value": "5-15 minutes"
      }
    ],
    "task_list": [
      {
        "id": 1,
        "title": "Define the single user workflow this product must solve first",
        "priority": "high"
      },
      {
        "id": 2,
        "title": "Write the structured output schema and critique rubric",
        "priority": "high"
      }
    ]
  },
  "critic_review": {
    "ready_for_delivery": true,
    "completeness_score": 0.93,
    "clarity_score": 0.9,
    "consistency_score": 0.91,
    "issues": [],
    "recommended_revisions": [
      "Sharpen the first buyer profile so packaging is easier to test."
    ]
  },
  "evaluation": {
    "completeness_score": 0.95,
    "consistency_score": 0.92,
    "latency_ms": 118,
    "estimated_cost_usd": 0.000842,
    "total_tokens": 746,
    "quality_score": 0.928
  },
  "agent_runs": [
    {
      "agent_name": "planner",
      "prompt_version": "2026-04-02",
      "model_provider": "mock"
    },
    {
      "agent_name": "critic",
      "prompt_version": "2026-04-02",
      "model_provider": "mock"
    }
  ]
}
```

## Example 2: Local Repair Marketplace

Request:

```json
{
  "concept": "A marketplace that helps homeowners compare vetted repair professionals, manage quotes, and convert decisions into booked jobs faster.",
  "additional_context": "Launch in one city first and emphasize trust."
}
```

Response excerpt:

```json
{
  "strategy_output": {
    "product_brief": {
      "product_name": "Fixlane",
      "category": "Marketplace",
      "target_user": "Service buyers and local operators coordinating offline work",
      "monetization_model": "Transaction take rate with optional promoted listings"
    },
    "monetization_risk_notes": [
      {
        "category": "delivery",
        "priority": "high",
        "title": "Over-scoping the first release is the main execution risk"
      },
      {
        "category": "go_to_market",
        "priority": "medium",
        "title": "Positioning must be sharper than 'AI assistant'"
      }
    ]
  },
  "critic_review": {
    "safety_notes": [
      "Marketplace flows usually need dispute handling, trust signals, and provider quality controls."
    ]
  }
}
```

## Example 3: Clinic Compliance Assistant

Request:

```json
{
  "concept": "A workflow assistant for small clinics that turns policy updates into staff action plans, documentation checklists, and audit reminders.",
  "additional_context": "Compliance-heavy domain with human review."
}
```

Response excerpt:

```json
{
  "strategy_output": {
    "product_brief": {
      "product_name": "TraceLedger",
      "category": "Workflow SaaS",
      "primary_platform": "Web app"
    },
    "monetization_risk_notes": [
      {
        "category": "compliance",
        "priority": "high",
        "title": "Regulated workflows raise trust and policy requirements"
      }
    ]
  },
  "critic_review": {
    "ready_for_delivery": true,
    "safety_notes": [
      "If this workflow influences regulated decisions, the product needs human review boundaries and stronger auditability."
    ]
  }
}
```

## Example 4: Meal Planning Subscription

Request:

```json
{
  "concept": "A mobile subscription app for busy parents that turns dietary goals, school schedules, and grocery budgets into flexible weekly meal plans.",
  "additional_context": "Consumer subscription with strong repeat usage."
}
```

Response excerpt:

```json
{
  "strategy_output": {
    "product_brief": {
      "product_name": "Weeknight Flow",
      "category": "Consumer subscription",
      "primary_platform": "Mobile app",
      "monetization_model": "Tiered subscription"
    },
    "follow_up_questions": [
      {
        "category": "pricing",
        "question": "Should pricing optimize for individual experimentation or family plan rollout first?"
      },
      {
        "category": "workflow",
        "question": "Which part of the workflow must feel almost instant for the product to seem worth trying?"
      }
    ]
  },
  "evaluation": {
    "quality_score": 0.91,
    "latency_ms": 110,
    "estimated_cost_usd": 0.000801
  }
}
```
