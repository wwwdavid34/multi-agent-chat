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
from config import get_frontend_url, is_auth_enabled
from routers import auth
from decision.graph import build_decision_graph

# Initialize logger early so it's available in all functions
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Discussion Panel")

# Configure CORS — specific origins only (wildcard blocks credentialed requests)
frontend_url = get_frontend_url()
cors_origins = [frontend_url]
# Add localhost variants for dev convenience
for port in ("5173", "5174", "3000"):
    for scheme in ("http",):
        origin = f"{scheme}://localhost:{port}"
        if origin not in cors_origins:
            cors_origins.append(origin)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication router
app.include_router(auth.router)


@app.on_event("startup")
async def startup_event():
    """Log startup information."""
    try:
        storage_mode = get_storage_mode()

        logger.info("=" * 80)
        logger.info("DEBATE ENGINE: LangGraph")
        logger.info("=" * 80)
        logger.info(f"Storage mode: {storage_mode}")

        # Log authentication status
        if is_auth_enabled():
            logger.info("AUTHENTICATION: Enabled (Google OAuth + JWT)")
        else:
            logger.info("AUTHENTICATION: Disabled (missing env variables)")
            logger.info("   See GOOGLE_OAUTH_SETUP.md for setup instructions")

        logger.info("=" * 80)
    except Exception as e:
        logger.error(f"Error during startup: {e}", exc_info=True)


class PanelistConfig(BaseModel):
    id: str
    name: str
    provider: str
    model: str
    role: str | None = None  # PRO, CON, DEVIL_ADVOCATE


class AskRequest(BaseModel):
    thread_id: str
    question: str
    attachments: list[str] | None = None
    panelists: list[PanelistConfig] | None = None
    provider_keys: dict[str, str] | None = None
    # Debate mode: "autonomous" | "supervised" | "participatory" | None (no debate)
    # - autonomous: runs without pauses until consensus or max_rounds
    # - supervised: pauses each round for user to review/vote
    # - participatory: pauses each round for user input
    debate_mode: str | None = None
    max_debate_rounds: int | None = 3
    continue_debate: bool | None = False  # Whether this is continuing a paused debate
    tagged_panelists: list[str] | None = None  # @mentioned panelist names
    user_message: str | None = None  # User's message to inject (participatory mode)
    exit_debate: bool | None = False  # User wants to end the debate early
    # Adversarial role assignment
    stance_mode: str | None = "free"  # "free", "adversarial", or "assigned"
    assigned_roles: dict[str, dict] | None = None  # panelist_name -> role assignment
    # Preset mode custom personas (for Business Validation, etc.)
    preset_personas: dict[str, str] | None = None  # panelist_name -> custom persona text
    # Custom moderator prompt for report consolidation
    moderator_prompt: str | None = None


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


class GenerateTitleRequest(BaseModel):
    first_message: str


class GenerateTitleResponse(BaseModel):
    title: str
    usage: dict[str, int] | None = None


class DecisionRequest(BaseModel):
    thread_id: str
    question: str
    constraints: dict | None = None
    max_iterations: int = 2
    resume: bool = False
    human_feedback: dict | None = None


@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring."""
    from datetime import datetime

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "0.6.0",
    }


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    attachments = req.attachments or []
    attachment_md = "\n".join(
        f"![user attachment {idx + 1}]({url})" for idx, url in enumerate(attachments)
    )
    question_text = req.question.strip() or "See attached images."
    if attachment_md:
        question_text = f"{question_text}\n\nAttached images:\n{attachment_md}"

    # Convert new debate_mode to legacy format for LangGraph
    is_debate = req.debate_mode is not None
    state = {
        "messages": [HumanMessage(content=question_text)],
        "panel_responses": {},
        "summary": None,
        "debate_mode": is_debate,
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
    logger.info(f"[DEBATE] LangGraph backend for thread: {req.thread_id}")
    logger.info(f"   Question: {req.question[:80]}{'...' if len(req.question) > 80 else ''}")
    logger.info(f"   Mode: {req.debate_mode or 'panel'} | Rounds: {req.max_debate_rounds}")
    return await _handle_langgraph_debate(req)


async def _handle_langgraph_debate(req: AskRequest) -> StreamingResponse:
    """Handle debate using LangGraph backend (existing implementation)."""
    logger.info(f"🟢 [LANGGRAPH] Initializing LangGraph service for thread {req.thread_id}")

    async def event_stream() -> AsyncIterator[str]:
        """Generate Server-Sent Events for graph execution."""
        print(f"[EVENT_STREAM] Started for thread {req.thread_id}", flush=True)
        logger.info(f"🟢 [LANGGRAPH] Event stream started for thread {req.thread_id}")

        attachments = req.attachments or []
        attachment_md = "\n".join(
            f"![user attachment {idx + 1}]({url})" for idx, url in enumerate(attachments)
        )
        question_text = req.question.strip() or "See attached images."
        if attachment_md:
            question_text = f"{question_text}\n\nAttached images:\n{attachment_md}"

        # Convert new debate_mode to legacy flags for LangGraph compatibility
        # debate_mode: "autonomous" | "supervised" | "participatory" | None
        is_debate = req.debate_mode is not None
        is_supervised = req.debate_mode in ("supervised", "participatory")
        is_participatory = req.debate_mode == "participatory"

        # If continuing a debate, provide empty state to resume from checkpoint
        if req.continue_debate:
            state = {}  # Empty state tells LangGraph to resume from checkpoint
            logger.info(f"Continuing debate for thread {req.thread_id}")
            # If exiting debate, set flag to force consensus
            if req.exit_debate:
                state["consensus_reached"] = True
        else:
            state = {
                "messages": [HumanMessage(content=question_text)],
                "panel_responses": {},
                "summary": None,
                "search_results": None,
                "needs_search": False,
                "debate_mode": is_debate,
                "max_debate_rounds": req.max_debate_rounds or 3,
                "debate_round": 0,
                "consensus_reached": False,
                "debate_history": [],
                "step_review": is_supervised,
                "debate_paused": False,
                "user_as_participant": is_participatory,
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
                    mode_label = f" ({req.debate_mode})" if req.debate_mode != "autonomous" else ""
                    yield f"data: {json.dumps({'type': 'status', 'message': f'Starting debate (max {max_rounds} rounds){mode_label}...'})}\n\n"
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


@app.post("/generate-title", response_model=GenerateTitleResponse)
async def generate_title(req: GenerateTitleRequest) -> GenerateTitleResponse:
    """Generate a conversation title from the first user message.

    Uses the moderator model (GPT-4o) to create a concise, descriptive title
    that captures the main topic of the conversation.
    """
    from panel_graph import _get_moderator_model
    from usage_tracker import create_usage_accumulator, add_to_accumulator
    from langchain_core.messages import HumanMessage

    # Limit message length for title generation (first 500 chars)
    truncated_message = req.first_message[:500]

    title_prompt = f"""Generate a concise, descriptive title (max 35 characters) for a conversation that starts with:

