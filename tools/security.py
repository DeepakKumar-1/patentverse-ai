"""
Security utilities for PatentVerse AI.

Demonstrates the "Security features" course concept:
- Input sanitization / validation before anything touches an LLM or external API
- A lightweight, dependency-free rate limiter to protect API budget
- No secrets are ever read from anywhere except environment variables

None of this is meant to be enterprise-grade auth — it's the minimum
responsible-agent hygiene every submission in this track should show.
"""

from __future__ import annotations

import os
import re
import time
from collections import defaultdict, deque
from dataclasses import dataclass


MAX_INPUT_LENGTH = 4000
# Very small denylist of characters/patterns that have no business being in a
# free-text invention description and could indicate prompt-injection attempts
# against downstream tools.
_SUSPICIOUS_PATTERNS = [
    r"ignore (all|previous) instructions",
    r"system\s*prompt",
    r"<\s*script",
]


class ValidationError(ValueError):
    """Raised when user-supplied input fails validation."""


def sanitize_invention_text(text: str) -> str:
    """Validate and clean free-text invention descriptions.

    Raises ValidationError on anything unsafe or malformed instead of
    silently "fixing" it — silent coercion hides bad input from the caller.
    """
    if not text or not text.strip():
        raise ValidationError("Invention description cannot be empty.")

    text = text.strip()

    if len(text) > MAX_INPUT_LENGTH:
        raise ValidationError(
            f"Invention description too long ({len(text)} chars). "
            f"Limit is {MAX_INPUT_LENGTH} characters."
        )

    lowered = text.lower()
    for pattern in _SUSPICIOUS_PATTERNS:
        if re.search(pattern, lowered):
            raise ValidationError(
                "Input rejected: contains a disallowed instruction-like pattern."
            )

    # Strip control characters but keep normal punctuation/unicode text.
    cleaned = "".join(ch for ch in text if ch.isprintable() or ch in "\n\t")
    return cleaned


def sanitize_search_query(query: str) -> str:
    """Validate a short search-query string used against the patent tool."""
    if not query or not query.strip():
        raise ValidationError("Search query cannot be empty.")
    query = query.strip()
    if len(query) > 300:
        query = query[:300]
    return query


@dataclass
class RateLimiter:
    """A simple sliding-window rate limiter, in-memory, per session id.

    This is intentionally dependency-free so the project runs out of the
    box in VS Code without a Redis instance. For production, swap this for
    a shared store (Redis, Firestore) behind a real API gateway.
    """

    max_requests: int = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    window_seconds: int = 60

    def __post_init__(self) -> None:
        self._hits: dict[str, deque] = defaultdict(deque)

    def check(self, session_id: str) -> bool:
        """Return True if the request is allowed, False if rate-limited."""
        now = time.time()
        hits = self._hits[session_id]

        while hits and now - hits[0] > self.window_seconds:
            hits.popleft()

        if len(hits) >= self.max_requests:
            return False

        hits.append(now)
        return True


# Shared limiter instance used across the app / CLI / MCP server.
default_rate_limiter = RateLimiter()
