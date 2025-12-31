"""FastAPI application exposing the /ask endpoint."""
import json
import logging
import os
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from panel_graph import panel_graph, get_storage_mode
from provider_clients import ProviderName, fetch_provider_models

app = FastAPI(title="AI Discussion Panel")

logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PanelistConfig(BaseModel):
    id: str
    name: str
    provider: str
    model: str


class AskRequest(BaseModel):
    thread_id: str
    question: str
    attachments: list[str] | None = None
    panelists: list[PanelistConfig] | None = None
    provider_keys: dict[str, str] | None = None
    debate_mode: bool | None = False
    max_debate_rounds: int | None = 3
    step_review: bool | None = False
    continue_debate: bool | None = False  # Whether this is continuing a paused debate


class AskResponse(BaseModel):
    thread_id: str
    summary: str
    panel_responses: dict[str, str]


class ProviderModel(BaseModel):
    id: str
    label: str


class ProviderKeyRequest(BaseModel):
    api_key: str


class ProviderModelsResponse(BaseModel):
    models: list[ProviderModel]


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    attachments = req.attachments or []
    attachment_md = "\n".join(
        f"![user attachment {idx + 1}]({url})" for idx, url in enumerate(attachments)
    )
    question_text = req.question.strip() or "See attached images."
    if attachment_md:
        question_text = f"{question_text}\n\nAttached images:\n{attachment_md}"

    state = {
        "messages": [HumanMessage(content=question_text)],
        "panel_responses": {},
        "summary": None,
        "debate_mode": req.debate_mode or False,
        "max_debate_rounds": req.max_debate_rounds or 3,
        "debate_round": 0,
        "consensus_reached": False,
        "debate_history": [],
    }

    config = {
        "configurable": {
            "thread_id": req.thread_id,
            "panelists": [panelist.model_dump() for panelist in req.panelists]
            if req.panelists
            else None,
            "provider_keys": {k: v for k, v in (req.provider_keys or {}).items() if v},
        }
    }
    result = await panel_graph.ainvoke(state, config=config)

    return AskResponse(
        thread_id=req.thread_id,
        summary=result["summary"],
        panel_responses=result["panel_responses"],
    )


