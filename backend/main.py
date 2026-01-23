"""FastAPI application exposing the /ask endpoint."""
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import AsyncIterator, Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.messages import HumanMessage
from pydantic import BaseModel

from auth.dependencies import get_current_user_optional
from auth.models import TokenPayload
from auth.provider_keys import resolve_provider_keys
from routers.auth import get_db

from panel_graph import panel_graph, get_storage_mode
from provider_clients import ProviderName, fetch_provider_models, check_provider_quota, QuotaStatus
from config import get_debate_engine, get_pg_conn_str, use_in_memory_checkpointer, get_frontend_url, is_auth_enabled
from routers import auth, admin, conversations

# Initialize logger early so it's available in all functions
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Discussion Panel")

# Initialize AG2 debate service (if enabled)
_ag2_service = None


async def get_ag2_service():
    """Lazy initialize AG2 debate service."""
    global _ag2_service
    if _ag2_service is None:
        try:
            from debate.service import AG2DebateService
            from debate.persistence import PostgresDebateStorage, InMemoryDebateStorage

            # Use in-memory storage if configured, otherwise use PostgreSQL
            if use_in_memory_checkpointer():
                storage = InMemoryDebateStorage()
                logger.info("🟦 [AG2-SERVICE] Initialized with IN-MEMORY storage")
            else:
                conn_str = get_pg_conn_str()
                storage = PostgresDebateStorage(conn_str)
                logger.info("🟦 [AG2-SERVICE] Initialized with PostgreSQL storage")

            _ag2_service = AG2DebateService(storage)
            logger.info("🟦 [AG2-SERVICE] AG2 debate service ready")
        except Exception as e:
            logger.error(f"🟥 [AG2-SERVICE] Failed to initialize: {e}", exc_info=True)
            raise

    return _ag2_service

# Configure CORS
# Note: In production, restrict to specific origins for security
frontend_url = get_frontend_url()
# Parse frontend_url which may contain comma-separated origins
cors_origins = [url.strip() for url in frontend_url.split(",") if url.strip()]
# Add common Cloudflare Pages patterns
cors_origins.extend([
    "https://multi-agent-chat.pages.dev",
    "http://localhost:5173",
    "http://localhost:3000",
])
# Remove duplicates while preserving order
cors_origins = list(dict.fromkeys(cors_origins))
logger.info(f"CORS allowed origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include authentication router
app.include_router(auth.router)

# Include admin router
app.include_router(admin.router)

# Include conversations router
app.include_router(conversations.router)


@app.on_event("startup")
async def startup_event():
    """Log startup information including debate engine selection."""
    try:
        engine = get_debate_engine()
        storage_mode = get_storage_mode()

        if engine == "ag2":
            logger.info("=" * 80)
            logger.info("🔵 DEBATE ENGINE: AG2 (New Backend)")
            logger.info("=" * 80)
            logger.info("✓ AG2 backend is ENABLED")
            logger.info("✓ Using feature-flag based routing")
            logger.info("✓ Lazy initialization on first request")
        else:
            logger.info("=" * 80)
            logger.info("🟢 DEBATE ENGINE: LangGraph (Legacy Backend)")
            logger.info("=" * 80)
            logger.info("✓ LangGraph backend is ACTIVE (default)")
            logger.info(f"✓ Storage mode: {storage_mode}")

        # Log authentication status
        if is_auth_enabled():
            logger.info("🔐 AUTHENTICATION: Enabled (Google OAuth + JWT)")
        else:
            logger.info("⚠️  AUTHENTICATION: Disabled (missing env variables)")
            logger.info("   See GOOGLE_OAUTH_SETUP.md for setup instructions")

        logger.info("=" * 80)
    except Exception as e:
        logger.error(f"🟥 Error during startup: {e}", exc_info=True)


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
    # NOTE: Default is None so the debate service can pick a sensible default
    # (e.g., "adversarial" for debates, "free" for panel-only).
    stance_mode: str | None = None  # "free", "adversarial", or "assigned"
    assigned_roles: dict[str, dict] | None = None  # panelist_name -> role assignment


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
async def ask(
    req: AskRequest,
    user: Optional[TokenPayload] = Depends(get_current_user_optional),
    pool = Depends(get_db),
) -> AskResponse:
    """Non-streaming endpoint for panel discussions.

    Supports optional authentication for BYOK enforcement.
    """
    # Extract required providers from panelists
    required_providers = set()
    if req.panelists:
        for p in req.panelists:
            required_providers.add(p.provider.lower())

    # Resolve provider keys with BYOK enforcement
    try:
        resolved_keys = await resolve_provider_keys(
            request_keys=req.provider_keys,
            user=user,
            pool=pool,
            required_providers=required_providers if required_providers else None,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
            "provider_keys": {k: v for k, v in resolved_keys.items() if v},
        }
    }
    result = await panel_graph.ainvoke(state, config=config)

    return AskResponse(
        thread_id=req.thread_id,
        summary=result["summary"],
        panel_responses=result["panel_responses"],
    )


