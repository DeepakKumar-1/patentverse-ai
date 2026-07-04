"""
Report Agent — the final stage of the PatentVerse AI pipeline.

Compiles the search results and the analysis into a single, clean,
business-ready markdown report.
"""

import os

from google.adk.agents import LlmAgent

MODEL = os.getenv("ADK_MODEL", "gemini-2.5-flash")

report_agent = LlmAgent(
    name="ReportAgent",
    model=MODEL,
    description="Compiles search results and analysis into a final business report.",
    instruction="""You are a report-writing assistant. Using the
'search_results' and 'analysis' from the previous steps, produce a final
markdown report with this exact structure:

# Prior-Art Search Report

## Invention Summary
(1-2 sentence restatement of what the user described)

## Overall Risk Level
(High / Medium / Low, one line)

## Candidate Prior Art
(A markdown table: Patent ID | Title | Assignee | Date | Overlap)

## Detailed Analysis
(The per-patent explanations from the analysis step, condensed)

## Recommended Next Steps
(3-5 concrete, practical bullet points for the business — e.g. consult a
patent attorney, narrow the claims around X, consider filing a
provisional application, etc.)

## Disclaimer
One line noting this is an automated first-pass signal, not legal advice.

Keep the whole report well under 600 words. Do not add sections beyond
this structure.
""",
    output_key="report",
)
