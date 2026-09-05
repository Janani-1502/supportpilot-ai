from __future__ import annotations

import re
from typing import Any

from src.document_service import retrieve_relevant_articles
from src.gemini_service import GeminiService
from src.models import EvidenceItem, HandoffSummary, ResolutionResponse


HIGH_RISK_PATTERNS = (
    r"\bfraud\b",
    r"\bunauthori[sz]ed\b",
    r"\bsomeone accessed\b",
    r"\blegal\b",
    r"\bcomplaint\b",
    r"\bthreat\b",
    r"\bemergency\b",
    r"\bprivacy\b",
    r"\bdata breach\b",
    r"\bcompensation\b",
)

CONNECTIVITY_TERMS = ("internet", "wifi", "broadband", "router", "connection", "offline")
CONNECTIVITY_DETAIL_TERMS = (
    "paid",
    "payment",
    "bill",
    "invoice",
    "disconnected",
    "red light",
    "router",
    "outage",
    "restarted",
)


def _contains_high_risk_request(message: str) -> bool:
    return any(re.search(pattern, message, flags=re.IGNORECASE) for pattern in HIGH_RISK_PATTERNS)


def _is_incomplete_connectivity_request(message: str) -> bool:
    normalized = message.lower()
    has_connectivity_topic = any(term in normalized for term in CONNECTIVITY_TERMS)
    has_specific_detail = any(term in normalized for term in CONNECTIVITY_DETAIL_TERMS)
    return has_connectivity_topic and not has_specific_detail


def _category(message: str) -> str:
    normalized = message.lower()
    if _contains_high_risk_request(message):
        return "Safety escalation"
    if any(term in normalized for term in ("payment", "paid", "bill", "invoice")):
        return "Billing and payment"
    if any(term in normalized for term in ("plan", "upgrade", "downgrade", "cancel")):
        return "Plan management"
    if any(term in normalized for term in ("password", "login", "otp", "locked", "access")):
        return "Account access"
    if any(term in normalized for term in CONNECTIVITY_TERMS):
        return "Connectivity"
    return "General support"


def _evidence(articles: list[dict[str, Any]]) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            article_id=article["id"],
            title=article["title"],
            section="content",
        )
        for article in articles
    ]


def _account_facts(account_snapshot: dict[str, Any]) -> list[str]:
    fields = ("id", "plan", "billing", "restriction", "known_outage", "verification")
    return [f"{field}: {account_snapshot[field]}" for field in fields if field in account_snapshot]


def _safe_fallback(
    category: str,
    account_snapshot: dict[str, Any],
    articles: list[dict[str, Any]],
) -> ResolutionResponse:
    recommendations = [
        f"Follow the verified local guidance in {article['id']}: {article['content']}"
        for article in articles
    ]
    return ResolutionResponse(
        issue_category=category,
        summary="Relevant local support guidance was found for this customer message.",
        recommended_resolution=recommendations,
        evidence=_evidence(articles),
        missing_information=[],
        confidence="medium",
        status="READY_FOR_AGENT",
        escalation_required=False,
        escalation_reason="",
        handoff_summary=HandoffSummary(
            issue=category,
            established_facts=_account_facts(account_snapshot),
            steps_already_tried=[],
            human_action_needed="",
        ),
    )


def _validated_gemini_response(
    response: ResolutionResponse | None,
    retrieved_articles: list[dict[str, Any]],
) -> ResolutionResponse | None:
    if response is None:
        return None

    retrieved_by_id = {article["id"]: article for article in retrieved_articles}
    if not response.evidence:
        return None

    for item in response.evidence:
        article = retrieved_by_id.get(item.article_id)
        if article is None or item.title != article["title"]:
            return None

    return response


