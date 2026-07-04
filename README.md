# 🔍 PatentVerse AI

**Multi-agent patent search & prior-art analysis system**, built with **Google Agent Development Kit (ADK)** and **Gemini**.

Submitted for the *Kaggle AI Agents: Intensive Vibe Coding Capstone* — **Agents for Business** track.

---

## 1. Problem

Filing a patent without a solid prior-art search is expensive and risky. Businesses either:
- Pay $2,000–$10,000+ per search to patent attorneys / search firms, or
- Skip proper prior-art analysis and risk rejection, litigation, or wasted R&D spend.

**PatentVerse AI** automates the initial prior-art search and novelty analysis, helping users identify similar patents much faster before consulting a patent attorney.

## 2. Solution

PatentVerse AI is a **3-agent pipeline** orchestrated with Google ADK:

```
                 ┌────────────────────┐
   User Query ─▶ │   Orchestrator      │  (SequentialAgent)
                 │   Agent             │
                 └─────────┬──────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
┌───────────────┐  ┌────────────────┐  ┌────────────────┐
│ Search Agent   │─▶│ Analysis Agent │─▶│ Report Agent   │
│ (finds patents)│  │ (novelty/risk) │  │ (final writeup)│
└───────┬────────┘  └────────────────┘  └────────────────┘
        │
        ▼
┌────────────────────┐
│ Patent Search Tool  │──▶ Real API (PatentsView) OR local mock dataset (auto-fallback)
└────────────────────┘
```

- **Search Agent** — takes the invention description, generates search queries, calls the `search_patents` tool to pull candidate prior-art patents.
- **Analysis Agent** — compares the retrieved patents with the user's invention and estimates the novelty risk.
- **Report Agent** — generates a structured summary containing the retrieved patents, novelty assessment, and recommendations.

Every candidate patent returned always includes its **publication date**, and searches can optionally be restricted to a **date range** (e.g. "only patents from 2015 to 2024") via the CLI `--from`/`--to` flags, the web UI's date fields, or the `date_from`/`date_to` MCP tool parameters.

The same patent-search capability is **also exposed as an MCP server** (`mcp_server/server.py`), so it can be plugged into Claude Desktop, other MCP clients, or other agents — not locked inside this one app.

## 3. Course concepts demonstrated

| Concept | Where |
|---|---|
| Multi-agent system (ADK `SequentialAgent`) | `agents/orchestrator.py` |
| MCP Server | `mcp_server/server.py` |
| Security features | `tools/security.py` (input sanitization, rate limiting, no hardcoded secrets) |
| Deployability | `Dockerfile`, `docker-compose.yml`, Cloud Run instructions below |
| Agent skills / CLI | `cli.py` |

## 4. Project structure

```
patentverse-ai/
├── agents/
│   ├── search_agent.py       # LlmAgent: finds candidate prior art
│   ├── analysis_agent.py     # LlmAgent: novelty/risk scoring
│   ├── report_agent.py       # LlmAgent: final business report
│   └── orchestrator.py       # SequentialAgent (root_agent) wiring the 3 together
├── tools/
│   ├── patent_search.py      # search_patents() — real API + mock fallback
│   └── security.py           # input validation + rate limiter
├── mcp_server/
│   └── server.py             # Exposes patent search as an MCP tool server
├── data/
│   └── mock_patents.json     # Offline sample patent dataset
├── static/
│   └── index.html            # Minimal web demo UI
├── main.py                   # FastAPI app (web demo + REST API)
├── cli.py                    # Command-line agent runner
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml
└── tests/
    └── test_tools.py
```

## 5. Setup (VS Code / local)

```bash
# 1. Clone / open the folder in VS Code
cd patentverse-ai

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Open .env and add your GOOGLE_API_KEY (from https://aistudio.google.com/apikey)
# PATENTSVIEW_API_KEY is optional — leave blank to use the built-in mock dataset
```

### Run the CLI (fastest way to test)

```bash
python cli.py --invention "A smart water bottle that tracks hydration using a load-cell sensor and syncs to a phone app via Bluetooth"
```

Optionally restrict the prior-art search to a date range:

```bash
python cli.py --invention "..." --from 2015 --to 2024
```

### Run the web demo (FastAPI + simple UI)

```bash
python main.py
# then open http://localhost:8000 in your browser
```

### Run the MCP server (for Claude Desktop / other MCP clients)

```bash
python mcp_server/server.py
```

Add this to your MCP client config (e.g. Claude Desktop `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "patentverse": {
      "command": "python",
      "args": ["/absolute/path/to/patentverse-ai/mcp_server/server.py"]
    }
  }
}
```

### Run with the ADK dev UI (optional, great for demo video)

```bash
adk web agents/
```

## 6. Deployment (Google Cloud Run)

```bash
gcloud run deploy patentverse-ai \
  --source . \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GOOGLE_API_KEY=YOUR_KEY_HERE
```

Or with Docker locally:

```bash
docker compose up --build
```

## 7. Security notes

- No API keys are ever hardcoded — all secrets are read from environment variables (`.env`, gitignored).
- User input (invention description) is length-checked and sanitized before being passed to any tool or the LLM (`tools/security.py`).
- A simple in-memory rate limiter throttles repeated requests per session to avoid runaway API spend.
- The mock dataset lets the entire pipeline be demoed/tested with **zero external API calls or keys**.

## 8. Limitations & next steps

- Mock dataset covers a small sample of illustrative patents — production use needs a licensed patent search API (PatentsView, USPTO PatentsView, Google Patents Public Datasets on BigQuery, or a commercial provider like Derwent/PatSnap).
- Analysis is a first-pass business signal, **not legal advice** — a licensed patent attorney should always review before filing.
- Future work: add a `DraftingAgent` to help write claims, and a `MonitoringAgent` that watches for newly published competing patents.

