from __future__ import annotations

from typing import Any


READY_FOR_AGENT = "READY_FOR_AGENT"
MORE_INFORMATION_REQUIRED = "MORE_INFORMATION_REQUIRED"
ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"

ALLOWED_STATUSES = {
    READY_FOR_AGENT,
    MORE_INFORMATION_REQUIRED,
    ESCALATE_TO_HUMAN,
}


class EvidenceItem:
    def __init__(
        self,
        article_id: str,
        title: str,
        section: str,
    ):
        self.article_id = article_id
        self.title = title
        self.section = section

    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> "EvidenceItem":
        return cls(
            article_id=str(data.get("article_id", "")),
            title=str(data.get("title", "")),
            section=str(data.get("section", "")),
        )

    def model_dump(self) -> dict[str, str]:
        return {
            "article_id": self.article_id,
            "title": self.title,
            "section": self.section,
        }


class HandoffSummary:
    def __init__(
        self,
        issue: str = "",
        established_facts: list[str] | None = None,
        steps_already_tried: list[str] | None = None,
        human_action_needed: str = "",
    ):
        self.issue = issue
        self.established_facts = established_facts or []
        self.steps_already_tried = steps_already_tried or []
        self.human_action_needed = human_action_needed

    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> "HandoffSummary":
        return cls(
            issue=str(data.get("issue", "")),
            established_facts=list(data.get("established_facts", [])),
            steps_already_tried=list(data.get("steps_already_tried", [])),
            human_action_needed=str(
                data.get("human_action_needed", "")
            ),
        )

    def model_dump(self) -> dict[str, Any]:
        return {
            "issue": self.issue,
            "established_facts": self.established_facts,
            "steps_already_tried": self.steps_already_tried,
            "human_action_needed": self.human_action_needed,
        }


class ResolutionResponse:
    def __init__(
        self,
        issue_category: str,
        summary: str,
        recommended_resolution: list[str],
        evidence: list[EvidenceItem | dict[str, str]],
        missing_information: list[str],
        confidence: str,
        status: str,
        escalation_required: bool,
        escalation_reason: str,
        handoff_summary: HandoffSummary | dict[str, Any] | None = None,
    ):
        self.issue_category = issue_category
        self.summary = summary
        self.recommended_resolution = recommended_resolution
        self.evidence = [
            item
            if isinstance(item, EvidenceItem)
            else EvidenceItem.model_validate(item)
            for item in evidence
        ]
        self.missing_information = missing_information
        self.confidence = confidence
        self.status = status
        self.escalation_required = escalation_required
        self.escalation_reason = escalation_reason

        if isinstance(handoff_summary, HandoffSummary):
            self.handoff_summary = handoff_summary
        else:
            self.handoff_summary = HandoffSummary.model_validate(
                handoff_summary or {}
            )

    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> "ResolutionResponse":
        return cls(
            issue_category=str(data.get("issue_category", "")),
            summary=str(data.get("summary", "")),
            recommended_resolution=list(
                data.get("recommended_resolution", [])
            ),
            evidence=list(data.get("evidence", [])),
            missing_information=list(
                data.get("missing_information", [])
            ),
            confidence=str(data.get("confidence", "low")),
            status=str(data.get("status", "")),
            escalation_required=bool(
                data.get("escalation_required", False)
            ),
            escalation_reason=str(
                data.get("escalation_reason", "")
            ),
            handoff_summary=data.get("handoff_summary"),
        )

    def model_dump(self) -> dict[str, Any]:
        return {
            "issue_category": self.issue_category,
            "summary": self.summary,
            "recommended_resolution": self.recommended_resolution,
            "evidence": [
                item.model_dump() for item in self.evidence
            ],
            "missing_information": self.missing_information,
            "confidence": self.confidence,
            "status": self.status,
            "escalation_required": self.escalation_required,
            "escalation_reason": self.escalation_reason,
            "handoff_summary": self.handoff_summary.model_dump(),
        }


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