def analyze_support_case(
    *,
    customer_message: str,
    conversation_history: list[dict[str, str]] | None,
    account_snapshot: dict[str, Any] | None,
    gemini_service: GeminiService | None = None,
) -> ResolutionResponse:
    """Produce a safe structured response from local evidence and optional Gemini."""
    message = customer_message.strip()
    history = conversation_history or []
    account = account_snapshot or {}

    if not message:
        return ResolutionResponse(
            issue_category="Unknown",
            summary="A customer message is required before the issue can be assessed.",
            recommended_resolution=[],
            evidence=[],
            missing_information=["Customer issue description"],
            confidence="low",
            status="MORE_INFORMATION_REQUIRED",
            escalation_required=False,
            escalation_reason="",
        )

    if not account:
        return ResolutionResponse(
            issue_category="Unknown",
            summary="An account snapshot is required for account-specific support guidance.",
            recommended_resolution=[],
            evidence=[],
            missing_information=["Verified account snapshot"],
            confidence="low",
            status="MORE_INFORMATION_REQUIRED",
            escalation_required=False,
            escalation_reason="",
        )

    articles = retrieve_relevant_articles(message)
    category = _category(message)

    if _contains_high_risk_request(message):
        escalation_articles = [article for article in articles if article["id"] == "ART-ESC-001"]
        return ResolutionResponse(
            issue_category="Safety escalation",
            summary="This request contains a sensitive issue that requires human review.",
            recommended_resolution=[
                "Do not make commitments about account changes, refunds, or compensation.",
                "Provide a concise handoff to the appropriate human support team.",
            ],
            evidence=_evidence(escalation_articles),
            missing_information=[],
            confidence="high",
            status="ESCALATE_TO_HUMAN",
            escalation_required=True,
            escalation_reason="Sensitive or high-risk issue requiring human review.",
            handoff_summary=HandoffSummary(
                issue=message,
                established_facts=_account_facts(account),
                steps_already_tried=[],
                human_action_needed="Review the sensitive request and decide the appropriate next action.",
            ),
        )

    if not articles:
        return ResolutionResponse(
            issue_category=category,
            summary="No verified local article matches this customer issue.",
            recommended_resolution=[],
            evidence=[],
            missing_information=[],
            confidence="low",
            status="ESCALATE_TO_HUMAN",
            escalation_required=True,
            escalation_reason="Unsupported issue with no verified local guidance.",
            handoff_summary=HandoffSummary(
                issue=message,
                established_facts=_account_facts(account),
                steps_already_tried=[],
                human_action_needed="Review the unsupported issue and provide verified guidance.",
            ),
        )

    if _is_incomplete_connectivity_request(message):
        return ResolutionResponse(
            issue_category="Connectivity",
            summary="More troubleshooting detail is needed before a safe resolution can be recommended.",
            recommended_resolution=[
                "Ask when the problem started.",
                "Ask for the router light or status.",
                "Ask whether the router has been restarted.",
                "Ask whether the issue affects one device or multiple devices.",
            ],
            evidence=_evidence(articles),
            missing_information=[
                "When the problem started",
                "Router light or status",
                "Whether the router was restarted",
                "Whether one or multiple devices are affected",
            ],
            confidence="medium",
            status="MORE_INFORMATION_REQUIRED",
            escalation_required=False,
            escalation_reason="",
        )

    if (
        any(term in message.lower() for term in CONNECTIVITY_TERMS)
        and account.get("known_outage") == "local outage reported"
    ):
        return ResolutionResponse(
            issue_category="Connectivity",
            summary="The supplied account snapshot reports a local outage for this connectivity issue.",
            recommended_resolution=[
                "Use the verified outage-handling process.",
                "Do not promise a restoration time unless it is separately verified.",
            ],
            evidence=_evidence(articles),
            missing_information=[],
            confidence="high",
            status="ESCALATE_TO_HUMAN",
            escalation_required=True,
            escalation_reason="Local outage reported in the supplied account snapshot.",
            handoff_summary=HandoffSummary(
                issue=message,
                established_facts=_account_facts(account),
                steps_already_tried=[],
                human_action_needed="Confirm outage handling and provide verified customer communication.",
            ),
        )

    service = gemini_service or GeminiService()
    gemini_response = service.generate_resolution(
        customer_message=message,
        conversation_history=history,
        account_snapshot=account,
        articles=articles,
    )
    validated_response = _validated_gemini_response(gemini_response, articles)

    return validated_response or _safe_fallback(category, account, articles)
