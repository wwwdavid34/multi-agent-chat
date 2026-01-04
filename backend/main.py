"""FastAPI application exposing the /ask endpoint."""
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException, Request
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
    user_as_participant: bool | None = False  # User is participating (user-debate mode)
    tagged_panelists: list[str] | None = None  # Panelist names user tagged
    user_message: str | None = None  # User's message in user-debate
    exit_user_debate: bool | None = False  # User wants to exit user-debate


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
async def ask_stream(req: AskRequest, request: Request):
    """Streaming endpoint that provides real-time status updates."""

    async def event_stream() -> AsyncIterator[str]:
        """Generate Server-Sent Events for graph execution."""
        print(f"[EVENT_STREAM] Started for thread {req.thread_id}", flush=True)

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
            # If exiting user-debate, set flag to force consensus
            if req.exit_user_debate:
                state["consensus_reached"] = True
                state["user_as_participant"] = False
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
                "user_as_participant": req.user_as_participant or False,
                "tagged_panelists": req.tagged_panelists or [],
                "user_message": req.user_message,
            }

        # Create an event queue for streaming individual panelist responses
        import asyncio
        event_queue = asyncio.Queue()

        config = {
            "configurable": {
                "thread_id": req.thread_id,
                "panelists": [panelist.model_dump() for panelist in req.panelists]
                if req.panelists
                else None,
                "provider_keys": {k: v for k, v in (req.provider_keys or {}).items() if v},
                "event_queue": event_queue,
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
            "pause_for_review": "Paused for your review...",
        }

        try:
            if req.continue_debate:
                yield f"data: {json.dumps({'type': 'status', 'message': 'Continuing debate...'})}\n\n"
            else:
                max_rounds = req.max_debate_rounds or 3
                if req.debate_mode:
                    suffix = " (step review)" if req.step_review else ""
                    yield f"data: {json.dumps({'type': 'status', 'message': f'Starting debate (max {max_rounds} rounds){suffix}...'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Starting panel...'})}\n\n"

            # Track accumulated state across node executions
            accumulated_state = {
                "panel_responses": {},
                "summary": None,
                "debate_history": [],
                "debate_paused": False,
                "usage": None,
            }

            # Create a background task to run the graph
            graph_complete = asyncio.Event()
            print(f"[STREAM] Starting graph stream for thread {req.thread_id}", flush=True)

            async def run_graph():
                """Run the graph and process node events."""
                try:
                    async for event in panel_graph.astream(state, config=config):
                        print(f"[STREAM] Got event with nodes: {list(event.keys())}", flush=True)

                        for node_name, node_output in event.items():
                            # Send status update for each node
                            if node_name in node_status_map:
                                status_message = node_status_map[node_name]
                                await event_queue.put({
                                    "type": "status",
                                    "message": status_message,
                                })

                            # Stream search sources from search node
                            if node_name == "search" and "search_sources" in node_output:
                                search_sources = node_output["search_sources"]
                                for source in search_sources:
                                    await event_queue.put({
                                        "type": "search_source",
                                        "url": source["url"],
                                        "title": source["title"],
                                    })

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
                                    await event_queue.put({
                                        "type": "debate_round",
                                        "round": latest_round,
                                    })

                            # Capture usage accumulator from any node that returns it
                            if "usage_accumulator" in node_output:
                                accumulated_state["usage"] = node_output["usage_accumulator"]
                finally:
                    graph_complete.set()

            # Start graph execution in background
            graph_task = asyncio.create_task(run_graph())

            # Stream events from the queue as they arrive
            while not graph_complete.is_set() or not event_queue.empty():
                try:
                    # Wait for events with a timeout to check if graph is complete
                    event_data = await asyncio.wait_for(event_queue.get(), timeout=0.1)

                    # Emit the event
                    yield f"data: {json.dumps(event_data)}\n\n"

                except asyncio.TimeoutError:
                    # No event available, continue waiting
                    continue

            # Wait for graph task to complete (should already be done)
            await graph_task

            # Format usage data for response
            usage_data = None
            if accumulated_state["usage"]:
                usage_data = {
                    "total_input_tokens": accumulated_state["usage"].get("total_input", 0),
                    "total_output_tokens": accumulated_state["usage"].get("total_output", 0),
                    "total_tokens": accumulated_state["usage"].get("total_input", 0) + accumulated_state["usage"].get("total_output", 0),
                    "call_count": len(accumulated_state["usage"].get("calls", [])),
                }

            # Send the complete result with accumulated state
            # If debate is paused, send partial result without summary
            if accumulated_state["debate_paused"]:
                result_data = {
                    "type": "debate_paused",
                    "thread_id": req.thread_id,
                    "panel_responses": accumulated_state["panel_responses"],
                    "debate_history": accumulated_state["debate_history"],
                    "debate_paused": True,
                    "usage": usage_data,
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
                        "usage": usage_data,
                    }
                    yield f"data: {json.dumps(result_data)}\n\n"

            # Save usage to database
            if accumulated_state["usage"]:
                try:
                    from datetime import datetime
                    from usage_tracker import get_usage_store, RequestUsage, TokenUsage

                    store = await get_usage_store()
                    usage_raw = accumulated_state["usage"]

                    request_usage = RequestUsage(
                        thread_id=req.thread_id,
                        message_id=f"{req.thread_id}-{int(datetime.now().timestamp() * 1000)}",
                        total_input_tokens=usage_raw.get("total_input", 0),
                        total_output_tokens=usage_raw.get("total_output", 0),
                    )
                    for call in usage_raw.get("calls", []):
                        request_usage.call_details.append(TokenUsage(
                            input_tokens=call.get("input_tokens", 0),
                            output_tokens=call.get("output_tokens", 0),
                            model=call.get("model", ""),
                            provider=call.get("provider", ""),
                            node_name=call.get("node", ""),
                        ))

                    await store.save(request_usage)
                    logger.info(f"Saved usage for thread {req.thread_id}: {usage_raw.get('total_input', 0)} in, {usage_raw.get('total_output', 0)} out")
                except Exception as e:
                    logger.warning(f"Failed to save usage data: {e}")

            # Send completion event
            print(f"[EVENT_STREAM] Sending done event for thread {req.thread_id}", flush=True)
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
            print(f"[EVENT_STREAM] Completed successfully for thread {req.thread_id}", flush=True)

        except asyncio.CancelledError:
            print(f"[EVENT_STREAM] CancelledError caught for thread {req.thread_id}", flush=True)
            return

        except Exception as e:
            error_msg = str(e) or f"{type(e).__name__}: {repr(e)}"
            print(f"[EVENT_STREAM] Error: {error_msg}", flush=True)
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


@app.get("/usage/{thread_id}")
async def get_thread_usage(thread_id: str):
    """Get usage statistics for a thread."""
    from usage_tracker import get_usage_store

    store = await get_usage_store()
    usages = await store.get_by_thread(thread_id)

    total_input = sum(u.total_input_tokens for u in usages)
    total_output = sum(u.total_output_tokens for u in usages)

    return {
        "thread_id": thread_id,
        "message_count": len(usages),
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_input + total_output,
        "messages": [u.to_dict() for u in usages],
    }


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
