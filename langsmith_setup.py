"""LangSmith tracing for LangGraph (https://smith.langchain.com).

Environment (typically in .env, loaded before the graph runs):

- LANGCHAIN_TRACING_V2=true — turn tracing on
- LANGCHAIN_API_KEY — API key from LangSmith → Settings → API Keys
- LANGCHAIN_PROJECT=my-project — optional project name in the UI

Optional (e.g. EU deployment):

- LANGCHAIN_ENDPOINT=https://api.eu.smith.langchain.com

Gemini calls in utils.py are not LangChain runnables; use @traceable there for nested spans.
"""

from __future__ import annotations

import os
from typing import Any


def tracing_enabled() -> bool:
    v = os.getenv("LANGCHAIN_TRACING_V2", "").strip().lower()
    return v in ("true", "1", "yes", "on")


def langsmith_configured() -> bool:
    return bool(os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY"))


def graph_run_config(
    *,
    run_name: str | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """RunnableConfig passed to compiled LangGraph.ainvoke / .invoke."""
    meta: dict[str, Any] = {"app": "annonce-job-scraper"}
    if extra_metadata:
        meta.update(extra_metadata)
    return {
        "run_name": run_name or "annonce-scraper",
        "tags": ["annonce", "langgraph"],
        "metadata": meta,
    }


def log_tracing_status() -> None:
    """One-line hint so misconfigured .env is obvious without printing secrets."""
    if not tracing_enabled():
        print("[LangSmith] Tracing vypnutý (LANGCHAIN_TRACING_V2).", flush=True)
        return
    if not langsmith_configured():
        print(
            "[LangSmith] Tracing zapnutý, ale chybí LANGCHAIN_API_KEY (nebo LANGSMITH_API_KEY).",
            flush=True,
        )
        return
    project = os.getenv("LANGCHAIN_PROJECT", "default")
    print(f"[LangSmith] Tracing zapnutý → projekt {project!r}.", flush=True)