@app.post("/ask-stream")
async def ask_stream(
    req: AskRequest,
    request: Request,
    user: TokenPayload | None = Depends(get_current_user_optional),
    pool = Depends(get_db),
):
    """Streaming endpoint that provides real-time status updates.

    Supports optional authentication. When authenticated:
    - User's stored keys are loaded
    - System keys are available if user is allowlisted

    When not authenticated:
    - Only keys provided in request (BYOK) are used
    """
    # Extract required providers from panelists
    required_providers = set()
    if req.panelists:
        for p in req.panelists:
            required_providers.add(p.provider.lower())

    # Resolve provider keys with BYOK enforcement
    try:
        resolved_keys = await resolve_provider_keys(
            request_keys=req.provider_keys,
            user=user,
            pool=pool,
            required_providers=required_providers if required_providers else None,
        )
        # Replace request keys with resolved keys
        req.provider_keys = resolved_keys
    except ValueError as e:
        # Missing required keys - return error as SSE
        # Capture error message before defining nested function (Python closure issue)
        error_msg = str(e)
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'message': error_msg})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )

    # Log which key sources were used
    if user:
        logger.info(f"🔑 [AUTH] Authenticated user: {user.email}")
    else:
        logger.info("🔑 [AUTH] Anonymous request - using BYOK only")

    # Check feature flag for debate engine selection
    debate_engine = get_debate_engine()

    if debate_engine == "ag2":
        # Use new AG2-based backend
        logger.info("=" * 80)
        logger.info(f"🔵 [DEBATE] Using AG2 backend for thread: {req.thread_id}")
        logger.info(f"   Question: {req.question[:80]}{'...' if len(req.question) > 80 else ''}")
        logger.info(f"   Mode: {req.debate_mode or 'panel'} | Rounds: {req.max_debate_rounds}")
        logger.info("=" * 80)
        return await _handle_ag2_debate(req)
    else:
        # Use existing LangGraph backend
        logger.info("=" * 80)
        logger.info(f"🟢 [DEBATE] Using LangGraph backend for thread: {req.thread_id}")
        logger.info(f"   Question: {req.question[:80]}{'...' if len(req.question) > 80 else ''}")
        logger.info(f"   Mode: {req.debate_mode or 'panel'} | Rounds: {req.max_debate_rounds}")
        logger.info("=" * 80)
        return await _handle_langgraph_debate(req)


