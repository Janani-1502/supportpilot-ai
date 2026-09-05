from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


Status = Literal[
    "READY_FOR_AGENT",
    "MORE_INFORMATION_REQUIRED",
    "ESCALATE_TO_HUMAN",
]


class EvidenceItem(BaseModel):
    article_id: str
    title: str
    section: str


class HandoffSummary(BaseModel):
    issue: str = ""
    established_facts: list[str] = Field(default_factory=list)
    steps_already_tried: list[str] = Field(default_factory=list)
    human_action_needed: str = ""


class ResolutionResponse(BaseModel):
    issue_category: str
    summary: str
    recommended_resolution: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    confidence: str
    status: Status
    escalation_required: bool
    escalation_reason: str = ""
    handoff_summary: HandoffSummary = Field(default_factory=HandoffSummary)
