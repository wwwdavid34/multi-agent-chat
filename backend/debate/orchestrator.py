"""Debate orchestrator for AG2 backend.

Implements the phase-based state machine for debate control.
Deterministic control flow with no magic - explicit phase transitions.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from .state import DebateState, DebateRound
from .agents import create_panelist_agent, create_moderator_agent, create_user_proxy, create_search_tool
from config import get_openai_api_key

try:
    import autogen as ag2
    from autogen import GroupChat, GroupChatManager, AssistantAgent
except ImportError:
    ag2 = None
    GroupChat = None
    GroupChatManager = None
    AssistantAgent = None

logger = logging.getLogger(__name__)

# Consensus prompt for evaluating agreement between panelists
CONSENSUS_PROMPT = """Based on the panel responses below, determine if the panelists have reached consensus.

Consensus means:
- All panelists agree on the main point
- Any disagreements are minor or peripheral
- There's a clear shared understanding on the core issue

Panel Responses:
{responses}

Respond with exactly: "CONSENSUS: YES" or "CONSENSUS: NO"

Then briefly explain (1-2 sentences):"""


class DebateOrchestrator:
    """Deterministic debate control plane.

    Manages debate lifecycle through explicit phase transitions:
    init -> debate -> [paused] -> debate -> moderation -> finished

    AG2 GroupChat handles:
    - Message history and context
    - Turn-taking between agents
    - Tool calling and execution

    DebateOrchestrator handles:
    - Phase transitions
    - Consensus checking
    - Round limits
    - Pause/resume logic
    """

    def __init__(self, state: DebateState, event_queue: asyncio.Queue):
        """Initialize orchestrator with state and event queue.

        Args:
            state: Initial debate state
            event_queue: Async queue for streaming events to frontend
        """
        self.state = state
        self.queue = event_queue
        self.agents: List[Any] = []
        self.groupchat: Optional[Any] = None
        self.manager: Optional[Any] = None
        self.moderator: Optional[Any] = None

    async def _emit_event(self, event_type: str, **kwargs) -> None:
        """Emit SSE event to frontend.

        Args:
            event_type: Type of event (status, panelist_response, etc.)
            **kwargs: Additional fields for the event
        """
        event = {"type": event_type, **kwargs}
        await self.queue.put(event)

    async def initialize(self) -> None:
        """Set up AG2 group chat and agents.

        Creates panelist agents, moderator, and group chat manager.
        Registers search tool if enabled.
        """
        if GroupChat is None:
            raise RuntimeError("ag2 not installed. Install with: pip install ag2")

        await self._emit_event("status", message="Initializing panel...")

        # Create panelist agents from configuration
        self.agents = []
        panelists = self.state.get("panelists", [])

        for panelist_config in panelists:
            try:
                provider = panelist_config.get("provider", "openai")
                api_key = panelist_config.get("api_key", get_openai_api_key())

                agent = create_panelist_agent(panelist_config, api_key)
                self.agents.append(agent)
                logger.info(f"Created agent: {panelist_config.get('name')}")
            except Exception as e:
                logger.error(f"Failed to create agent for {panelist_config}: {e}")
                raise

        # Create moderator agent
        try:
            self.moderator = create_moderator_agent()
        except Exception as e:
            logger.error(f"Failed to create moderator: {e}")
            raise

        # Create AG2 GroupChat (AG2 manages turn-taking and message history)
        self.groupchat = GroupChat(
            agents=self.agents + [self.moderator],
            messages=[],
            max_round=50,  # Safety limit for AG2's internal loop
        )

        # Create GroupChatManager to orchestrate the chat
        try:
            self.manager = GroupChatManager(
                groupchat=self.groupchat,
                llm_config={
                    "config_list": [{"model": "gpt-4o-mini", "api_key": get_openai_api_key()}]
                },
                is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
            )
        except Exception as e:
            logger.error(f"Failed to create GroupChatManager: {e}")
            raise

        logger.info(f"Initialized debate with {len(self.agents)} panelists")

    async def run_debate_round(self, question: str) -> DebateRound:
        """Execute one debate round using AG2.

        1. Inject question into AG2 group chat
        2. Let AG2 manage agent turn-taking
        3. Collect panelist responses
        4. Check for consensus
        5. Emit debate_round event

        Args:
            question: The debate question/topic

        Returns:
            DebateRound with responses and consensus status
        """
        await self._emit_event("status", message="Panel is discussing...")

        round_number = self.state.get("debate_round", 0)

        # For first round, prepare topic context
        if round_number == 0:
            # Initial question to start debate
            initial_message = f"Let's discuss this topic: {question}\n\nEach panelist should provide their perspective."
        else:
            # Continuation for subsequent rounds
            initial_message = f"Continue the discussion on: {question}\n\nConsider the points already raised and add new insights."

        # Inject the message into AG2 group chat
        self.groupchat.messages.append({
            "role": "user",
            "content": initial_message,
        })

        # Collect responses from each panelist
        responses: Dict[str, str] = {}

        try:
            # Let each panelist respond
            for agent in self.agents:
                try:
                    # Get panelist response via AG2
                    reply = agent.generate_reply(
                        messages=self.groupchat.messages,
                        sender=self.manager,
                    )

                    if reply:
                        responses[agent.name] = reply
                        self.groupchat.messages.append({
                            "role": "assistant",
                            "content": reply,
                            "name": agent.name,
                        })

                        # Stream response to frontend
                        await self._emit_event(
                            "panelist_response",
                            panelist=agent.name,
                            response=reply,
                        )

                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error getting response from {agent.name}: {error_msg}")

                    # Provide helpful error context
                    if "model_not_found" in error_msg or "does not exist" in error_msg:
                        responses[agent.name] = f"(Model error: Check model name and API access)"
                    elif "401" in error_msg or "Unauthorized" in error_msg:
                        responses[agent.name] = f"(API authentication error: Check API key)"
                    elif "429" in error_msg or "rate limit" in error_msg.lower():
                        responses[agent.name] = f"(Rate limit exceeded: Try again in a moment)"
                    else:
                        responses[agent.name] = f"(Unable to generate response: {error_msg[:100]})"

        except Exception as e:
            logger.error(f"Error during debate round: {e}")
            raise

        # Check for consensus
        consensus = await self._check_consensus(responses)

        # Build round result
        round_data = DebateRound(
            round_number=round_number,
            panel_responses=responses,
            consensus_reached=consensus,
            user_message=None,
        )

        # Emit debate round event
        await self._emit_event("debate_round", round=round_data)

        # Update state
        if "debate_history" not in self.state:
            self.state["debate_history"] = []
        self.state["debate_history"].append(round_data)

        return round_data

    async def _check_consensus(self, responses: Dict[str, str]) -> bool:
        """Simplified consensus checking.

        Logic:
        - User-debate mode: never auto-consensus (user drives)
        - Single panelist: auto-consensus
        - Multiple panelists: use moderator to evaluate

        Args:
            responses: Dict of panelist_name -> response_text

        Returns:
            Boolean indicating if consensus was reached
        """
        # User-debate: never auto-consensus
        if self.state.get("user_as_participant"):
            return False

        # Single panelist: auto-consensus
        if len(responses) <= 1:
            return True

        # Multiple panelists: use moderator to evaluate
        try:
            # Format responses for prompt
            responses_text = "\n".join(
                f"- {name}: {resp[:200]}..."
                for name, resp in responses.items()
            )

            prompt = CONSENSUS_PROMPT.format(responses=responses_text)

            # Get moderator's consensus evaluation
            result = self.moderator.generate_reply(
                messages=[{"role": "user", "content": prompt}],
                sender=None,
            )

            return "CONSENSUS: YES" in (result or "")

        except Exception as e:
            logger.error(f"Error checking consensus: {e}")
            # On error, don't claim consensus
            return False

    async def run_moderation(self) -> str:
        """Generate final summary via moderator.

        Takes full debate history and generates synthesized summary.

        Returns:
            Final summary string
        """
        await self._emit_event("status", message="Moderating the discussion...")

        try:
            # Get all messages from group chat
            debate_history = "\n".join(
                f"{m.get('name', 'User')}: {m.get('content', '')}"
                for m in self.groupchat.messages[-20:]  # Last 20 messages for context
            )

            summary_prompt = f"""Please provide a final synthesis of this panel discussion:

