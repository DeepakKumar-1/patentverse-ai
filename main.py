#!/usr/bin/env python
"""
PatentVerse AI — FastAPI web app.

Serves:
- POST /api/search   -> runs the full multi-agent pipeline, returns report
- GET  /              -> minimal demo UI (static/index.html)
- GET  /health        -> health check for deployment platforms
"""

import os

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, Request  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

from agents.pipeline_runner import RateLimitedError, ValidationError, run_patent_pipeline  # noqa: E402

app = FastAPI(title="PatentVerse AI", version="1.0.0")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    # Without this, FastAPI/Starlette returns a plain-text "Internal Server
    # Error" body on unexpected crashes, which breaks the frontend's
    # res.json() call (that's the "Unexpected token 'I'..." error). This
    # guarantees the client always gets valid JSON, and prints the real
    # traceback to the terminal running `python main.py` so it's easy to
    # diagnose the root cause.
    import traceback

    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Server error: {exc.__class__.__name__}: {exc}"},
    )

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class SearchRequest(BaseModel):
    invention: str = Field(..., min_length=1, max_length=4000)
    date_from: str | None = Field(None, description='Earliest patent date, e.g. "2015" or "2015-01-01".')
    date_to: str | None = Field(None, description='Latest patent date, e.g. "2024" or "2024-12-31".')


class SearchResponse(BaseModel):
    report: str


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/api/search", response_model=SearchResponse)
async def api_search(payload: SearchRequest, request: Request):
    # Use the client's IP as a coarse per-user identity for rate limiting.
    # Good enough for a demo; swap for real auth/session ids in production.
    user_id = request.client.host if request.client else "anonymous"
    try:
        report = await run_patent_pipeline(
            payload.invention,
            user_id=user_id,
            date_from=payload.date_from,
            date_to=payload.date_to,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RateLimitedError as e:
        raise HTTPException(status_code=429, detail=str(e))
    return SearchResponse(report=report)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
