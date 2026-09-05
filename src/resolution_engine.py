from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.document_service import retrieve_relevant_articles
from src.gemini_service import GeminiService
from src.models import (
    ESCALATE_TO_HUMAN,
    MORE_INFORMATION_REQUIRED,
    READY_FOR_AGENT,
    build_response,
)


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


CONNECTIVITY_TERMS = (
    "internet",
    "wifi",
    "broadband",
    "router",
    "connection",
    "offline",
    "disconnected",
)


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
    return any(
        re.search(pattern, message, flags=re.IGNORECASE)
        for pattern in HIGH_RISK_PATTERNS
    )


def _is_incomplete_connectivity_request(message: str) -> bool:
    normalized = message.lower()

    has_connectivity_topic = any(
        term in normalized for term in CONNECTIVITY_TERMS
    )

    has_specific_detail = any(
        term in normalized for term in CONNECTIVITY_DETAIL_TERMS
    )

    return has_connectivity_topic and not has_specific_detail


def _category(message: str) -> str:
    normalized = message.lower()

    if _contains_high_risk_request(message):
        return "Safety escalation"

    if any(
        term in normalized
        for term in ("payment", "paid", "bill", "invoice")
    ):
        return "Billing and payment"

    if any(
        term in normalized
        for term in ("plan", "upgrade", "downgrade", "cancel")
    ):
        return "Plan management"

    if any(
        term in normalized
        for term in ("password", "login", "otp", "locked", "access")
    ):
        return "Account access"

    if any(term in normalized for term in CONNECTIVITY_TERMS):
        return "Connectivity"

    return "General support"


def _evidence(
    articles: list[dict[str, Any]],
) -> list[dict[str, str]]:
    return [
        {
            "article_id": article["id"],
            "title": article["title"],
            "section": "content",
        }
        for article in articles
    ]


def _account_facts(account: dict[str, Any]) -> list[str]:
    fields = (
        "id",
        "plan",
        "billing",
        "restriction",
        "known_outage",
        "verification",
    )

    return [
        f"{field}: {account[field]}"
        for field in fields
        if field in account
    ]


def _safe_fallback(
    category: str,
    account: dict[str, Any],
    articles: list[dict[str, Any]],
) -> dict[str, Any]:
    recommendations = [
        f"Follow the verified local guidance in {article['id']}: "
        f"{article['content']}"
        for article in articles
    ]

    return build_response(
        issue_category=category,
        summary=(
            "Relevant local support guidance was found "
            "for this customer message."
        ),
        recommended_resolution=recommendations,
        evidence=_evidence(articles),
        missing_information=[],
        confidence="medium",
        status=READY_FOR_AGENT,
        escalation_required=False,
        escalation_reason="",
        handoff_summary={
            "issue": category,
            "established_facts": _account_facts(account),
            "steps_already_tried": [],
            "human_action_needed": "",
        },
    )


def _validate_gemini_response(
    response: dict[str, Any] | None,
    retrieved_articles: list[dict[str, Any]],
) -> dict[str, Any] | None:

    if not isinstance(response, dict):
        return None

    required_fields = (
        "issue_category",
        "summary",
        "recommended_resolution",
        "evidence",
        "missing_information",
        "confidence",
        "status",
        "escalation_required",
        "escalation_reason",
        "handoff_summary",
    )

    if any(field not in response for field in required_fields):
        return None

    if response["status"] not in {
        READY_FOR_AGENT,
        MORE_INFORMATION_REQUIRED,
        ESCALATE_TO_HUMAN,
    }:
        return None

    retrieved_by_id = {
        article["id"]: article
        for article in retrieved_articles
    }

    for item in response["evidence"]:
        article = retrieved_by_id.get(item.get("article_id"))

        if article is None:
            return None

        if item.get("title") != article["title"]:
            return None

    return response


def _load_account(account_id: str) -> dict[str, Any] | None:
    accounts_path = (
        Path(__file__).resolve().parent.parent
        / "data"
        / "sample_accounts.json"
    )

    with accounts_path.open("r", encoding="utf-8") as file:
        accounts = json.load(file)

    return next(
        (
            item
            for item in accounts
            if item.get("id") == account_id
        ),
        None,
    )


