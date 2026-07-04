#!/usr/bin/env python
"""
PatentVerse AI — MCP server.

Exposes the patent search capability as a standard MCP tool server, so it
can be plugged into Claude Desktop, other MCP-compatible clients, or other
agent frameworks — decoupling the capability from this specific app.

Run:
    python mcp_server/server.py

Then point any MCP client at this script over stdio.
"""

import sys
from pathlib import Path

# Allow running this file directly (`python mcp_server/server.py`) by making
# the project root importable, since it sits one level above this package.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from tools.patent_search import search_patents as _search_patents  # noqa: E402
from tools.security import ValidationError, sanitize_search_query  # noqa: E402

mcp = FastMCP("patentverse-ai")


@mcp.tool()
def search_patents(
    query: str,
    limit: int = 5,
    date_from: str | None = None,
    date_to: str | None = None,
) -> dict:
    """Search for prior-art patents related to a technology or invention description.

    Args:
        query: Keywords or a short description of the invention/technology.
        limit: Maximum number of candidate patents to return (default 5, max 20).
        date_from: Optional earliest publication date to include, as
            "YYYY" or "YYYY-MM-DD" (e.g. "2015").
        date_to: Optional latest publication date to include, same format.

    Returns:
        A dict with `source` ("patentsview" or "mock") and `results`
        (a list of patent records: patent_id, title, assignee, date, abstract —
        every result includes its publication date).
    """
    try:
        sanitize_search_query(query)
    except ValidationError as e:
        return {"source": "error", "results": [], "error": str(e)}

    return _search_patents(query=query, limit=limit, date_from=date_from, date_to=date_to)


if __name__ == "__main__":
    # Runs over stdio by default, which is what most MCP desktop clients expect.
    mcp.run()