{debate_history}

Create a comprehensive summary that:
1. Identifies key arguments from each panelist
2. Highlights areas of agreement
3. Notes important disagreements
4. Provides your assessment of the strongest points
5. Suggests areas for further exploration

Keep the summary to 2-3 paragraphs."""

            summary = self.moderator.generate_reply(
                messages=[{"role": "user", "content": summary_prompt}],
                sender=None,
            )

            return summary or "Unable to generate summary"

        except Exception as e:
            logger.error(f"Error during moderation: {e}")
            return f"Moderation failed: {str(e)}"

    async def step(self) -> DebateState:
        """Execute one phase step.

        Phase state machine:
        - init: Initialize AG2 setup -> debate
        - debate: Run debate round -> paused/debate/moderation
        - paused: Wait for user -> debate
        - moderation: Generate summary -> finished
        - finished: Terminal state

        Returns:
            Updated state after step execution
        """
        try:
            match self.state["phase"]:
                case "init":
                    # Initialize AG2 group chat
                    await self.initialize()
                    self.state["phase"] = "debate"
                    return self.state

                case "debate":
                    # Run one debate round
                    question = self.state.get("question", "")
                    round_result = await self.run_debate_round(question)
                    self.state["debate_round"] = self.state.get("debate_round", 0) + 1

                    # Deterministic phase transition logic
                    if round_result["consensus_reached"]:
                        self.state["phase"] = "moderation"
                    elif self.state.get("debate_round", 0) >= self.state.get("max_rounds", 3):
                        self.state["phase"] = "moderation"
                    elif self.state.get("step_review"):
                        self.state["phase"] = "paused"
                    else:
                        self.state["phase"] = "debate"  # Loop for next round

                    return self.state

                case "paused":
                    # Wait for user to resume (no action here)
                    return self.state

                case "moderation":
                    # Generate final summary
                    summary = await self.run_moderation()
                    self.state["summary"] = summary
                    self.state["phase"] = "finished"
                    return self.state

                case "finished":
                    # Terminal state
                    return self.state

        except Exception as e:
            logger.error(f"Error in orchestrator step: {e}")
            await self._emit_event("error", message=str(e))
            raise
