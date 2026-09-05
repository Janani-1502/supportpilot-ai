from __future__ import annotations

import json
import os
from typing import Any

from google import genai
from google.genai import types
from pydantic import ValidationError

from src.models import ResolutionResponse


SYSTEM_INSTRUCTIONS = """
You are SupportPilot AI, a customer-support resolution assistant.

Use only the customer message, conversation history, account snapshot, and
retrieved local support articles supplied in this request. Do not invent account
facts, payment status, outages, evidence, refunds, plan changes, tickets,
technician visits, or any other action.

Return only a structured ResolutionResponse. Cite only supplied article IDs in
evidence. Recommendations must describe actions for a support agent; never
claim to perform a real-world action. If the supplied information cannot support
a safe answer, use MORE_INFORMATION_REQUIRED or ESCALATE_TO_HUMAN.
""".strip()


class GeminiService:
    """Safe, optional Gemini structured-output client."""

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    def generate_resolution(
        self,
        *,
        customer_message: str,
        conversation_history: list[dict[str, str]],
        account_snapshot: dict[str, Any],
        articles: list[dict[str, Any]],
    ) -> ResolutionResponse | None:
        """Return validated Gemini output, or None on any safe fallback path."""
        if not self.api_key:
            return None

        request_data = {
            "customer_message": customer_message,
            "conversation_history": conversation_history,
            "account_snapshot": account_snapshot,
            "retrieved_support_articles": articles,
        }

        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=self.model_name,
                contents=json.dumps(request_data),
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTIONS,
                    response_mime_type="application/json",
                    response_schema=ResolutionResponse,
                    temperature=0.1,
                ),
            )

            if isinstance(response.parsed, ResolutionResponse):
                return response.parsed

            if response.text:
                return ResolutionResponse.model_validate_json(response.text)
        except (Exception, ValidationError):
            return None

        return None