def analyze_case(payload: dict[str, Any]) -> dict[str, Any]:
    """Analyze a customer support case safely."""

    customer_message = str(
        payload.get("customer_message", "")
    ).strip()

    account_id = str(
        payload.get("account_id", "")
    ).strip()

    conversation_history = payload.get(
        "conversation_history",
        [],
    )

    # ------------------------------------------------------------
    # 1. Customer message validation
    # ------------------------------------------------------------

    if not customer_message:
        return build_response(
            issue_category="Unknown",
            summary=(
                "A customer message is required before "
                "the issue can be assessed."
            ),
            recommended_resolution=[],
            evidence=[],
            missing_information=["Customer issue description"],
            confidence="low",
            status=MORE_INFORMATION_REQUIRED,
            escalation_required=False,
            escalation_reason="",
        )

    # ------------------------------------------------------------
    # 2. Account lookup
    # ------------------------------------------------------------

    account = _load_account(account_id)

    if not account:
        return build_response(
            issue_category="Unknown",
            summary=(
                "A valid account is required for "
                "account-specific support guidance."
            ),
            recommended_resolution=[],
            evidence=[],
            missing_information=["Verified account ID"],
            confidence="low",
            status=MORE_INFORMATION_REQUIRED,
            escalation_required=False,
            escalation_reason="",
        )

    # ------------------------------------------------------------
    # 3. Retrieve local support articles
    # ------------------------------------------------------------

    articles = retrieve_relevant_articles(customer_message)

    category = _category(customer_message)

    # ------------------------------------------------------------
    # 4. High-risk / sensitive requests
    # ------------------------------------------------------------

    if _contains_high_risk_request(customer_message):

        escalation_articles = [
            article
            for article in articles
            if article["id"] == "ART-ESC-001"
        ]

        # If normal keyword retrieval did not find the
        # escalation article, retrieve it explicitly from
        # the local support knowledge base.
        if not escalation_articles:
            escalation_candidates = retrieve_relevant_articles(
                "fraud legal complaint privacy data breach "
                "compensation emergency"
            )

            escalation_articles = [
                article
                for article in escalation_candidates
                if article["id"] == "ART-ESC-001"
            ]

        return build_response(
            issue_category="Safety escalation",
            summary=(
                "This request contains a sensitive issue "
                "that requires human review."
            ),
            recommended_resolution=[
                (
                    "Do not make commitments about account changes, "
                    "refunds, or compensation."
                ),
                (
                    "Provide a concise handoff to the appropriate "
                    "human support team."
                ),
            ],
            evidence=_evidence(escalation_articles),
            missing_information=[],
            confidence="high",
            status=ESCALATE_TO_HUMAN,
            escalation_required=True,
            escalation_reason=(
                "Sensitive or high-risk issue requiring human review."
            ),
            handoff_summary={
                "issue": customer_message,
                "established_facts": _account_facts(account),
                "steps_already_tried": [],
                "human_action_needed": (
                    "Review the sensitive request and decide "
                    "the appropriate next action."
                ),
            },
        )

    # ------------------------------------------------------------
    # 5. Unsupported issue
    # ------------------------------------------------------------

    if not articles:
        return build_response(
            issue_category=category,
            summary=(
                "No verified local article matches "
                "this customer issue."
            ),
            recommended_resolution=[],
            evidence=[],
            missing_information=[],
            confidence="low",
            status=ESCALATE_TO_HUMAN,
            escalation_required=True,
            escalation_reason=(
                "Unsupported issue with no verified local guidance."
            ),
            handoff_summary={
                "issue": customer_message,
                "established_facts": _account_facts(account),
                "steps_already_tried": [],
                "human_action_needed": (
                    "Review the unsupported issue and provide "
                    "verified guidance."
                ),
            },
        )

    # ------------------------------------------------------------
    # 6. Incomplete connectivity request
    # ------------------------------------------------------------

    if _is_incomplete_connectivity_request(customer_message):
        return build_response(
            issue_category="Connectivity",
            summary=(
                "More troubleshooting detail is needed before "
                "a safe resolution can be recommended."
            ),
            recommended_resolution=[
                "Ask when the problem started.",
                "Ask for the router light or status.",
                "Ask whether the router has been restarted.",
                (
                    "Ask whether the issue affects one device "
                    "or multiple devices."
                ),
            ],
            evidence=_evidence(articles),
            missing_information=[
                "When the problem started",
                "Router light or status",
                "Whether the router was restarted",
                "Whether one or multiple devices are affected",
            ],
            confidence="medium",
            status=MORE_INFORMATION_REQUIRED,
            escalation_required=False,
            escalation_reason="",
        )

    # ------------------------------------------------------------
    # 7. Known local outage
    # ------------------------------------------------------------

    if (
        any(
            term in customer_message.lower()
            for term in CONNECTIVITY_TERMS
        )
        and account.get("known_outage") == "local outage reported"
    ):
        return build_response(
            issue_category="Connectivity",
            summary=(
                "The supplied account snapshot reports a local "
                "outage for this connectivity issue."
            ),
            recommended_resolution=[
                "Use the verified outage-handling process.",
                (
                    "Do not promise a restoration time unless "
                    "it is separately verified."
                ),
            ],
            evidence=_evidence(articles),
            missing_information=[],
            confidence="high",
            status=ESCALATE_TO_HUMAN,
            escalation_required=True,
            escalation_reason=(
                "Local outage reported in the supplied "
                "account snapshot."
            ),
            handoff_summary={
                "issue": customer_message,
                "established_facts": _account_facts(account),
                "steps_already_tried": [],
                "human_action_needed": (
                    "Confirm outage handling and provide "
                    "verified customer communication."
                ),
            },
        )

    # ------------------------------------------------------------
    # 8. Gemini analysis
    # ------------------------------------------------------------

    service = GeminiService()

    gemini_response = service.generate_resolution(
        customer_message=customer_message,
        conversation_history=(
            conversation_history
            if isinstance(conversation_history, list)
            else []
        ),
        account_snapshot=account,
        articles=articles,
    )

    # ------------------------------------------------------------
    # 9. Validate Gemini output
    # ------------------------------------------------------------

    validated_response = _validate_gemini_response(
        gemini_response,
        articles,
    )

    # ------------------------------------------------------------
    # 10. Safe local fallback
    # ------------------------------------------------------------

    return validated_response or _safe_fallback(
        category,
        account,
        articles,
    )