@app.post("/ask-stream")
async def ask_stream(req: AskRequest):
    """Streaming endpoint that provides real-time status updates."""

    async def event_stream() -> AsyncIterator[str]:
        """Generate Server-Sent Events for graph execution."""

        attachments = req.attachments or []
        attachment_md = "\n".join(
            f"![user attachment {idx + 1}]({url})" for idx, url in enumerate(attachments)
        )
        question_text = req.question.strip() or "See attached images."
        if attachment_md:
            question_text = f"{question_text}\n\nAttached images:\n{attachment_md}"

        # If continuing a debate, provide empty state to resume from checkpoint
        if req.continue_debate:
            state = {}  # Empty state tells LangGraph to resume from checkpoint
            logger.info(f"Continuing debate for thread {req.thread_id}")
        else:
            state = {
                "messages": [HumanMessage(content=question_text)],
                "panel_responses": {},
                "summary": None,
                "search_results": None,
                "needs_search": False,
                "debate_mode": req.debate_mode or False,
                "max_debate_rounds": req.max_debate_rounds or 3,
                "debate_round": 0,
                "consensus_reached": False,
                "debate_history": [],
                "step_review": req.step_review or False,
                "debate_paused": False,
            }

        config = {
            "configurable": {
                "thread_id": req.thread_id,
                "panelists": [panelist.model_dump() for panelist in req.panelists]
                if req.panelists
                else None,
                "provider_keys": {k: v for k, v in (req.provider_keys or {}).items() if v},
            }
        }

        # Map node names to user-friendly status messages
        node_status_map = {
            "summarize_conversation": "Summarizing conversation history...",
            "moderator_search_decision": "Moderator is analyzing the question...",
            "search": "Searching the web...",
            "panelists": "Panel is discussing...",
            "consensus_checker": "Evaluating consensus...",
            "moderator": "Moderating the discussion...",
        }

        try:
            # Track accumulated state across node executions
            accumulated_state = {
                "panel_responses": {},
                "summary": None,
                "debate_history": [],
                "debate_paused": False,
            }

            # Stream events from the graph
            async for event in panel_graph.astream(state, config=config):
                for node_name, node_output in event.items():
                    # Send status update for each node
                    if node_name in node_status_map:
                        status_message = node_status_map[node_name]
                        yield f"data: {json.dumps({'type': 'status', 'message': status_message})}\n\n"

                    # Accumulate panel_responses from panelists node
                    if node_name == "panelists" and "panel_responses" in node_output:
                        accumulated_state["panel_responses"].update(node_output["panel_responses"])

                    # Get summary from moderator node
                    if node_name == "moderator" and "summary" in node_output:
                        accumulated_state["summary"] = node_output["summary"]

                    # Track if debate is paused for user review
                    if node_name == "pause_for_review":
                        accumulated_state["debate_paused"] = node_output.get("debate_paused", False)
                        logger.info("Debate paused - waiting for user to continue")

                    # Emit debate round events when consensus_checker completes
                    if node_name == "consensus_checker" and "debate_history" in node_output:
                        accumulated_state["debate_history"] = node_output["debate_history"]
                        # Send the latest debate round to the frontend
                        if node_output["debate_history"]:
                            latest_round = node_output["debate_history"][-1]
                            debate_round_event = {
                                "type": "debate_round",
                                "round": latest_round,
                            }
                            yield f"data: {json.dumps(debate_round_event)}\n\n"

            # Send the complete result with accumulated state
            # If debate is paused, send partial result without summary
            if accumulated_state["debate_paused"]:
                result_data = {
                    "type": "debate_paused",
                    "thread_id": req.thread_id,
                    "panel_responses": accumulated_state["panel_responses"],
                    "debate_history": accumulated_state["debate_history"],
                    "debate_paused": True,
                }
                yield f"data: {json.dumps(result_data)}\n\n"
            elif accumulated_state["summary"]:
                # Check if the summary indicates an error condition
                summary_lower = accumulated_state["summary"].lower()
                is_error_response = any(
                    phrase in summary_lower
                    for phrase in [
                        "rate limiting",
                        "rate limit",
                        "context length limitations",
                        "unable to generate summary",
                        "cannot process this request",
                    ]
                )

                if is_error_response:
                    # Send as error event instead of result
                    error_data = {"type": "error", "message": accumulated_state["summary"]}
                    yield f"data: {json.dumps(error_data)}\n\n"
                else:
                    # Normal result - debate complete
                    result_data = {
                        "type": "result",
                        "thread_id": req.thread_id,
                        "summary": accumulated_state["summary"],
                        "panel_responses": accumulated_state["panel_responses"],
                        "debate_history": accumulated_state["debate_history"],
                        "debate_paused": False,
                    }
                    yield f"data: {json.dumps(result_data)}\n\n"

            # Send completion event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            error_msg = str(e) or f"{type(e).__name__}: {repr(e)}"
            logger.exception("Error during streaming: %s", error_msg)
            error_data = {"type": "error", "message": error_msg}
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )


@app.post("/providers/{provider}/models", response_model=ProviderModelsResponse)
async def get_provider_models(provider: ProviderName, payload: ProviderKeyRequest) -> ProviderModelsResponse:
    api_key = payload.api_key.strip()
    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required")

    try:
        models = await fetch_provider_models(provider, api_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - network issues
        logger.exception("Failed to fetch models for provider %s", provider.value)
        raise HTTPException(status_code=502, detail="Failed to load models") from exc

    payload_models = [ProviderModel(**model) for model in models]
    return ProviderModelsResponse(models=payload_models)


@app.get("/initial-keys")
async def get_initial_keys() -> dict[str, str]:
    """Return API keys from environment variables for prefilling the UI.

    Keys are read from environment variables and returned to the frontend
    to prefill the configuration panel. This allows users to configure
    API keys via .env file instead of manually entering them.
    """
    return {
        "openai": os.getenv("OPENAI_API_KEY", ""),
        "gemini": os.getenv("GEMINI_API_KEY", ""),
        "claude": os.getenv("CLAUDE_API_KEY", ""),
        "grok": os.getenv("GROK_API_KEY", ""),
    }


@app.get("/storage-info")
async def get_storage_info() -> dict[str, str]:
    """Return information about the current storage mode.

    Returns whether the app is using in-memory storage (ephemeral) or
    PostgreSQL database (persistent). This helps users understand if their
    conversations will persist across restarts.
    """
    return get_storage_mode()


# Serve static frontend files (built by Vite)
frontend_dist = Path(__file__).parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")
    logger.info("Serving static frontend from %s", frontend_dist)
else:
    logger.warning("Frontend dist directory not found at %s", frontend_dist)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
