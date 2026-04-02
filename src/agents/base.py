"""Shared agent primitives."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

from ..models import AgentRunMetrics

T = TypeVar("T")


@dataclass
class AgentRunResult(Generic[T]):
    """Container for agent output plus execution metadata."""

    output: T
    execution: AgentRunMetrics


class Agent(ABC, Generic[T]):
    """Base class for planner and critic agents."""

    name: str
    version: str

    @abstractmethod
    async def run(self, *args, **kwargs) -> AgentRunResult[T]:
        """Execute the agent and return typed output."""
