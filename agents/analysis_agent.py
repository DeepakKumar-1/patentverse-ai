"""
Analysis Agent — the second stage of the PatentVerse AI pipeline.

Takes the candidate patents found by SearchAgent (available in session
state under `search_results`) and scores each one for novelty/overlap
risk against the user's original invention description.
"""

import os

from google.adk.agents import LlmAgent

MODEL = os.getenv("ADK_MODEL", "gemini-2.5-flash")

analysis_agent = LlmAgent(
    name="AnalysisAgent",
    model=MODEL,
    description="Assesses novelty/overlap risk of candidate prior-art patents.",
    instruction="""You are a patent analysis assistant helping a business
(not a lawyer) understand their prior-art risk.

You have access to the candidate patents found in 'search_results' from
the previous step, and the user's original invention description in the
conversation.

For EACH candidate patent, produce:
- Overlap score: High / Medium / Low
- 1-2 sentence explanation of what specifically overlaps or differs
  between the invention and that patent

Then give an OVERALL assessment:
- Overall risk level: High / Medium / Low
- The single closest prior-art patent (name it) and why it's the closest
- What appears to be genuinely novel about the user's invention, if
  anything

Be direct and business-plain — no legal jargon, no hedging disclaimers
beyond a single closing line reminding them this isn't legal advice.
Never claim certainty about legal patentability — you are giving a
first-pass signal only.
""",
    output_key="analysis",
)
