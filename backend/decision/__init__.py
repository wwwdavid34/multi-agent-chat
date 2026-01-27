"""Multi-agent decision assistant built on LangGraph.

This module provides a structured decision-making pipeline where expert agents
analyze options, conflicts are detected, humans review assumptions, and a
synthesizer produces a final recommendation.
"""

from __future__ import annotations

from .schemas import (
    ExpertTask,
    OptionAnalysis,
    ExpertOutput,
    Conflict,
    HumanFeedback,
    Recommendation,
)
from .state import DecisionState, merge_expert_outputs

__all__ = [
    "ExpertTask",
    "OptionAnalysis",
    "ExpertOutput",
    "Conflict",
    "HumanFeedback",
    "Recommendation",
    "DecisionState",
    "merge_expert_outputs",
]
