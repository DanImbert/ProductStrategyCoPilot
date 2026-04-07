# Architecture

```mermaid
flowchart TD
    Request[Incoming REST request] --> API[FastAPI route]
    API --> RequestId[Request ID middleware]
    RequestId --> Service[CopilotService]
    Service --> PromptRegistry[Prompt registry]
    PromptRegistry --> Planner[PlannerAgent]
    PromptRegistry --> Critic[CriticAgent]
    Planner --> Adapter[LLM Adapter]
    Adapter --> Retry[Retry and JSON parsing]
    Retry --> Strategy[ProductStrategyDocument]
    Strategy --> Critic[CriticAgent]
    Critic --> Adapter
    Critic --> Review[CriticReview]
    Service --> Evaluator[ResponseEvaluator]
    Planner --> Metrics[AgentRunMetrics]
    Critic --> Metrics
    Evaluator --> Response[StrategyResponse]
    Response --> Benchmark[Benchmark and examples]
```

## Main components

- `api/`: HTTP boundary, request parsing, dependency injection
- `services/`: orchestration layer that coordinates planner, critic, and evaluation
- `agents/`: agent implementations with versioned prompts and typed outputs
- `core/`: config, prompt registry, model adapters, logging
- `evaluation/`: heuristic quality scoring, latency and cost rollups
- `tests/`: core logic and API behavior

## Zero-Cost Modes

- `mock`: deterministic offline baseline used by default for tests, regression checks, and benchmark reproducibility
- `local`: free OpenAI-compatible local model endpoint such as Ollama or LM Studio
- `openai`: optional hosted provider path kept behind environment configuration