async def _handle_ag2_debate(req: AskRequest) -> StreamingResponse:
    """Handle debate using AG2 backend."""
    try:
        logger.info(f"🔵 [AG2] Initializing AG2 debate service for thread {req.thread_id}")
        service = await get_ag2_service()
        logger.info(f"🔵 [AG2] Service initialized, starting event stream for thread {req.thread_id}")

        async def ag2_event_stream() -> AsyncIterator[str]:
            """Stream events from AG2 debate service."""
            try:
                # Determine if this is a resume or start
                if req.continue_debate:
                    logger.info(f"Resuming AG2 debate for thread {req.thread_id}")
                    event_iter = service.resume_debate(
                        thread_id=req.thread_id,
                        user_message=req.user_message,
                    )
                else:
                    logger.info(f"Starting AG2 debate for thread {req.thread_id}")
                    # debate_mode: "autonomous" | "supervised" | "participatory" | None
                    event_iter = service.start_debate(
                        thread_id=req.thread_id,
                        question=req.question,
                        panelists=[p.model_dump() for p in req.panelists] if req.panelists else [],
                        provider_keys=req.provider_keys or {},
                        debate_mode=req.debate_mode or "autonomous",
                        max_debate_rounds=req.max_debate_rounds or 3,
                        tagged_panelists=req.tagged_panelists or [],
                        # Adversarial role assignment
                        # Pass through None so backend can default to adversarial for debates.
                        stance_mode=req.stance_mode,
                        assigned_roles=req.assigned_roles,
                    )

                # Stream events from service as SSE
                event_count = 0
                async for event in event_iter:
                    event_count += 1
                    event_type = event.get("type", "unknown")

                    # Log event with visual indicator
                    if event_type == "status":
                        logger.debug(f"🔵 [AG2-EVENT] Status: {event.get('message', '')}")
                    elif event_type == "panelist_response":
                        panelist = event.get("panelist", "Unknown")
                        logger.debug(f"🔵 [AG2-EVENT] {panelist} responded ({len(event.get('response', '')) // 10} words)")
                    elif event_type == "debate_round":
                        round_num = event.get("round", {}).get("round_number", "?")
                        logger.info(f"🔵 [AG2-EVENT] Debate round {round_num} complete")
                    elif event_type == "result":
                        logger.info(f"🔵 [AG2-EVENT] Debate complete - Final result received")
                    elif event_type == "error":
                        logger.error(f"🔵 [AG2-EVENT] Error: {event.get('message', 'Unknown error')}")
                    elif event_type == "done":
                        logger.info(f"🔵 [AG2-EVENT] Stream complete ({event_count} events total)")

                    yield f"data: {json.dumps(event)}\n\n"

            except asyncio.CancelledError:
                logger.info(f"AG2 debate stream cancelled for {req.thread_id}")
                return
            except Exception as e:
                logger.error(f"Error in AG2 debate stream: {e}", exc_info=True)
                yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        return StreamingResponse(
            ag2_event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error(f"Failed to start AG2 debate service: {e}", exc_info=True)
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'message': f'Failed to initialize AG2 debate service: {str(e)}'})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            status_code=500,
        )


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
async def get_provider_models(
    provider: ProviderName,
    payload: ProviderKeyRequest,
    user: Optional[TokenPayload] = Depends(get_current_user_optional),
    pool = Depends(get_db),
) -> ProviderModelsResponse:
    """Fetch available models for a provider.

    If API key is provided, use it directly.
    If user is authenticated and allowlisted, use system key automatically.
    """
    from auth.provider_keys import get_system_key, get_user_allowlisted_providers, CANONICAL_PROVIDERS

    api_key = payload.api_key.strip() if payload.api_key else ""

    # If no API key provided, check if user is allowlisted for system key
    if not api_key and user and pool:
        try:
            allowlisted = await get_user_allowlisted_providers(user.email, pool)
            canonical = CANONICAL_PROVIDERS.get(provider.value, provider.value)
            if canonical in allowlisted:
                api_key = get_system_key(canonical) or ""
                if api_key:
                    logger.info(f"Using system key for {provider.value} (user {user.email} allowlisted)")
        except Exception as e:
            logger.warning(f"Could not check allowlist: {e}")

    if not api_key:
        raise HTTPException(status_code=400, detail="API key is required. Sign in and get allowlisted for system keys, or provide your own.")

    try:
        models = await fetch_provider_models(provider, api_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - network issues
        logger.exception("Failed to fetch models for provider %s", provider.value)
        raise HTTPException(status_code=502, detail="Failed to load models") from exc

    payload_models = [ProviderModel(**model) for model in models]
    return ProviderModelsResponse(models=payload_models)


class QuotaCheckRequest(BaseModel):
    """Request to check quota for multiple providers."""
    providers: list[str]  # List of provider names to check


class QuotaCheckResponse(BaseModel):
    """Response with quota status for each provider."""
    results: dict[str, QuotaStatus]


@app.post("/providers/check-quota", response_model=QuotaCheckResponse)
async def check_providers_quota(
    request: QuotaCheckRequest,
    user: Optional[TokenPayload] = Depends(get_current_user_optional),
    pool = Depends(get_db),
) -> QuotaCheckResponse:
    """Check API quota availability for specified providers.

    For each provider, makes a minimal API call to verify:
    1. API key is valid
    2. Quota/rate limits are not exhausted

    Returns status for each provider indicating if it can be used.
    """
    from auth.provider_keys import get_system_key, get_user_allowlisted_providers, CANONICAL_PROVIDERS

    results: dict[str, QuotaStatus] = {}

    # Get user's allowlisted providers if authenticated
    allowlisted: set[str] = set()
    if user and pool:
        try:
            allowlisted = await get_user_allowlisted_providers(user.email, pool)
        except Exception as e:
            logger.warning(f"Could not check allowlist: {e}")

    # Check each requested provider in parallel
    async def check_single_provider(provider_name: str) -> tuple[str, QuotaStatus]:
        try:
            provider = ProviderName(provider_name)
        except ValueError:
            return (provider_name, {"available": False, "error": f"Unknown provider: {provider_name}", "provider": provider_name})

        # Get API key - try system key if user is allowlisted
        canonical = CANONICAL_PROVIDERS.get(provider_name, provider_name)
        api_key = ""
        if canonical in allowlisted:
            api_key = get_system_key(canonical) or ""

        if not api_key:
            return (provider_name, {"available": False, "error": "No API key available", "provider": provider_name})

        status = await check_provider_quota(provider, api_key)
        return (provider_name, status)

    # Run all checks in parallel
    tasks = [check_single_provider(p) for p in request.providers]
    check_results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in check_results:
        if isinstance(result, Exception):
            logger.error(f"Quota check error: {result}")
            continue
        provider_name, status = result
        results[provider_name] = status

    return QuotaCheckResponse(results=results)


@app.get("/initial-keys")
async def get_initial_keys() -> dict[str, str]:
    """DEPRECATED: This endpoint exposes system keys and should not be used.

    For security, this now returns empty keys. Users should:
    1. Sign in with Google OAuth
    2. Add their own API keys (BYOK) via the settings panel
    3. Admins can allowlist users to use system keys

    This endpoint is kept for backwards compatibility but returns empty values.
    """
    logger.warning("Deprecated /initial-keys endpoint called - returning empty keys")
    return {
        "openai": "",
        "gemini": "",
        "claude": "",
        "grok": "",
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
