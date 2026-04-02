"""Tests for adapter selection and retry behavior."""

from __future__ import annotations

import asyncio

from src.core.config import Settings
from src.core.llm_client import BaseLLMAdapter, LLMUsage, LocalOpenAICompatibleAdapter, MockLLMAdapter, OpenAIAdapter, get_llm_adapter


class FlakyJsonAdapter(BaseLLMAdapter):
    """Adapter that fails once with invalid JSON and then succeeds."""

    provider_name = "test"

    def __init__(self, settings: Settings):
        super().__init__(settings)
        self.calls = 0

    async def _request_text(
        self,
        *,
        prompt_name: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
        metadata: dict[str, str],
    ) -> tuple[str, LLMUsage]:
        self.calls += 1
        if self.calls == 1:
            raw_text = "not valid json"
        else:
            raw_text = '{"status": "ok"}'
        usage = self._estimate_usage("\n".join(message["content"] for message in messages), raw_text)
        return raw_text, usage


def test_get_llm_adapter_supports_zero_cost_and_optional_provider_switching() -> None:
    assert isinstance(get_llm_adapter(Settings(llm_provider="mock")), MockLLMAdapter)
    assert isinstance(get_llm_adapter(Settings(llm_provider="local")), LocalOpenAICompatibleAdapter)
    assert isinstance(get_llm_adapter(Settings(llm_provider="openai")), OpenAIAdapter)


def test_generate_json_retries_once_after_invalid_json() -> None:
    adapter = FlakyJsonAdapter(Settings(llm_provider="mock", llm_max_retries=2))

    result = asyncio.run(
        adapter.generate_json(
            prompt_name="planner_strategy",
            messages=[{"role": "user", "content": "hello"}],
            temperature=0.1,
            max_tokens=50,
            metadata={},
        )
    )

    assert result.payload == {"status": "ok"}
    assert result.retries == 1
    assert adapter.calls == 2
