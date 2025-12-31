"""LangGraph orchestration for the AI multi-agent discussion panel."""
from __future__ import annotations

import logging
import asyncio
from typing import Annotated, Any, Callable, Dict, Iterable, List, Optional

import httpx
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, AnyMessage, BaseMessage, HumanMessage, SystemMessage, RemoveMessage
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import Protocol, TypedDict

from config import (
    get_claude_api_key,
    get_gemini_api_key,
    get_grok_api_key,
    get_openai_api_key,
    get_pg_conn_str,
    use_in_memory_checkpointer,
)


logger = logging.getLogger(__name__)

# Global variable to track actual storage mode (set during graph compilation)
_actual_storage_mode: str = "unknown"

# Global reference to keep the PostgreSQL connection context manager alive
_postgres_cm = None

class DebateRound(TypedDict):
    """Single round of debate with all panelist responses."""
    round_number: int
    panel_responses: Dict[str, str]
    consensus_reached: bool


class PanelState(TypedDict):
    """State shared across all nodes in the discussion graph."""

    messages: Annotated[List[AnyMessage], add_messages]
    panel_responses: Dict[str, str]
    summary: Optional[str]
    conversation_summary: str
    search_results: Optional[str]  # Web search results shared among panelists
    needs_search: bool  # Whether moderator determined search is needed
    debate_mode: bool  # Whether debate mode is enabled
    debate_round: int  # Current debate round number
    max_debate_rounds: int  # Maximum number of debate rounds
    consensus_reached: bool  # Whether panelists have reached consensus
    debate_history: List[DebateRound]  # History of all debate rounds
    step_review: bool  # Whether to pause after each round for user review
    debate_paused: bool  # Whether debate is currently paused waiting for user


class PanelistConfig(TypedDict):
    id: str
    name: str
    provider: str
    model: str


DEFAULT_PANELISTS: List[PanelistConfig] = [
    {
        "id": "panelist-default-1",
        "name": "GPT-4o Mini",
        "provider": "openai",
        "model": "gpt-4o-mini",
    },
    {
        "id": "panelist-default-2",
        "name": "GPT-4o",
        "provider": "openai",
        "model": "gpt-4o",
    },
]


PROVIDER_DEFAULT_MODELS: Dict[str, str] = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-1.5-flash",
    "claude": "claude-3-haiku-20240307",
    "grok": "grok-beta",
}


class PanelistRunner(Protocol):
    def invoke(self, messages: List[AnyMessage]) -> AIMessage:  # pragma: no cover - protocol
        ...

    async def ainvoke(self, messages: List[AnyMessage]) -> AIMessage:  # pragma: no cover - protocol
        ...