"{truncated_message}"

Requirements:
- Be specific and capture the main topic
- Use title case
- No quotes or special characters around the title
- Max 35 characters
- Be direct and clear
- If you can't fit the idea, use abbreviations

Title:"""

    try:
        moderator_model = _get_moderator_model()
        response = await moderator_model.ainvoke([HumanMessage(content=title_prompt)])
        title = response.content.strip()

        # Ensure title length constraint (35 chars max)
        if len(title) > 35:
            title = title[:32] + "..."

        # Track usage
        usage_acc = create_usage_accumulator()
        add_to_accumulator(usage_acc, response, model="gpt-4o", provider="openai", node_name="title_generation")

        return GenerateTitleResponse(
            title=title,
            usage={
                "input_tokens": usage_acc.get("total_input", 0),
                "output_tokens": usage_acc.get("total_output", 0),
            }
        )
    except Exception as e:
        logger.exception("Failed to generate title")
        # Fallback to truncated message if generation fails
        fallback_title = truncated_message[:47] + "..." if len(truncated_message) > 50 else truncated_message
        return GenerateTitleResponse(title=fallback_title, usage=None)


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


@app.post("/decision-stream")
async def decision_stream(req: DecisionRequest, request: Request):
    """Stream a decision assistant session via SSE."""
    async def event_generator():
        try:
            graph = build_decision_graph()
            config = {"configurable": {"thread_id": req.thread_id}}

            if req.resume and req.human_feedback:
                from langgraph.types import Command
                stream = graph.astream(
                    Command(resume=req.human_feedback),
                    config,
                    stream_mode="updates",
                )
            else:
                initial_state = {
                    "user_question": req.question,
                    "constraints": req.constraints or {},
                    "iteration": 0,
                    "max_iterations": req.max_iterations,
                    "phase": "planning",
                    "expert_outputs": {},
                }
                stream = graph.astream(
                    initial_state,
                    config,
                    stream_mode="updates",
                )

            async for event in stream:
                for node_name, node_output in event.items():
                    if node_name == "__interrupt__":
                        yield f"data: {json.dumps({'type': 'awaiting_input', 'data': node_output})}\n\n"
                        continue

                    if node_name == "planner":
                        yield f"data: {json.dumps({'type': 'phase_update', 'phase': 'planning'})}\n\n"
                        yield f"data: {json.dumps({'type': 'options_identified', 'options': node_output.get('decision_options', []), 'expert_tasks': node_output.get('expert_tasks', [])})}\n\n"
                    elif node_name == "run_expert":
                        outputs = node_output.get("expert_outputs", {})
                        for role, output in outputs.items():
                            yield f"data: {json.dumps({'type': 'expert_complete', 'expert_role': role, 'output': output}, default=str)}\n\n"
                    elif node_name == "conflict_detector":
                        yield f"data: {json.dumps({'type': 'phase_update', 'phase': 'conflict'})}\n\n"
                        yield f"data: {json.dumps({'type': 'conflicts_detected', 'conflicts': node_output.get('conflicts', []), 'open_questions': node_output.get('open_questions', [])}, default=str)}\n\n"
                    elif node_name == "human_gate":
                        yield f"data: {json.dumps({'type': 'phase_update', 'phase': 'human'})}\n\n"
                    elif node_name == "synthesizer":
                        yield f"data: {json.dumps({'type': 'phase_update', 'phase': 'synthesis'})}\n\n"
                        yield f"data: {json.dumps({'type': 'recommendation', 'recommendation': node_output.get('recommendation', {})}, default=str)}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except Exception as e:
            logger.error("Decision stream error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


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
