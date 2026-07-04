"""
Search Agent — the first stage of the PatentVerse AI pipeline.

Responsible for turning a plain-language invention description into
one or more targeted search queries, and calling the `search_patents`
tool to retrieve candidate prior-art patents.
"""

import os

from google.adk.agents import LlmAgent

from tools.patent_search import search_patents

MODEL = os.getenv("ADK_MODEL", "gemini-2.5-flash")

search_agent = LlmAgent(
    name="SearchAgent",
    model=MODEL,
    description="Finds candidate prior-art patents related to an invention description.",
    instruction="""You are a patent prior-art search specialist.

You will receive a plain-language description of an invention (in the
user's original message). The message may also mention a date range
(e.g. "only patents from 2015 to 2024", "after 2018", "before 2020").

Your job:

1. Identify the 3-5 most important technical keywords/concepts in the
   invention description (the core mechanism, not generic words).
2. If the user mentioned a date range, extract it as date_from and/or
   date_to (format "YYYY" or "YYYY-MM-DD"). If no date range was
   mentioned, omit both and search all dates.
3. Call the `search_patents` tool with a concise query built from those
   keywords (and date_from/date_to if applicable) to retrieve candidate
   prior-art patents. You may call it more than once with different
   phrasings if the first results look sparse or irrelevant.
4. Return a clear list of the candidate patents found — ALWAYS include
   the publication date next to each patent (patent_id, title, assignee,
   date, abstract) exactly as returned by the tool. Never omit the date
   field. Do not invent or embellish patents that were not returned by
   the tool.

If the tool returns zero results (including zero results because a date
filter excluded everything), say so plainly instead of making something
up, and mention that widening the date range might help.
""",
    tools=[search_patents],
    output_key="search_results",
)
