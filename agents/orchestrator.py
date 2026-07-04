"""
Orchestrator — the root agent of PatentVerse AI.

Wires SearchAgent -> AnalysisAgent -> ReportAgent into a single
SequentialAgent pipeline. This is the multi-agent system entry point
used by main.py, cli.py, and `adk web` / `adk run`.
"""

from google.adk.agents import SequentialAgent

from agents.search_agent import search_agent
from agents.analysis_agent import analysis_agent
from agents.report_agent import report_agent

root_agent = SequentialAgent(
    name="PatentVerseOrchestrator",
    description=(
        "Coordinates prior-art search, novelty analysis, and report "
        "generation for a given invention description."
    ),
    sub_agents=[search_agent, analysis_agent, report_agent],
)
