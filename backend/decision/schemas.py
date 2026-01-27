"""Pydantic schemas for the decision assistant pipeline.

These models define the data exchanged between graph nodes:
- Planner emits ExpertTask items
- Expert nodes produce ExpertOutput with OptionAnalysis per option
- Conflict detector emits Conflict items
- Human gate consumes/produces HumanFeedback
- Synthesizer produces a Recommendation
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ExpertTask(BaseModel):
    """A task assigned to a domain expert by the planner."""

    expert_role: str
    deliverable: str


class OptionAnalysis(BaseModel):
    """One expert's analysis of a single decision option."""

    option: str
    claims: list[str]
    numbers: dict[str, Any] = Field(default_factory=dict)
    risks: list[str] = Field(default_factory=list)
    score: float = Field(ge=0, le=10)


class ExpertOutput(BaseModel):
    """Full output from one expert, covering all options they analysed."""

    expert_role: str
    option_analyses: dict[str, OptionAnalysis]
    assumptions: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)


class Conflict(BaseModel):
    """A disagreement or data conflict detected between experts."""

    conflict_type: str
    topic: str
    experts: list[str]
    values: list[str]


class HumanFeedback(BaseModel):
    """Structured feedback from the human reviewer at the gate node."""

    action: str
    approved_assumptions: list[str] = Field(default_factory=list)
    rejected_assumptions: list[str] = Field(default_factory=list)
    removed_options: list[str] = Field(default_factory=list)
    updated_constraints: dict[str, Any] = Field(default_factory=dict)
    additional_instructions: str = ""


class Recommendation(BaseModel):
    """Final synthesised recommendation produced by the synthesizer node."""

    recommended_option: str
    reasoning: list[str]
    tradeoffs: dict[str, dict]
    risks: list[str]
    what_would_change_mind: list[str]
    confidence: float = Field(ge=0, le=1)
