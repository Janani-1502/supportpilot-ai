from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


READY_FOR_AGENT = "READY_FOR_AGENT"
MORE_INFORMATION_REQUIRED = "MORE_INFORMATION_REQUIRED"
ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"

ALLOWED_STATUSES = {
    READY_FOR_AGENT,
    MORE_INFORMATION_REQUIRED,
    ESCALATE_TO_HUMAN,
}


class EvidenceItem(BaseModel):
    article_id: str
    title: str
    section: str


class HandoffSummary(BaseModel):
    issue: str = ""
    established_facts: list[str] = []
    steps_already_tried: list[str] = []
    human_action_needed: str = ""


class ResolutionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    issue_category: str
    summary: str
    recommended_resolution: list[str]
    evidence: list[EvidenceItem]
    missing_information: list[str]
    confidence: str
    status: str
    escalation_required: bool
    escalation_reason: str
    handoff_summary: HandoffSummary


def empty_handoff() -> dict[str, Any]:
    return {
        "issue": "",
        "established_facts": [],
        "steps_already_tried": [],
        "human_action_needed": "",
    }


def build_response(
    *,
    issue_category: str,
    summary: str,
    recommended_resolution: list[str],
    evidence: list[dict[str, str]],
    missing_information: list[str],
    confidence: str,
    status: str,
    escalation_required: bool,
    escalation_reason: str,
    handoff_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:

    if status not in ALLOWED_STATUSES:
        raise ValueError("Invalid response status.")

    return {
        "issue_category": issue_category,
        "summary": summary,
        "recommended_resolution": recommended_resolution,
        "evidence": evidence,
        "missing_information": missing_information,
        "confidence": confidence,
        "status": status,
        "escalation_required": escalation_required,
        "escalation_reason": escalation_reason,
        "handoff_summary": handoff_summary or empty_handoff(),
    }