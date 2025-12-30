"""FastAPI application exposing the /ask endpoint."""
import json
import logging
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from panel_graph import panel_graph
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

        state = {
            "messages": [HumanMessage(content=question_text)],
            "panel_responses": {},
            "summary": None,
            "search_results": None,
            "needs_search": False,
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
            "moderator": "Moderating the discussion...",
        }

        try:
            # Track accumulated state across node executions
            accumulated_state = {
                "panel_responses": {},
                "summary": None,
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

            # Send the complete result with accumulated state
            if accumulated_state["summary"]:
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
                    # Normal result
                    result_data = {
                        "type": "result",
                        "thread_id": req.thread_id,
                        "summary": accumulated_state["summary"],
                        "panel_responses": accumulated_state["panel_responses"],
                    }
                    yield f"data: {json.dumps(result_data)}\n\n"

            # Send completion event
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            logger.exception("Error during streaming: %s", e)
            error_data = {"type": "error", "message": str(e)}
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
