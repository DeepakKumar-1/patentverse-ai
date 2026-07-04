"""
Shared helper that wraps the ADK Runner + InMemorySessionService so both
the CLI and the FastAPI web app can invoke the PatentVerse pipeline the
same way, without duplicating boilerplate.
"""

from __future__ import annotations

import uuid

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from agents.orchestrator import root_agent
from tools.security import ValidationError, default_rate_limiter, sanitize_invention_text

APP_NAME = "patentverse_ai"

# A single shared session service so state persists across calls within
# one process run (not required for a one-shot CLI call, but keeps the
# same pattern the FastAPI app needs for multi-request handling).
_session_service = InMemorySessionService()
_runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=_session_service)


class RateLimitedError(RuntimeError):
    """Raised when a caller exceeds the configured rate limit."""


async def run_patent_pipeline(
    invention_text: str,
    user_id: str = "local_user",
    date_from: str | None = None,
    date_to: str | None = None,
) -> str:
    """Run the full Search -> Analysis -> Report pipeline for one invention
    description and return the final report text.

    Each call gets its own fresh session, since a prior-art search is a
    one-shot task rather than an ongoing conversation.

    Args:
        invention_text: Plain-language invention description.
        user_id: Session/rate-limit identity.
        date_from: Optional earliest patent publication date ("YYYY" or
            "YYYY-MM-DD") to restrict the search to.
        date_to: Optional latest patent publication date, same format.
    """
    if not default_rate_limiter.check(user_id):
        raise RateLimitedError(
            "Rate limit exceeded — please wait a moment before trying again."
        )

    clean_text = sanitize_invention_text(invention_text)  # raises ValidationError on bad input

    # The date range is folded into the message text (rather than passed as
    # a separate structured field) because SearchAgent is an LlmAgent that
    # parses the date range out of natural language per its instructions —
    # this keeps the tool-calling contract simple and lets users also just
    # type "...patents from 2015 to 2020" directly if they prefer.
    if date_from or date_to:
        range_note = f"\n\n[Date range filter: from {date_from or 'any'} to {date_to or 'any'}]"
        clean_text = f"{clean_text}{range_note}"

    session_id = str(uuid.uuid4())
    await _session_service.create_session(
        app_name=APP_NAME, user_id=user_id, session_id=session_id
    )

    user_message = types.Content(role="user", parts=[types.Part(text=clean_text)])

    final_text = ""
    async for event in _runner.run_async(
        user_id=user_id, session_id=session_id, new_message=user_message
    ):
        if getattr(event, "content", None) and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    final_text = part.text  # keep the latest — report agent runs last

    return final_text or "No report was generated. Please try rephrasing your invention description."


__all__ = ["run_patent_pipeline", "RateLimitedError", "ValidationError"]