class GrokChatRunner:
    """Minimal runner for xAI's Grok chat completion API."""

    api_url = "https://api.x.ai/v1/chat/completions"

    def __init__(self, model: str, api_key: str, temperature: float) -> None:
        self.model = model
        self.api_key = api_key
        self.temperature = temperature

    def invoke(self, messages: List[AnyMessage]) -> AIMessage:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": _to_openai_messages(messages),
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=30.0) as client:
            response = client.post(self.api_url, json=payload, headers=headers)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:  # pragma: no cover - network failures
                raise RuntimeError(f"Grok request failed: {response.text}") from exc

        data = response.json()
        content = _extract_grok_content(data)
        if not content:
            raise RuntimeError("Grok returned an empty response")
        return AIMessage(content=content)

    async def ainvoke(self, messages: List[AnyMessage]) -> AIMessage:
        payload = {
            "model": self.model,
            "temperature": self.temperature,
            "messages": _to_openai_messages(messages),
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(self.api_url, json=payload, headers=headers)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:  # pragma: no cover - network failures
                raise RuntimeError(f"Grok request failed: {response.text}") from exc

        data = response.json()
        content = _extract_grok_content(data)
        if not content:
            raise RuntimeError("Grok returned an empty response")
        return AIMessage(content=content)


def _to_openai_messages(messages: Iterable[BaseMessage]) -> List[Dict[str, str]]:
    as_dicts: List[Dict[str, str]] = []
    for message in messages:
        if isinstance(message, HumanMessage):
            role = "user"
        elif isinstance(message, AIMessage):
            role = "assistant"
        else:
            role = "system"
        as_dicts.append({"role": role, "content": _message_content_as_text(message)})
    return as_dicts


def _message_content_as_text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return str(content)


def _normalize_message_content(message: BaseMessage) -> BaseMessage:
    """
    Normalize message content to ensure compatibility with LLM APIs.

    Fixes issues where checkpoint deserialization creates invalid content formats
    (e.g., array with raw strings instead of objects).
    """
    content = message.content

    # If content is already a string, it's valid
    if isinstance(content, str):
        return message

    # If content is a list, ensure all elements are properly formatted
    if isinstance(content, list):
        # Check if any element is a raw string (invalid format)
        has_raw_strings = any(isinstance(item, str) for item in content)

        if has_raw_strings:
            # Convert to plain text string
            normalized_content = _message_content_as_text(message)
            # Create new message with normalized content
            if isinstance(message, HumanMessage):
                return HumanMessage(content=normalized_content)
            elif isinstance(message, AIMessage):
                return AIMessage(content=normalized_content)
            elif isinstance(message, SystemMessage):
                return SystemMessage(content=normalized_content)

    return message


def _extract_grok_content(payload: Dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: List[str] = []
        for part in content:
            if isinstance(part, dict):
                text = part.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return ""


ProviderFactory = Callable[[PanelistConfig, Dict[str, str]], PanelistRunner]


def _create_openai_runner(panelist: PanelistConfig, provider_keys: Dict[str, str]) -> PanelistRunner:
    model_name = panelist["model"] or PROVIDER_DEFAULT_MODELS["openai"]
    api_key = _provider_key("openai", provider_keys, get_openai_api_key)
    return ChatOpenAI(model=model_name, temperature=0.2, api_key=api_key)


def _create_gemini_runner(panelist: PanelistConfig, provider_keys: Dict[str, str]) -> PanelistRunner:
    model_name = panelist["model"] or PROVIDER_DEFAULT_MODELS["gemini"]
    api_key = _provider_key("gemini", provider_keys, get_gemini_api_key)
    return ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key, temperature=0.2)


def _create_claude_runner(panelist: PanelistConfig, provider_keys: Dict[str, str]) -> PanelistRunner:
    model_name = panelist["model"] or PROVIDER_DEFAULT_MODELS["claude"]
    api_key = _provider_key("claude", provider_keys, get_claude_api_key)
    return ChatAnthropic(model=model_name, temperature=0.2, anthropic_api_key=api_key)


def _create_grok_runner(panelist: PanelistConfig, provider_keys: Dict[str, str]) -> PanelistRunner:
    model_name = panelist["model"] or PROVIDER_DEFAULT_MODELS["grok"]
    api_key = _provider_key("grok", provider_keys, get_grok_api_key)
    return GrokChatRunner(model=model_name, api_key=api_key, temperature=0.2)


PROVIDER_FACTORIES: Dict[str, ProviderFactory] = {
    "openai": _create_openai_runner,
    "gemini": _create_gemini_runner,
    "claude": _create_claude_runner,
    "grok": _create_grok_runner,
}


get_openai_api_key()
summarizer_model = ChatOpenAI(model="gpt-4o-mini", temperature=0.1, api_key=get_openai_api_key())
moderator_model = ChatOpenAI(model="gpt-4o", temperature=0.1, api_key=get_openai_api_key())


def _truncate_messages(messages: List[AnyMessage], max_recent: int = 10) -> List[AnyMessage]:
    """
    Intelligently truncate message history to fit within context limits.

    Strategy:
    1. Keep system messages (summaries, search results)
    2. Keep the most recent user-assistant exchanges
    3. Drop older conversation history
    """
    if len(messages) <= max_recent:
        return messages

    # Separate system messages from conversation messages
    system_messages = [msg for msg in messages if isinstance(msg, SystemMessage)]
    conversation_messages = [msg for msg in messages if not isinstance(msg, SystemMessage)]

    # Keep only the most recent conversation messages
    recent_conversation = conversation_messages[-max_recent:]

    # Combine: system messages + recent conversation
    truncated = system_messages + recent_conversation

    logger.warning(
        f"Context truncated: {len(messages)} → {len(truncated)} messages "
        f"(kept {len(system_messages)} system + {len(recent_conversation)} recent)"
    )

    return truncated


async def _invoke_with_retry(
    runner,
    history: List[AnyMessage],
    panelist_name: str,
    max_retries: int = 3
) -> AnyMessage:
    """
    Invoke a panelist with automatic retry on context length errors.

    Progressively reduces context window on each retry:
    - Retry 1: Keep last 10 messages
    - Retry 2: Keep last 6 messages
    - Retry 3: Keep last 3 messages
    """
    truncation_levels = [10, 6, 3]

    for attempt in range(max_retries):
        try:
            current_history = history if attempt == 0 else _truncate_messages(history, truncation_levels[attempt - 1])
            return await runner.ainvoke(current_history)

        except Exception as e:
            error_str = str(e)

            # Check if it's a rate limit error (fail fast, don't retry)
            is_rate_limit_error = (
                "rate_limit_exceeded" in error_str or
                "rate limit" in error_str.lower() or
                "too many requests" in error_str.lower() or
                "quota exceeded" in error_str.lower()
            )

            if is_rate_limit_error:
                logger.error(f"{panelist_name}: Rate limit exceeded. Not retrying.")
                return AIMessage(
                    content=f"I apologize, but I cannot respond right now due to rate limiting. "
                           f"The API has reached its request limit. Please try again in a moment."
                )

            # Check if it's a context length error (retry with truncation)
            is_context_error = (
                "context_length_exceeded" in error_str or
                "maximum context length" in error_str.lower() or
                "too many tokens" in error_str.lower()
            )

            if not is_context_error:
                # Not a context error, don't retry
                raise

            if attempt < max_retries - 1:
                logger.warning(
                    f"{panelist_name}: Context length exceeded (attempt {attempt + 1}/{max_retries}). "
                    f"Retrying with truncated context (max {truncation_levels[attempt]} messages)..."
                )
            else:
                # Final retry failed
                logger.error(
                    f"{panelist_name}: All retries exhausted. Returning error response."
                )
                # Return a fallback response
                return AIMessage(
                    content=f"I apologize, but I cannot process this request due to context length limitations. "
                           f"The conversation history is too long. Please start a new conversation or "
                           f"reduce the amount of context."
                )

    # Should never reach here, but just in case
    raise RuntimeError("Unexpected retry logic error")


async def panelist_sequence_node(state: PanelState, config: Optional[RunnableConfig] = None) -> Dict[str, object]:
    """Run each configured panelist in parallel and collect responses."""

    panel_configs = _resolve_panelists(config)
    provider_keys = _resolve_provider_keys(config)
    panel_responses = dict(state.get("panel_responses", {}))

    # Normalize message content when loading from checkpoint to fix format issues
    raw_messages = list(state.get("messages", []))
    history: List[AnyMessage] = [_normalize_message_content(msg) for msg in raw_messages]

    summary = state.get("conversation_summary", "")
    if summary:
        history = [SystemMessage(content=f"Previous conversation summary: {summary}")] + history

    # Inject search results if available
    search_results = state.get("search_results")
    if search_results:
        search_context = SystemMessage(
            content=f"IMPORTANT: Web search results for the current question:\n\n{search_results}\n\n"
                   f"Please use this information in your response when relevant."
        )
        history = [search_context] + history
        logger.info("Injected search results into panelist context")

    # In debate mode (round > 0), inject other panelists' responses for debate context
    debate_mode = state.get("debate_mode", False)
    debate_round = state.get("debate_round", 0)

    if debate_mode and debate_round > 0 and panel_responses:
        panelist_names = list(panel_responses.keys())
        if debate_round == 1:
            # First debate round - establish clear positions
            debate_context = SystemMessage(
                content=f"=== DEBATE ROUND {debate_round} - TAKE A STANCE ===\n\n"
                       f"You are participating in a panel debate with: {', '.join(panelist_names)}\n\n"
                       f"CRITICAL INSTRUCTIONS FOR DEBATE MODE:\n"
                       f"- DO NOT provide a balanced 'on one hand, on the other hand' response\n"
                       f"- You MUST take a clear, specific position on the question\n"
                       f"- Defend your position with strong arguments and evidence\n"
                       f"- Review other panelists' responses below and identify where you DISAGREE\n"
                       f"- Use @Name syntax to directly challenge other panelists (e.g., '@ChatGPT, I disagree because...')\n"
                       f"- Be respectful but assertive - this is a debate, not a consensus exercise\n"
                       f"- If you genuinely agree with another panelist, say so explicitly and build on their argument\n\n"
                       f"Previous Round Responses:\n\n" +
                       "\n\n".join(f"{name}:\n{resp}" for name, resp in panel_responses.items()) +
                       f"\n\n{'='*50}\n\n"
                       f"Now take a CLEAR STANCE for Round {debate_round}. Use @Name to challenge specific points:"
            )
        else:
            # Subsequent rounds - refine position or concede
            debate_context = SystemMessage(
                content=f"=== DEBATE ROUND {debate_round} - DEFEND OR CONCEDE ===\n\n"
                       f"You are continuing the debate with: {', '.join(panelist_names)}\n\n"
                       f"INSTRUCTIONS:\n"
                       f"- Review how other panelists responded to your arguments\n"
                       f"- Either DEFEND your position with new evidence/reasoning, or CONCEDE if they made valid points\n"
                       f"- Use @Name to respond to specific arguments (e.g., '@Claude, you raise a good point about X, but...')\n"
                       f"- Look for weaknesses in opposing arguments and point them out\n"
                       f"- If you're changing your position, clearly state what convinced you\n"
                       f"- Only agree to consensus if you genuinely believe the positions have converged\n\n"
                       f"Previous Round Responses:\n\n" +
                       "\n\n".join(f"{name}:\n{resp}" for name, resp in panel_responses.items()) +
                       f"\n\n{'='*50}\n\n"
                       f"Round {debate_round} - Defend your position or explain what changed your mind:"
            )
        history = [debate_context] + history
        logger.info(f"Injected debate context for round {debate_round}")

    new_messages: List[AnyMessage] = []

    runners = [_build_runner(p, provider_keys) for p in panel_configs]

    # Run all panelists in parallel with retry logic for context errors
    results = await asyncio.gather(
        *(_invoke_with_retry(runner, history, panelist["name"])
          for runner, panelist in zip(runners, panel_configs))
    )

    for panelist, response in zip(panel_configs, results):
        new_messages.append(response)
        panel_responses[panelist["name"]] = response.content

    return {
        "messages": new_messages,
        "panel_responses": panel_responses,
    }


async def moderator_search_decision(state: PanelState) -> Dict[str, Any]:
    """Moderator evaluates if web search is needed to answer the question."""

    # Normalize message content when loading from checkpoint
    raw_messages = list(state.get("messages", []))
    messages = [_normalize_message_content(msg) for msg in raw_messages]

    if not messages:
        return {"search_results": None, "needs_search": False}

    # Get the latest user question
    user_messages = [m for m in messages if isinstance(m, HumanMessage)]
    if not user_messages:
        return {"search_results": None, "needs_search": False}

    latest_question = user_messages[-1].content

    # Moderator analyzes the question
    decision_prompt = f"""You are a moderator analyzing whether a question requires current web information.

Question: {latest_question}

Analyze if this question can be answered with general knowledge and reasoning, or if it requires:
- Current events or recent developments
- Real-time data (weather, stock prices, sports scores, etc.)
- Information about events that happened recently
- Latest research, news, or announcements
- Time-sensitive information
- Facts that change frequently

Respond in this exact format:
DECISION: [SEARCH or NO_SEARCH]
REASONING: [Brief explanation of why search is or isn't needed]

Examples:
- "Explain how neural networks work" → NO_SEARCH (general knowledge)
- "What are the latest breakthroughs in AI?" → SEARCH (needs current info)
- "Who won the 2024 election?" → SEARCH (recent event)
- "What is quantum computing?" → NO_SEARCH (established concept)
- "Current weather in Tokyo" → SEARCH (real-time data)
"""

    response = await moderator_model.ainvoke([HumanMessage(content=decision_prompt)])
    decision_text = response.content

    # Parse decision
    needs_search = "DECISION: SEARCH" in decision_text.upper()

    # Extract reasoning for logging
    reasoning = "No reasoning provided"
    if "REASONING:" in decision_text:
        reasoning = decision_text.split("REASONING:", 1)[1].strip()

    logger.info(f"Moderator decision: {'SEARCH' if needs_search else 'NO_SEARCH'}")
    logger.info(f"Reasoning: {reasoning}")

    return {
        "search_results": None,  # Will be filled by search node if needed
        "needs_search": needs_search,
    }


async def search_node(state: PanelState) -> Dict[str, Any]:
    """Perform web search - only called when moderator decides it's needed."""

    # Normalize message content when loading from checkpoint
    raw_messages = list(state.get("messages", []))
    messages = [_normalize_message_content(msg) for msg in raw_messages]

    user_messages = [m for m in messages if isinstance(m, HumanMessage)]
    if not user_messages:
        return {"search_results": None}

    latest_question = user_messages[-1].content

    logger.info(f"Performing web search for: {latest_question}")

    try:
        # Initialize Tavily search
        from langchain_tavily import TavilySearch

        search_tool = TavilySearch(
            max_results=5,
            include_answer=True,
            include_raw_content=True,
            search_depth="advanced",
        )

        results = await search_tool.ainvoke(latest_question)

        # TavilySearch returns a formatted string directly
        if isinstance(results, str):
            formatted_results = f"=== WEB SEARCH RESULTS ===\n\n"
            formatted_results += f"Query: {latest_question}\n\n"
            formatted_results += results
        else:
            # Handle list/dict format (fallback)
            formatted_results = "=== WEB SEARCH RESULTS ===\n\n"
            formatted_results += f"Query: {latest_question}\n"

            if isinstance(results, list):
                formatted_results += f"Found {len(results)} sources\n\n"
                for i, result in enumerate(results, 1):
                    if isinstance(result, dict):
                        formatted_results += f"## Source {i}: {result.get('title', 'Untitled')}\n"
                        formatted_results += f"URL: {result.get('url', 'N/A')}\n"
                        formatted_results += f"\nContent:\n{result.get('content', '')}\n"
                        formatted_results += "\n" + "="*50 + "\n\n"
                    else:
                        formatted_results += f"{result}\n\n"
            else:
                formatted_results += f"{results}\n"

        logger.info("Search completed successfully")
        return {"search_results": formatted_results}

    except Exception as e:
        logger.error(f"Search failed: {e}")
        error_msg = f"Search attempted but failed: {str(e)}\nPlease answer based on your general knowledge."
        return {"search_results": error_msg}


def moderator_node(state: PanelState) -> Dict[str, object]:
    panel_responses = state.get("panel_responses", {})

    # Normalize message content when loading from checkpoint to fix format issues
    raw_messages = list(state.get("messages", []))
    messages = [_normalize_message_content(msg) for msg in raw_messages]

    panel_text = "\n\n".join(
        f"{name}:\n{resp}" for name, resp in panel_responses.items()
    )

    moderator_prompt = (
        "You are moderating a panel of expert AI agents.\n"
        "Provide a final consolidated answer.\n"
        "Highlight agreements and disagreements.\n\n"
        f"Panel responses:\n{panel_text}"
    )

    # Try with full context first, then progressively truncate on context errors
    truncation_levels = [None, 10, 6, 3]  # None means no truncation

    for attempt, max_messages in enumerate(truncation_levels):
        try:
            current_messages = messages if max_messages is None else _truncate_messages(messages, max_messages)

            response = moderator_model.invoke(
                current_messages + [HumanMessage(content=moderator_prompt)]
            )

            return {
                "messages": [response],
                "summary": response.content,
            }

        except Exception as e:
            error_str = str(e)

            # Check if it's a rate limit error (fail fast, don't retry)
            is_rate_limit_error = (
                "rate_limit_exceeded" in error_str or
                "rate limit" in error_str.lower() or
                "too many requests" in error_str.lower() or
                "quota exceeded" in error_str.lower()
            )

            if is_rate_limit_error:
                logger.error("Moderator: Rate limit exceeded. Not retrying.")
                return {
                    "messages": [],
                    "summary": "Unable to generate summary due to rate limiting. The API has reached its request limit. Please try again in a moment.",
                }

            # Check if it's a context length error (retry with truncation)
            is_context_error = (
                "context_length_exceeded" in error_str or
                "maximum context length" in error_str.lower() or
                "too many tokens" in error_str.lower()
            )

            if not is_context_error or attempt == len(truncation_levels) - 1:
                # Not a context error, or final attempt failed
                if is_context_error:
                    logger.error("Moderator: All retries exhausted due to context length")
                    # Return error summary
                    return {
                        "messages": [],
                        "summary": "Unable to generate summary due to context length limitations. Please start a new conversation.",
                    }
                else:
                    raise

            logger.warning(
                f"Moderator: Context length exceeded (attempt {attempt + 1}). "
                f"Retrying with truncated context (max {truncation_levels[attempt + 1]} messages)..."
            )


async def consensus_checker_node(state: PanelState) -> Dict[str, Any]:
    """
    Evaluate if panelists have reached consensus on their responses.

    Uses the moderator model to analyze if there's substantial agreement
    or if continued debate would be beneficial.
    """
    panel_responses = state.get("panel_responses", {})
    debate_round = state.get("debate_round", 0)

    if len(panel_responses) < 2:
        # Can't have meaningful debate with less than 2 panelists; treat as consensus so we can terminate.
        consensus_reached = True
        debate_history = list(state.get("debate_history") or [])
        current_round: DebateRound = {
            "round_number": debate_round,
            "panel_responses": dict(panel_responses),
            "consensus_reached": consensus_reached,
        }
        debate_history.append(current_round)
        return {
            "consensus_reached": consensus_reached,
            "debate_round": debate_round + 1,
            "debate_history": debate_history,
        }

    panel_text = "\n\n".join(
        f"{name}:\n{resp}" for name, resp in panel_responses.items()
    )

    consensus_prompt = f"""You are evaluating whether a panel of AI agents has reached TRUE CONSENSUS in a debate.

Current debate round: {debate_round}

Panel responses:
{panel_text}

IMPORTANT: Be STRICT in evaluating consensus. Panelists simply covering similar topics is NOT consensus.

Consider consensus reached ONLY if ALL of these are true:
- Panelists have taken SPECIFIC positions (not just "it depends" or "there are pros and cons")
- Their final conclusions and recommendations ALIGN
- They explicitly acknowledge agreement with each other
- No significant contradictions remain in their positions
- They've moved from disagreement to agreement through the debate

Consider consensus NOT reached if:
- Panelists are giving balanced "both sides" responses without clear stances
- They mention different factors without agreeing on which is most important
- They propose different solutions or recommendations
- They haven't directly engaged with each other's arguments
- They're talking past each other on different aspects
- Further debate could force them to take clearer positions
- Round 1: Almost NEVER grant consensus - agents need to challenge each other first

Respond in this exact format:
CONSENSUS: [YES or NO]
REASONING: [Explain whether they took clear stances and if those stances align]
KEY_DISAGREEMENTS: [If NO, list the specific positions that differ]
"""

    response = await moderator_model.ainvoke([HumanMessage(content=consensus_prompt)])
    decision_text = response.content

    # Parse decision
    consensus_reached = "CONSENSUS: YES" in decision_text.upper()

    # Extract reasoning for logging
    reasoning = "No reasoning provided"
    if "REASONING:" in decision_text:
        reasoning_section = decision_text.split("REASONING:", 1)[1]
        if "KEY_DISAGREEMENTS:" in reasoning_section:
            reasoning = reasoning_section.split("KEY_DISAGREEMENTS:")[0].strip()
        else:
            reasoning = reasoning_section.strip()

    logger.info(f"Consensus check (round {debate_round}): {'YES' if consensus_reached else 'NO'}")
    logger.info(f"Reasoning: {reasoning}")

    # Save this round to debate history
    debate_history = list(state.get("debate_history") or [])
    current_round: DebateRound = {
        "round_number": debate_round,
        "panel_responses": panel_responses.copy(),
        "consensus_reached": consensus_reached,
    }
    debate_history.append(current_round)

    return {
        "consensus_reached": consensus_reached,
        "debate_round": debate_round + 1,  # Increment for next round
        "debate_history": debate_history,
    }


def pause_for_review(state: PanelState) -> Dict[str, Any]:
    """
    Pause the debate for user review in step review mode.
    The graph will end here and wait for user to continue.
    """
    logger.info("Debate paused for user review")
    return {
        "debate_paused": True,
        "summary": None,  # Don't generate final summary yet
    }


def summarize_conversation(state: PanelState) -> Dict[str, Any]:
    summary = state.get("conversation_summary", "")

    # Normalize message content when loading from checkpoint
    raw_messages = list(state.get("messages", []))
    messages = [_normalize_message_content(msg) for msg in raw_messages]

    # Keep last 4 messages
    if len(messages) <= 4:
        return {}

    to_summarize = messages[:-4]
    
    # Generate summary
    prompt = (
        f"Current summary: {summary}\n\n"
        "New lines of conversation:\n" +
        "\n".join(f"{m.type}: {m.content}" for m in to_summarize) +
        "\n\nSummarize the new lines into the existing summary."
    )
    
    response = summarizer_model.invoke([HumanMessage(content=prompt)])
    new_summary = response.content
    
    # Delete summarized messages
    delete_messages = [RemoveMessage(id=m.id) for m in to_summarize]
    
    return {
        "conversation_summary": new_summary,
        "messages": delete_messages
    }


def should_summarize(state: PanelState) -> str:
    messages = state.get("messages", [])
    if len(messages) > 6:
        return "summarize_conversation"
    return "moderator_search_decision"


def should_search(state: PanelState) -> str:
    """Route to search node if moderator determined search is needed."""
    if state.get("needs_search", False):
        return "search"
    return "panelists"


def should_continue_debate(state: PanelState) -> str:
    """
    Decide whether to continue debating or proceed to final moderation.

    Routes to:
    - "consensus_checker" if debate mode is on and we haven't hit max rounds
    - "moderator" if debate mode is off, consensus reached, or max rounds hit
    """
    debate_mode = state.get("debate_mode", False)

    if not debate_mode:
        # Debate mode off, go straight to moderator
        return "moderator"

    debate_round = state.get("debate_round", 0)
    max_rounds = state.get("max_debate_rounds", 3)
    consensus_reached = state.get("consensus_reached", False)

    # If this is the first round (round 0), always check for consensus
    if debate_round == 0:
        return "consensus_checker"

    # Check if we should continue debating
    if consensus_reached:
        logger.info("Consensus reached, ending debate")
        return "moderator"

    # Allow the final round to be evaluated by consensus_checker.
    # (panelists already produced responses for `debate_round`; consensus_checker decides termination and increments.)
    if debate_round > max_rounds:
        logger.info(f"Max debate rounds ({max_rounds}) exceeded, ending debate")
        return "moderator"

    # Continue debating
    logger.info(f"Continuing debate (round {debate_round}/{max_rounds})")
    return "consensus_checker"


def after_consensus_check(state: PanelState) -> str:
    """
    After checking consensus, decide whether to loop back for another debate round,
    pause for user review (in step review mode), or proceed to final moderation.
    """
    consensus_reached = state.get("consensus_reached", False)
    debate_round = state.get("debate_round", 1)  # Already incremented by consensus_checker
    max_rounds = state.get("max_debate_rounds", 3)
    step_review = state.get("step_review", False)

    # IMPORTANT: Force at least ONE round of actual debate
    # Round 0 = initial responses, Round 1 = first debate
    # Never go to moderator before Round 1 completes
    if debate_round <= 1:
        logger.info(f"Round {debate_round} - forcing debate to continue (need at least 1 debate round)")
        # In step review mode, pause after round 1 for user decision
        if step_review:
            logger.info("Step review mode: pausing after round 1 for user review")
            return "pause_for_review"
        return "panelists"

    # After Round 1+, check if we should end the debate
    if consensus_reached:
        logger.info("Consensus reached after check, proceeding to moderator")
        return "moderator"

    if debate_round > max_rounds:
        logger.info(f"Max rounds ({max_rounds}) exceeded, proceeding to moderator")
        return "moderator"

    # In step review mode, pause for user to decide whether to continue
    if step_review:
        logger.info(f"Step review mode: pausing after round {debate_round} for user review")
        return "pause_for_review"

    logger.info(f"No consensus, continuing to debate round {debate_round}")
    return "panelists"


def _resolve_panelists(config: Optional[RunnableConfig]) -> List[PanelistConfig]:
    configurable = {}
    if config and isinstance(config, dict):
        configurable = config.get("configurable") or {}

    raw_panelists = configurable.get("panelists")
    if isinstance(raw_panelists, list) and raw_panelists:
        source = raw_panelists
    else:
        source = DEFAULT_PANELISTS

    resolved: List[PanelistConfig] = []
    for index, entry in enumerate(source):
        resolved.append(_sanitize_panelist(entry, index))
    return resolved


def _resolve_provider_keys(config: Optional[RunnableConfig]) -> Dict[str, str]:
    configurable = {}
    if config and isinstance(config, dict):
        configurable = config.get("configurable") or {}
    raw_keys = configurable.get("provider_keys")
    provider_keys: Dict[str, str] = {}
    if isinstance(raw_keys, dict):
        for key, value in raw_keys.items():
            if isinstance(value, str) and value.strip():
                provider_keys[key.lower()] = value.strip()
    return provider_keys


def _sanitize_panelist(entry: Any, index: int) -> PanelistConfig:
    if not isinstance(entry, dict):
        raise ValueError("Each panelist must be an object")

    provider = str(entry.get("provider") or "openai").lower().strip()
    if provider not in PROVIDER_FACTORIES:
        raise ValueError(f"Unsupported provider: {provider}")

    default_model = PROVIDER_DEFAULT_MODELS.get(provider, PROVIDER_DEFAULT_MODELS["openai"])
    model = str(entry.get("model") or default_model).strip() or default_model
    name = str(entry.get("name") or f"Panelist {index + 1}").strip() or f"Panelist {index + 1}"
    identifier = str(entry.get("id") or f"panelist-{index + 1}").strip() or f"panelist-{index + 1}"

    return {
        "id": identifier,
        "name": name,
        "provider": provider,
        "model": model,
    }


def _build_runner(panelist: PanelistConfig, provider_keys: Dict[str, str]) -> PanelistRunner:
    provider = panelist["provider"].lower()
    factory = PROVIDER_FACTORIES.get(provider)
    if not factory:
        raise ValueError(f"Unsupported provider: {provider}")
    return factory(panelist, provider_keys)


def _provider_key(provider: str, provider_keys: Dict[str, str], fallback: Callable[[], str]) -> str:
    sanitized = provider.lower()
    key = provider_keys.get(sanitized)
    if key:
        return key
    return fallback()


def build_panel_graph():
    builder = StateGraph(PanelState)

    # Add all nodes
    builder.add_node("summarize_conversation", summarize_conversation)
    builder.add_node("moderator_search_decision", moderator_search_decision)
    builder.add_node("search", search_node)
    builder.add_node("panelists", panelist_sequence_node)
    builder.add_node("consensus_checker", consensus_checker_node)
    builder.add_node("pause_for_review", pause_for_review)
    builder.add_node("moderator", moderator_node)

    # Routing from START: check if summarization is needed
    builder.add_conditional_edges(START, should_summarize)

    # After summarization, go to search decision
    builder.add_edge("summarize_conversation", "moderator_search_decision")

    # After search decision, conditionally route to search or directly to panelists
    builder.add_conditional_edges("moderator_search_decision", should_search)

    # After search, go to panelists
    builder.add_edge("search", "panelists")

    # After panelists, conditionally check if we should continue debating or go to moderator
    builder.add_conditional_edges("panelists", should_continue_debate)

    # After consensus check, decide to loop back to panelists, pause for review, or go to moderator
    builder.add_conditional_edges("consensus_checker", after_consensus_check)

    # Pause for review ends the graph (user will continue manually)
    builder.add_edge("pause_for_review", END)

    # Moderator completes the discussion
    builder.add_edge("moderator", END)

    global _actual_storage_mode

    if use_in_memory_checkpointer():
        checkpointer = MemorySaver()
        _actual_storage_mode = "memory"
        logger.info("Using in-memory storage (ephemeral)")
    else:
        global _postgres_cm
        try:
            # Import async PostgreSQL checkpointer
            from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
            import asyncio
            import threading

            pg_url = get_pg_conn_str()

            # Create async checkpointer by entering the async context manager
            # Since we may be in a running event loop (uvicorn), we need to run this
            # in a new event loop in a separate thread
            async def _setup_checkpointer():
                cm = AsyncPostgresSaver.from_conn_string(pg_url)
                return await cm.__aenter__()

            def _run_in_new_loop():
                # Create a new event loop for this thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(_setup_checkpointer())
                finally:
                    loop.close()

            # Run in a thread to avoid "event loop already running" errors
            result_container = []
            def thread_target():
                try:
                    result_container.append(_run_in_new_loop())
                except Exception as e:
                    result_container.append(e)

            thread = threading.Thread(target=thread_target)
            thread.start()
            thread.join()

            if result_container and not isinstance(result_container[0], Exception):
                checkpointer = result_container[0]
                # Store the checkpointer globally to prevent garbage collection
                _postgres_cm = checkpointer
                _actual_storage_mode = "postgres"
                logger.info("Using PostgreSQL storage (persistent) with async support")
            else:
                raise result_container[0] if result_container else RuntimeError("Failed to initialize checkpointer")


        except Exception as exc:  # pragma: no cover - fallback in local envs
            logger.warning("Falling back to in-memory checkpointer: %s", exc)
            checkpointer = MemorySaver()
            _actual_storage_mode = "memory"
    return builder.compile(checkpointer=checkpointer)


def get_storage_mode() -> dict[str, str]:
    """Return information about the current storage mode."""
    return {
        "mode": _actual_storage_mode,
        "persistent": str(_actual_storage_mode == "postgres").lower(),
        "description": (
            "In-memory storage (conversations will be lost on restart)"
            if _actual_storage_mode == "memory"
            else "PostgreSQL database (conversations persist across restarts)"
        ),
    }


panel_graph = build_panel_graph()
