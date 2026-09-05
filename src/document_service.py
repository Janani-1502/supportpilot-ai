"""Deterministic local support-article retrieval."""

import json
import re
from pathlib import Path
from typing import Any


ARTICLES_PATH = Path(__file__).resolve().parent.parent / "data" / "support_articles.json"


def load_support_articles(path: Path = ARTICLES_PATH) -> list[dict[str, Any]]:
    """Load the local support article collection."""
    with path.open("r", encoding="utf-8") as file:
        articles = json.load(file)

    if not isinstance(articles, list):
        raise ValueError("support_articles.json must contain a JSON array.")

    return articles


def _keyword_in_message(keyword: str, message: str) -> bool:
    """Match a keyword or phrase as whole words, ignoring case."""
    pattern = r"(?<!\w)" + re.escape(keyword.lower()) + r"(?!\w)"
    return bool(re.search(pattern, message.lower()))


def retrieve_relevant_articles(message: str, limit: int = 3) -> list[dict[str, Any]]:
    """Return locally stored articles ranked by the number of matched keywords.

    Each matched keyword adds one point. A message with no matched keywords
    returns an empty list rather than an inferred answer.
    """
    if not message.strip() or limit <= 0:
        return []

    scored_articles: list[dict[str, Any]] = []
    for article in load_support_articles():
        matched_keywords = [
            keyword
            for keyword in article["keywords"]
            if _keyword_in_message(keyword, message)
        ]
        relevance_score = len(matched_keywords)

        if relevance_score:
            scored_articles.append(
                {
                    "id": article["id"],
                    "title": article["title"],
                    "keywords": article["keywords"],
                    "content": article["content"],
                    "matched_keywords": matched_keywords,
                    "relevance_score": relevance_score,
                }
            )

    return sorted(
        scored_articles,
        key=lambda article: article["relevance_score"],
        reverse=True,
    )[:limit]
