"""Debate orchestrator for AG2 backend.

Implements the phase-based state machine for debate control.
Deterministic control flow with no magic - explicit phase transitions.
"""

import asyncio
import logging
import re
from typing import Dict, Any, List, Optional

from .state import DebateState, DebateRound, QualityMetrics, RoundScoreData, DebateMode
from .agents import create_panelist_agent, create_moderator_agent, create_user_proxy, create_search_tool
from .evaluators import StanceExtractor, ArgumentParser, ConcessionDetector, ResponsivenessScorer
from .persistence import DebateStorage
from .scoring import DebateScorer, RoundScore
from config import (
    get_claude_api_key,
    get_gemini_api_key,
    get_grok_api_key,
    get_openai_api_key,
)

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

    def __init__(self, state: DebateState, event_queue: asyncio.Queue, storage: Optional[DebateStorage] = None):
        """Initialize orchestrator with state and event queue.

        Args:
            state: Initial debate state
            event_queue: Async queue for streaming events to frontend
            storage: Optional storage backend for quality tracking
        """
        self.state = state
        self.queue = event_queue
        self.storage = storage
        self.agents: List[Any] = []
        self.groupchat: Optional[Any] = None
        self.manager: Optional[Any] = None
        self.moderator: Optional[Any] = None
        
        # Initialize evaluators for quality tracking
        try:
            self.stance_extractor = StanceExtractor()
            self.argument_parser = ArgumentParser()
            self.concession_detector = ConcessionDetector()
            self.responsiveness_scorer = ResponsivenessScorer()
            self.evaluators_enabled = True
            logger.info("Quality evaluators initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize evaluators: {e}. Quality tracking disabled.")
            self.evaluators_enabled = False

        # Initialize scorer for human-in-the-loop scoring
        self.scorer = DebateScorer()
        self.scoring_enabled = True
        logger.info("Debate scorer initialized")

    async def _emit_event(self, event_type: str, **kwargs) -> None:
        """Emit SSE event to frontend.

        Args:
            event_type: Type of event (status, panelist_response, etc.)
            **kwargs: Additional fields for the event
        """
        event = {"type": event_type, **kwargs}
        await self.queue.put(event)

    def _parse_mentions(self, message: str) -> List[str]:
        """Extract @mentions from user message.

        Matches @mentions against actual panelist names (case-insensitive).

        Args:
            message: User's message potentially containing @mentions

        Returns:
            List of matched panelist names
        """
        # Extract all @mentions from message
        mentions = re.findall(r'@(\w+)', message)
        if not mentions:
            return []

        # Get panelist names from state
        panelists = self.state.get("panelists", [])
        panelist_names = [p.get("name", "") for p in panelists]

        # Match mentions to actual panelist names (case-insensitive)
        matched = []
        for name in panelist_names:
            for mention in mentions:
                if mention.lower() == name.lower():
                    matched.append(name)
                    break

        return matched

    def _inject_user_message(self, message: str, round_number: int) -> None:
        """Inject user message into debate context for all agents.

        Adds user input to GroupChat history so agents can see and respond to it.
        Handles @mentions by tagging specific panelists.

        Args:
            message: User's message to inject
            round_number: Current debate round number
        """
        if not message or not message.strip():
            return

        # Parse @mentions from message
        mentions = self._parse_mentions(message)

        # Build user context injection
        mention_note = ""
        if mentions:
            mention_note = f"\nTagged panelists: {', '.join(mentions)}\nTagged panelists should respond directly to this input."
        else:
            mention_note = "\nAll panelists should consider this input."

        user_injection = f"""
══════════════════════════════════════
[USER INPUT - Round {round_number}]
{message}
{mention_note}
══════════════════════════════════════
"""

        # Add to AG2 GroupChat history
        self.groupchat.messages.append({
            "role": "user",
            "content": user_injection,
            "name": "User"
        })

        # Update tagged_panelists in state for tracking
        if mentions:
            self.state["tagged_panelists"] = mentions

        logger.info(f"Injected user message into round {round_number}, mentions: {mentions}")

    def _auto_assign_adversarial_roles(self) -> None:
        """Assign PRO/CON/DEVIL'S ADVOCATE roles to panelists.

        Respects pre-assigned roles from panelist config, only auto-assigns
        for panelists without a role.

        Assignment logic for unassigned panelists:
        - Even number of unassigned: half PRO, half CON
        - Odd number of unassigned: half PRO, half CON, last one is Devil's Advocate

        Examples (all unassigned):
        - 2 panelists: 1 PRO, 1 CON
        - 3 panelists: 1 PRO, 1 CON, 1 DEVIL'S ADVOCATE
        - 4 panelists: 2 PRO, 2 CON
        - 5 panelists: 2 PRO, 2 CON, 1 DEVIL'S ADVOCATE
        """
        panelists = self.state.get("panelists", [])
        question = self.state.get("question", "the topic")
        n = len(panelists)

        if n == 0:
            self.state["assigned_roles"] = {}
            return

        roles = {}

        # First pass: collect pre-assigned roles from panelist configs
        pre_assigned_count = {"PRO": 0, "CON": 0, "DEVIL_ADVOCATE": 0}
        unassigned_panelists = []

        for i, panelist in enumerate(panelists):
            name = panelist.get("name", f"Panelist_{i}")
            pre_role = panelist.get("role")  # Check for pre-assigned role

            if pre_role in ("PRO", "CON", "DEVIL_ADVOCATE"):
                # Use pre-assigned role
                pre_assigned_count[pre_role] += 1
                role = pre_role
                if role == "PRO":
                    position = f"Argue FOR: {question}"
                    constraints = [
                        "You MUST argue in favor of the proposition",
                        "Find and emphasize positive aspects and benefits",
                        "Counter all arguments from CON panelists",
                        "Never concede that the proposition is wrong"
                    ]
                elif role == "CON":
                    position = f"Argue AGAINST: {question}"
                    constraints = [
                        "You MUST argue against the proposition",
                        "Find and emphasize negative aspects, risks, and problems",
                        "Counter all arguments from PRO panelists",
                        "Never concede that the proposition is right"
                    ]
                else:  # DEVIL_ADVOCATE
                    position = "STRICTLY NEUTRAL CRITIC - You do NOT support either side of this debate"
                    constraints = [
                        "ABSOLUTE RULE: Your stance is NEUTRAL - never FOR, never AGAINST",
                        "You exist ONLY to critique - you have NO personal position on the topic",
                        "When PRO argues, you MUST find flaws in their reasoning",
                        "When CON argues, you MUST find flaws in their reasoning too",
                        "You NEVER say 'I agree' or 'I support' any position"
                    ]

                roles[name] = {
                    "panelist_name": name,
                    "role": role,
                    "position_statement": position,
                    "constraints": constraints
                }
                logger.info(f"Using pre-assigned role for {name}: {role}")
            else:
                unassigned_panelists.append((i, panelist, name))

        # Second pass: auto-assign roles to remaining panelists
        unassigned_count = len(unassigned_panelists)
        if unassigned_count > 0:
            # Calculate how many PRO and CON needed
            # Odd: last one is Devil's Advocate, rest split evenly
            has_devils_advocate = (unassigned_count % 2 == 1)
            debate_count = unassigned_count - 1 if has_devils_advocate else unassigned_count
            pro_count = debate_count // 2
            con_count = debate_count - pro_count

            pro_assigned = 0
            con_assigned = 0

            for idx, (i, panelist, name) in enumerate(unassigned_panelists):
                # Last unassigned panelist is Devil's Advocate if odd number
                if has_devils_advocate and idx == unassigned_count - 1:
                    role = "DEVIL_ADVOCATE"
                    position = "STRICTLY NEUTRAL CRITIC - You do NOT support either side of this debate"
                    constraints = [
                        "ABSOLUTE RULE: Your stance is NEUTRAL - never FOR, never AGAINST",
                        "You exist ONLY to critique - you have NO personal position on the topic",
                        "When PRO argues, you MUST find flaws in their reasoning",
                        "When CON argues, you MUST find flaws in their reasoning too",
                        "You NEVER say 'I agree' or 'I support' any position"
                    ]
                elif pro_assigned < pro_count:
                    role = "PRO"
                    position = f"Argue FOR: {question}"
                    constraints = [
                        "You MUST argue in favor of the proposition",
                        "Find and emphasize positive aspects and benefits",
                        "Counter all arguments from CON panelists",
                        "Never concede that the proposition is wrong"
                    ]
                    pro_assigned += 1
                else:
                    role = "CON"
                    position = f"Argue AGAINST: {question}"
                    constraints = [
                        "You MUST argue against the proposition",
                        "Find and emphasize negative aspects, risks, and problems",
                        "Counter all arguments from PRO panelists",
                        "Never concede that the proposition is right"
                    ]
                    con_assigned += 1

                roles[name] = {
                    "panelist_name": name,
                    "role": role,
                    "position_statement": position,
                    "constraints": constraints
                }

        self.state["assigned_roles"] = roles
        role_summary = {name: info["role"] for name, info in roles.items()}
        logger.info(f"Assigned adversarial roles: {role_summary}")

    def _seed_assigned_roles_from_panelist_configs(self) -> None:
        """Seed assigned_roles from panelist configs (pre-assigned roles only).

        This ensures role-aware prompting works even when stance_mode is "free"/"assigned"
        but the frontend provided per-panelist roles in the panelist configs.
        """
        panelists = self.state.get("panelists", []) or []
        question = self.state.get("question", "the topic")

        assigned_roles = self.state.get("assigned_roles")
        if not isinstance(assigned_roles, dict):
            assigned_roles = {}

        for i, panelist in enumerate(panelists):
            name = panelist.get("name", f"Panelist_{i}")
            pre_role = panelist.get("role")

            if pre_role not in ("PRO", "CON", "DEVIL_ADVOCATE"):
                continue

            existing = assigned_roles.get(name)
            existing_role = existing.get("role") if isinstance(existing, dict) else None
            if existing_role in ("PRO", "CON", "DEVIL_ADVOCATE"):
                if existing_role != pre_role:
                    logger.warning(
                        f"Panelist role conflict for {name}: panelist_config={pre_role} assigned_roles={existing_role}. "
                        f"Keeping assigned_roles."
                    )
                continue

            if pre_role == "PRO":
                position = f"Argue FOR: {question}"
                constraints = [
                    "You MUST argue in favor of the proposition",
                    "Find and emphasize positive aspects and benefits",
                    "Counter all arguments from CON panelists",
                    "Never concede that the proposition is wrong",
                ]
            elif pre_role == "CON":
                position = f"Argue AGAINST: {question}"
                constraints = [
                    "You MUST argue against the proposition",
                    "Find and emphasize negative aspects, risks, and problems",
                    "Counter all arguments from PRO panelists",
                    "Never concede that the proposition is right",
                ]
            else:  # DEVIL_ADVOCATE
                position = "STRICTLY NEUTRAL CRITIC - You do NOT support either side of this debate"
                constraints = [
                    "ABSOLUTE RULE: Your stance is NEUTRAL - never FOR, never AGAINST",
                    "You exist ONLY to critique - you have NO personal position on the topic",
                    "When PRO argues, you MUST find flaws in their reasoning",
                    "When CON argues, you MUST find flaws in their reasoning too",
                    "You NEVER say 'I agree' or 'I support' any position",
                ]

            assigned_roles[name] = {
                "panelist_name": name,
                "role": pre_role,
                "position_statement": position,
                "constraints": constraints,
            }

        self.state["assigned_roles"] = assigned_roles

    def _role_expected_stance(self, role_type: str) -> Optional[str]:
        if role_type == "PRO":
            return "FOR"
        if role_type == "CON":
            return "AGAINST"
        if role_type == "DEVIL_ADVOCATE":
            return "NEUTRAL"
        return None

    def _role_required_prefix(self, role_type: str) -> Optional[str]:
        if role_type == "PRO":
            return "Position: FOR -"
        if role_type == "CON":
            return "Position: AGAINST -"
        if role_type == "DEVIL_ADVOCATE":
            return "As Devil's Advocate, I will critique both sides without taking a position."
        return None

    def _starts_with_required_prefix(self, response_text: str, required_prefix: str) -> bool:
        stripped = (response_text or "").lstrip()
        if stripped.startswith(required_prefix):
            return True
        if stripped.startswith(("\"", "“", "”", "'")):
            stripped = stripped[1:].lstrip()
            return stripped.startswith(required_prefix)
        return False

    def _build_stance_reminder_section(self) -> str:
        """Build a per-round stance reminder to reinforce assigned roles."""
        assigned_roles = self.state.get("assigned_roles") or {}

        lines: List[str] = []
        if assigned_roles:
            for name, role_info in assigned_roles.items():
                role_type = (role_info or {}).get("role", "")
                required_prefix = self._role_required_prefix(role_type) or ""
                if role_type == "PRO":
                    lines.append(f"  - {name}: PRO (argue FOR) | start with: {required_prefix}")
                elif role_type == "CON":
                    lines.append(f"  - {name}: CON (argue AGAINST) | start with: {required_prefix}")
                elif role_type == "DEVIL_ADVOCATE":
                    lines.append(f"  - {name}: DEVIL'S ADVOCATE (neutral critic) | start with: {required_prefix}")
                elif role_type:
                    lines.append(f"  - {name}: {role_type}")
        else:
            lines = [
                "  - Each panelist MUST take a clear stance (FOR or AGAINST) and stick to it.",
                "  - Start with either: Position: FOR -  OR  Position: AGAINST -",
                "  - Do NOT hedge with 'it depends' or switch sides mid-debate.",
            ]

        return (
            "\n\n═══════════════════════════════════════════════════════════════\n"
            "MANDATORY STANCE REMINDER (do not switch roles):\n"
            + "\n".join(lines)
            + "\n═══════════════════════════════════════════════════════════════\n"
        )

    def _build_role_enhanced_prompt(self, panelist_name: str, base_prompt: str) -> str:
        """Build system prompt with role constraints for adversarial debates.

        Args:
            panelist_name: Name of the panelist
            base_prompt: Original system prompt

        Returns:
            Enhanced prompt with role instructions
        """
        assigned_roles = self.state.get("assigned_roles", {})
        if not assigned_roles:
            return base_prompt

        role = assigned_roles.get(panelist_name)
        if not role:
            return base_prompt

        role_type = role.get("role", "")
        position = role.get("position_statement", "")
        constraints = role.get("constraints", [])

        if not role_type:
            # No role specified, return unmodified prompt
            return base_prompt

        # Build emphatic role instructions
        if role_type == "PRO":
            stance_instruction = "You are assigned to argue FOR the proposition. You MUST defend this position."
            forbidden = "FORBIDDEN: Do NOT agree that the proposition is wrong. Do NOT side with CON arguments."
        elif role_type == "CON":
            stance_instruction = "You are assigned to argue AGAINST the proposition. You MUST oppose this position."
            forbidden = "FORBIDDEN: Do NOT agree that the proposition is right. Do NOT side with PRO arguments."
        elif role_type == "DEVIL_ADVOCATE":
            stance_instruction = "You are the Devil's Advocate. You MUST NOT take a FOR or AGAINST position. Stay NEUTRAL and criticize BOTH sides equally."
            forbidden = "FORBIDDEN: Do NOT support either PRO or CON. Do NOT say 'I agree with...' for either side. You must criticize BOTH positions."
        else:
            # Unknown role type - log warning and use generic fallback
            logger.warning(f"Unknown role type '{role_type}' for {panelist_name}")
            stance_instruction = "Present a balanced analysis."
            forbidden = ""

        role_section = f"""
╔══════════════════════════════════════════════════════════════════╗
║  MANDATORY ASSIGNED ROLE: {role_type:^20}                        ║
╚══════════════════════════════════════════════════════════════════╝

{stance_instruction}

YOUR POSITION: {position}

ROLE REQUIREMENTS:
"""
        for i, constraint in enumerate(constraints, 1):
            role_section += f"  {i}. {constraint}\n"

        if role_type == "DEVIL_ADVOCATE":
            role_section += f"""
╔═══════════════════════════════════════════════════════════════════╗
║  !!!  DEVIL'S ADVOCATE - YOU HAVE NO POSITION  !!!                ║
╚═══════════════════════════════════════════════════════════════════╝

YOUR IDENTITY: You are a NEUTRAL CRITIC. You do NOT have an opinion.
YOUR JOB: Find problems with EVERY argument from EVERY side.

WHAT YOU MUST DO:
1. Start by saying: "As the Devil's Advocate, I will critique both sides..."
2. Critique at least ONE argument from the PRO side
3. Critique at least ONE argument from the CON side
4. End by saying: "I take no position - both sides need stronger arguments"

WHAT YOU MUST NEVER DO:
- Never say "I agree with PRO" or "I agree with CON"
- Never say "I believe" or "In my opinion" about the topic
- Never conclude that one side is right
- Never take a FOR or AGAINST stance

{forbidden}

YOUR TEMPLATE:
"As Devil's Advocate, I critique both positions:

To the PRO side: [Your criticism of their argument]

To the CON side: [Your criticism of their argument]

Both sides need to strengthen their cases before I would find either convincing."
═══════════════════════════════════════════════════════════════════

"""
        else:
            role_section += f"""
CRITICAL INSTRUCTIONS:
- You MUST maintain your assigned {role_type} position throughout the debate
- You MUST NOT switch sides or agree with opposing panelists
- If you see merit in an opposing point, STILL argue against it
- Find flaws, weaknesses, and counterarguments to opposing views
- Your goal is to make the STRONGEST possible case for YOUR assigned side

{forbidden}

"""

        return base_prompt + "\n" + role_section

    def _build_score_feedback(self, panelist_name: str) -> str:
        """Generate score feedback for agent context.

        Provides agents with:
        - Their current score and standing
        - Recent scoring events
        - Suggestions for improvement
        - Forced concession requirement if behind

        Args:
            panelist_name: Name of the panelist

        Returns:
            Score feedback string to inject into context, or empty string
        """
        if not self.scoring_enabled:
            return ""

        state = self.scorer.get_scores(panelist_name)
        if not state:
            return ""

        leader = self.scorer.get_leader()
        if not leader:
            return ""

        leader_name, leader_score = leader
        gap = leader_score - state.cumulative

        # Build feedback message
        feedback = f"""
════════════════════════════════════════════════════════════
DEBATE STATUS - Your Score: {state.cumulative} pts
════════════════════════════════════════════════════════════
Leader: {leader_name} with {leader_score} pts
{">>> YOU ARE LEADING! <<<" if gap <= 0 else f"You are {gap} points behind."}

"""

        # Add recent scoring events
        if state.events_history:
            recent = state.events_history[-5:]
            feedback += "RECENT SCORING:\n"
            for event in recent:
                sign = "+" if event.points >= 0 else ""
                feedback += f"  {sign}{event.points} pts: {event.reason}\n"
            feedback += "\n"

        # Add improvement suggestions
        feedback += "TO IMPROVE YOUR SCORE:\n"
        if state.ignored_claims:
            feedback += f"  - Address opponent's argument (+10 pts each)\n"
        feedback += "  - Provide concrete evidence for your claims (+8 pts)\n"
        feedback += "  - Find flaws in opponent's reasoning (+10 pts)\n"

        # Add forced concession if behind by 30+ pts
        if self.scorer.should_force_concession(panelist_name):
            feedback += f"""
════════════════════════════════════════════════════════════
!!! REQUIRED: FORCED CONCESSION !!!
════════════════════════════════════════════════════════════
You are {gap} points behind the leader ({leader_name}).

YOU MUST acknowledge at least ONE strong point from {leader_name}'s argument:
1. State specifically what point you are conceding
2. Explain why it's a valid point
3. Then continue making your own arguments

IMPORTANT:
- Do NOT switch sides or abandon your assigned role
- Frame the concession as a LIMITED point, then reaffirm your overall stance

This shows intellectual honesty and may help recover your standing.
════════════════════════════════════════════════════════════
"""
        else:
            feedback += "════════════════════════════════════════════════════════════\n"

        return feedback

    async def initialize(self) -> None:
        """Set up AG2 group chat and agents.

        Creates panelist agents, moderator, and group chat manager.
        Registers search tool if enabled.
        Applies adversarial role assignments if stance_mode is set.
        """
        if GroupChat is None:
            raise RuntimeError("ag2 not installed. Install with: pip install ag2")

        await self._emit_event("status", message="Initializing panel...")

        # Always seed pre-assigned roles from panelist configs so they're reflected in
        # state["assigned_roles"] and recognized by prompting/scoring.
        self._seed_assigned_roles_from_panelist_configs()

        # Handle adversarial role assignment (Phase 2)
        stance_mode = self.state.get("stance_mode", "free")
        if stance_mode == "adversarial":
            panelist_count = len(self.state.get("panelists") or [])
            assigned_count = len(self.state.get("assigned_roles") or {})
            if assigned_count != panelist_count:
                self._auto_assign_adversarial_roles()
            await self._emit_event(
                "roles_assigned",
                mode="adversarial",
                roles={k: v["role"] for k, v in (self.state.get("assigned_roles") or {}).items()}
            )

        # Create panelist agents from configuration
        self.agents = []
        panelists = self.state.get("panelists") or []
        provider_keys = self.state.get("provider_keys") or {}

        # Debug: Log received panelist configurations
        logger.info(f"🔵 [ROLE-DEBUG] Received {len(panelists)} panelist configs:")
        for p in panelists:
            logger.info(f"   - {p.get('name')}: provider={p.get('provider')}, role={p.get('role')}")

        # Get assigned roles (includes both pre-assigned and auto-assigned)
        assigned_roles = self.state.get("assigned_roles") or {}

        for panelist_config in panelists:
            try:
                provider = panelist_config.get("provider", "openai")
                panelist_name = panelist_config.get("name", "")

                # Inject the assigned role into config for persona-based prompt
                # This ensures auto-assigned roles also get persona prompts
                effective_role = panelist_config.get("role")  # Pre-assigned from frontend
                if effective_role:
                    logger.info(f"🔵 [ROLE-DEBUG] {panelist_name}: Using PRE-ASSIGNED role '{effective_role}'")
                elif panelist_name in assigned_roles:
                    # Use auto-assigned role
                    effective_role = assigned_roles[panelist_name].get("role")
                    logger.info(f"🔵 [ROLE-DEBUG] {panelist_name}: Using AUTO-ASSIGNED role '{effective_role}'")

                # Create a copy of config with the effective role
                config_with_role = {**panelist_config, "role": effective_role}

                # Get API key for this provider from provider_keys, with fallbacks
                if provider in provider_keys and provider_keys[provider]:
                    api_key = provider_keys[provider]
                elif provider == "openai":
                    api_key = get_openai_api_key()
                elif provider in {"gemini", "google"}:
                    api_key = get_gemini_api_key()
                elif provider in {"claude", "anthropic"}:
                    api_key = get_claude_api_key()
                elif provider in {"xai", "grok"}:
                    api_key = get_grok_api_key()
                else:
                    # Fallback to OpenAI if provider unknown
                    api_key = get_openai_api_key()
                    logger.warning(f"Unknown provider '{provider}', falling back to OpenAI API key")

                # Create agent with role for persona-based prompt
                # All agents now get persona prompts (both pre-assigned and auto-assigned)
                agent = create_panelist_agent(config_with_role, api_key)

                self.agents.append(agent)
                assigned_role = (self.state.get("assigned_roles") or {}).get(panelist_name, {}).get("role", "")
                role_info = f" [{assigned_role}]" if assigned_role else ""
                logger.info(f"Created agent: {panelist_name}{role_info} (provider: {provider})")
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

        # Choose a manager LLM config that matches an available provider so we
        # don't hard-require OpenAI when running Gemini/Claude-only setups.
        def _manager_config_list() -> list[dict]:
            provider_pref = [
                ("openai", "gpt-4o-mini", get_openai_api_key, {"api_type": "openai"}),
                ("google", "gemini-1.5-flash", get_gemini_api_key, {"api_type": "google"}),
                ("anthropic", "claude-3-5-haiku-20241022", get_claude_api_key, {"api_type": "anthropic"}),
                ("xai", "grok-beta", get_grok_api_key, {"api_type": "openai"}),
            ]

            for provider, default_model, key_fn, extra in provider_pref:
                # Prefer explicit provider_keys passed in
                if provider_keys.get(provider):
                    return [{
                        "model": default_model,
                        "api_key": provider_keys[provider],
                        **extra,
                    }]

                # Fall back to environment-based keys if available
                try:
                    api_key = key_fn()
                    return [{
                        "model": default_model,
                        "api_key": api_key,
                        **extra,
                    }]
                except Exception:
                    continue

            raise RuntimeError("No valid API key available to initialize GroupChatManager")

        # Create GroupChatManager to orchestrate the chat
        try:
            self.manager = GroupChatManager(
                groupchat=self.groupchat,
                llm_config={"config_list": _manager_config_list()},
                is_termination_msg=lambda x: "TERMINATE" in x.get("content", ""),
            )
        except Exception as e:
            logger.error(f"Failed to create GroupChatManager: {e}")
            raise

        logger.info(f"Initialized debate with {len(self.agents)} panelists")

    async def run_debate_round(self, question: str, user_message: Optional[str] = None) -> DebateRound:
        """Execute one debate round using AG2.

        1. Inject user message if provided (human-in-the-loop)
        2. Inject question into AG2 group chat
        3. Let AG2 manage agent turn-taking
        4. Collect panelist responses
        5. Check for consensus
        6. Emit debate_round event

        Args:
            question: The debate question/topic
            user_message: Optional user input to inject into this round

        Returns:
            DebateRound with responses and consensus status
        """
        await self._emit_event("status", message="Panel is discussing...")

        round_number = self.state.get("debate_round", 0)

        # Inject user message if provided (Phase 1: Human-in-the-loop)
        if user_message:
            self._inject_user_message(user_message, round_number)
            await self._emit_event(
                "user_message_injected",
                message=user_message,
                round=round_number,
                mentions=self.state.get("tagged_panelists", [])
            )

        # For first round, prepare topic context
        if round_number == 0:
            # Check for assigned roles to create explicit stance assignments
            assigned_roles = self.state.get("assigned_roles") or {}
            stance_reminder = self._build_stance_reminder_section()

            if assigned_roles:
                initial_message = f"""DEBATE TOPIC: {question}
{stance_reminder}

RULES FOR PRO PANELISTS:
- You MUST argue FOR the proposition
- Do NOT agree with CON panelists
- Your stance MUST be: FOR

RULES FOR CON PANELISTS:
- You MUST argue AGAINST the proposition
- Do NOT agree with PRO panelists
- Your stance MUST be: AGAINST

SPECIAL RULES FOR DEVIL'S ADVOCATE:
- YOU ARE FORBIDDEN from starting with "Position: FOR" or "Position: AGAINST"
- You MUST start with: As Devil's Advocate, I will critique both sides without taking a position.
- You MUST critique BOTH the PRO arguments AND the CON arguments
- You have NO OPINION - you are a critic, not a participant
- If you take sides, you have FAILED your role

Now, each panelist: state your assigned position clearly and argue for it.
(PRO: Argue FOR. CON: Argue AGAINST. Devil's Advocate: Critique BOTH sides without taking a position.)"""
            else:
                # No assigned roles - use generic polarization prompt
                initial_message = f"""DEBATE TOPIC: {question}
{stance_reminder}

IMPORTANT: Each panelist MUST take a clear FOR or AGAINST position.
- Do NOT all agree or hedge with "it depends"
- Take OPPOSITE sides to create a real debate
- Be bold and defend your position strongly
- The goal is to explore ALL sides of the issue through genuine disagreement

Now, each panelist: state your position clearly and argue for it."""
        else:
            # Continuation for subsequent rounds - build opponent summary for direct attacks
            debate_history = self.state.get("debate_history", [])
            opponent_summary = ""
            if debate_history:
                latest_round = debate_history[-1]
                responses = latest_round.get("panel_responses", {})
                if responses:
                    opponent_summary = "\n\n🎯 OPPONENT CLAIMS TO ATTACK:\n"
                    for name, resp in responses.items():
                        # Extract first 200 chars as their main claim
                        claim_preview = resp[:200].replace('\n', ' ')
                        if len(resp) > 200:
                            claim_preview += "..."
                        opponent_summary += f"- {name} argued: \"{claim_preview}\"\n"
            stance_reminder = self._build_stance_reminder_section()

            initial_message = f"""Continue debating: {question}
{opponent_summary}{stance_reminder}
⚔️ ROUND {round_number + 1} INSTRUCTIONS - TIME TO FIGHT:

1. ATTACK OPPONENTS BY NAME - Quote their specific claims and demolish them
2. Don't just repeat your position - RESPOND to what they said
3. Use phrases like "@[Name]: Your claim that X is wrong because..."
4. Find the WEAKEST point in each opponent's argument and expose it
5. If they attacked you, DEFEND and COUNTER-ATTACK

PRO panelists: Attack CON arguments. Show why their fears are unfounded.
CON panelists: Attack PRO arguments. Show why their promises are empty.
Devil's Advocate: Critique EVERYONE. Find flaws in ALL arguments.

This is a DEBATE, not a monologue. ENGAGE YOUR OPPONENTS!"""

        # Inject the message into AG2 group chat
        self.groupchat.messages.append({
            "role": "user",
            "content": initial_message,
        })

        # Collect responses from each panelist
        responses: Dict[str, str] = {}

        try:
            # ROUND 0 SPECIAL HANDLING: Generate responses independently
            # to prevent agents from seeing and copying each other's stances.
            # In subsequent rounds, agents should see previous responses for debate.
            is_first_round = (round_number == 0)

            # Store messages to add after all agents respond (for round 0)
            pending_messages: List[Dict[str, Any]] = []

            # Let each panelist respond
            for agent in self.agents:
                try:
                    # Inject per-agent role instruction to ensure they follow their assigned role
                    assigned_roles = self.state.get("assigned_roles") or {}
                    agent_role = assigned_roles.get(agent.name, {})
                    role_type = agent_role.get("role", "")

                    if role_type and is_first_round:
                        # Inject explicit role instruction for THIS agent
                        if role_type == "PRO":
                            role_instruction = f""">>> {agent.name}, YOUR MANDATORY ROLE IS: PRO <<<
You MUST argue FOR the proposition.
START your response with exactly: Position: FOR -
You are FORBIDDEN from arguing against or staying neutral."""
                        elif role_type == "CON":
                            role_instruction = f""">>> {agent.name}, YOUR MANDATORY ROLE IS: CON <<<
You MUST argue AGAINST the proposition.
START your response with exactly: Position: AGAINST -
You are FORBIDDEN from arguing for or staying neutral."""
                        elif role_type == "DEVIL_ADVOCATE":
                            # Get actual panelist names for the instruction
                            other_panelists = [a.name for a in self.agents if a.name != agent.name]
                            panelist_list = ", ".join(other_panelists) if other_panelists else "other panelists"

                            role_instruction = f""">>> {agent.name}, YOU ARE THE DEVIL'S ADVOCATE - YOU MUST NOT TAKE A SIDE <<<
YOU ARE FORBIDDEN FROM: Starting with "Position: FOR" or "Position: AGAINST"
YOU MUST START WITH: As Devil's Advocate, I will critique both sides without taking a position.

IMPORTANT FOR ROUND 1: This is the FIRST round - the other panelists ({panelist_list}) are responding at the same time as you.
Since you haven't seen their arguments yet, you should:
1. Introduce your role as the Devil's Advocate
2. Explain that you will be critiquing BOTH sides equally
3. Outline the types of weaknesses you'll be looking for (logical fallacies, missing evidence, assumptions)
4. Make clear that you take NO position on the topic itself

In SUBSEQUENT rounds, you will directly attack specific arguments from {panelist_list} by name.

YOU DO NOT HAVE AN OPINION. YOU ARE A CRITIC, NOT A PARTICIPANT.
If you take a FOR or AGAINST position, you have FAILED."""
                        else:
                            role_instruction = None

                        if role_instruction:
                            self.groupchat.messages.append({
                                "role": "system",
                                "content": role_instruction,
                                "name": f"RoleInstruction_{agent.name}"
                            })
                            logger.info(f"Injected role instruction for {agent.name}: {role_type}")

                    # Inject score feedback for this panelist (Phase 4: Score Feedback)
                    # Only for rounds > 0 when we have scores
                    if round_number > 0 and self.scoring_enabled:
                        score_feedback = self._build_score_feedback(agent.name)
                        if score_feedback:
                            self.groupchat.messages.append({
                                "role": "system",
                                "content": score_feedback,
                                "name": f"ScoreFeedback_{agent.name}"
                            })
                            logger.debug(f"Injected score feedback for {agent.name}")

                    # Get panelist response via AG2
                    reply = agent.generate_reply(
                        messages=self.groupchat.messages,
                        sender=self.manager,
                    )

                    # Clean up the role instruction message after response
                    if role_type and is_first_round:
                        self.groupchat.messages = [
                            msg for msg in self.groupchat.messages
                            if msg.get("name") != f"RoleInstruction_{agent.name}"
                        ]

                    # Handle different reply formats from different providers
                    # Some providers return strings, others return dicts
                    if isinstance(reply, dict):
                        # Extract content from dict response (e.g., Gemini)
                        reply_text = reply.get("content") or str(reply)
                    elif isinstance(reply, str):
                        reply_text = reply
                    else:
                        # Fallback: convert to string
                        reply_text = str(reply) if reply else ""

                    if reply_text and reply_text.strip():
                        final_text = reply_text

                        # Enforce stance-taking format and stance compliance (deterministic, at most 2 rewrite attempts).
                        required_prefix = self._role_required_prefix(role_type) if role_type else None
                        if required_prefix:
                            stripped = final_text.lstrip()
                            stripped_no_quote = stripped
                            if stripped_no_quote.startswith(("\"", "“", "”", "'")):
                                stripped_no_quote = stripped_no_quote[1:].lstrip()

                            format_ok = self._starts_with_required_prefix(final_text, required_prefix)
                            if role_type == "DEVIL_ADVOCATE" and (
                                stripped_no_quote.startswith("Position: FOR") or stripped_no_quote.startswith("Position: AGAINST")
                            ):
                                format_ok = False

                            if not format_ok:
                                correction_name = f"StanceCorrection_{agent.name}"
                                correction = f"""Your previous response did NOT follow your assigned role requirements.

Rewrite your response so that it strictly follows your role: {role_type}.
MANDATORY: Start your rewritten response with exactly:
{required_prefix}
Return ONLY the rewritten response text.

Previous response:
{final_text}
"""
                                self.groupchat.messages.append({
                                    "role": "system",
                                    "content": correction,
                                    "name": correction_name,
                                })
                                try:
                                    corrected = agent.generate_reply(
                                        messages=self.groupchat.messages,
                                        sender=self.manager,
                                    )
                                finally:
                                    self.groupchat.messages = [
                                        msg for msg in self.groupchat.messages
                                        if msg.get("name") != correction_name
                                    ]

                                if isinstance(corrected, dict):
                                    corrected_text = corrected.get("content") or str(corrected)
                                elif isinstance(corrected, str):
                                    corrected_text = corrected
                                else:
                                    corrected_text = str(corrected) if corrected else ""

                                if corrected_text and corrected_text.strip():
                                    final_text = corrected_text

                            if role_type == "DEVIL_ADVOCATE":
                                # Devil's Advocate must remain neutral: never take a FOR/AGAINST position or agree with a side.
                                has_banned_stance = re.search(r"\bPosition:\s*(FOR|AGAINST)\b", final_text, re.IGNORECASE)
                                has_agreement = re.search(r"\bI\s+(agree|support)\b", final_text, re.IGNORECASE)
                                if has_banned_stance or has_agreement:
                                    mismatch_name = f"StanceMismatchCorrection_{agent.name}"
                                    mismatch = f"""You violated the Devil's Advocate neutrality requirements.

Assigned role: DEVIL_ADVOCATE
MANDATORY: Rewrite your response to remain NEUTRAL, critique BOTH sides, and start with exactly:
{required_prefix}

FORBIDDEN: Do NOT use "Position: FOR" or "Position: AGAINST". Do NOT say "I agree" or "I support".
Return ONLY the rewritten response text.

Previous response:
{final_text}
"""
                                    self.groupchat.messages.append({
                                        "role": "system",
                                        "content": mismatch,
                                        "name": mismatch_name,
                                    })
                                    try:
                                        corrected2 = agent.generate_reply(
                                            messages=self.groupchat.messages,
                                            sender=self.manager,
                                        )
                                    finally:
                                        self.groupchat.messages = [
                                            msg for msg in self.groupchat.messages
                                            if msg.get("name") != mismatch_name
                                        ]

                                    if isinstance(corrected2, dict):
                                        corrected2_text = corrected2.get("content") or str(corrected2)
                                    elif isinstance(corrected2, str):
                                        corrected2_text = corrected2
                                    else:
                                        corrected2_text = str(corrected2) if corrected2 else ""

                                    if corrected2_text and corrected2_text.strip():
                                        final_text = corrected2_text

                            # Additional stance compliance check (beyond just the prefix).
                            expected_stance = self._role_expected_stance(role_type)
                            if expected_stance and role_type != "DEVIL_ADVOCATE":
                                if self.evaluators_enabled:
                                    stance_data = await self.stance_extractor.extract_stance(
                                        panelist_name=agent.name,
                                        response=final_text,
                                        previous_stance=None,
                                        assigned_role=role_type,
                                    )
                                    extracted = (stance_data or {}).get("stance")
                                    confidence = float((stance_data or {}).get("confidence", 0.0) or 0.0)
                                    if extracted and extracted != expected_stance and confidence >= 0.6:
                                        mismatch_name = f"StanceMismatchCorrection_{agent.name}"
                                        mismatch = f"""Your response does not match your assigned stance.

Assigned role: {role_type}
Expected stance: {expected_stance}
MANDATORY: Rewrite your response to match your assigned stance and start with exactly:
{required_prefix}

Return ONLY the rewritten response text.

Previous response:
{final_text}
"""
                                        self.groupchat.messages.append({
                                            "role": "system",
                                            "content": mismatch,
                                            "name": mismatch_name,
                                        })
                                        try:
                                            corrected2 = agent.generate_reply(
                                                messages=self.groupchat.messages,
                                                sender=self.manager,
                                            )
                                        finally:
                                            self.groupchat.messages = [
                                                msg for msg in self.groupchat.messages
                                                if msg.get("name") != mismatch_name
                                            ]

                                        if isinstance(corrected2, dict):
                                            corrected2_text = corrected2.get("content") or str(corrected2)
                                        elif isinstance(corrected2, str):
                                            corrected2_text = corrected2
                                        else:
                                            corrected2_text = str(corrected2) if corrected2 else ""

                                        if corrected2_text and corrected2_text.strip():
                                            final_text = corrected2_text

                        responses[agent.name] = final_text

                        # Remove the personalized score feedback message (keep groupchat clean)
                        if round_number > 0 and self.scoring_enabled:
                            self.groupchat.messages = [
                                msg for msg in self.groupchat.messages
                                if msg.get("name") != f"ScoreFeedback_{agent.name}"
                            ]

                        # For first round: DON'T add to groupchat yet (so other agents don't see it)
                        # For subsequent rounds: add immediately (normal debate behavior)
                        response_message = {
                            "role": "assistant",
                            "content": final_text,
                            "name": agent.name,
                        }

                        if is_first_round:
                            # Queue message for later - don't let other agents see it yet
                            pending_messages.append(response_message)
                        else:
                            # Normal behavior - add immediately for debate context
                            self.groupchat.messages.append(response_message)

                        # Stream response to frontend
                        await self._emit_event(
                            "panelist_response",
                            panelist=agent.name,
                            response=final_text,
                        )

                except Exception as e:
                    error_msg = str(e)
                    logger.error(f"Error getting response from {agent.name}: {error_msg}")

                    # Clean up the role instruction message on error too
                    if role_type and is_first_round:
                        self.groupchat.messages = [
                            msg for msg in self.groupchat.messages
                            if msg.get("name") != f"RoleInstruction_{agent.name}"
                        ]

                    # Clean up score feedback message on error too
                    if round_number > 0 and self.scoring_enabled:
                        self.groupchat.messages = [
                            msg for msg in self.groupchat.messages
                            if msg.get("name") != f"ScoreFeedback_{agent.name}"
                        ]

                    # Provide helpful error context
                    if "model_not_found" in error_msg or "does not exist" in error_msg:
                        responses[agent.name] = f"(Model error: Check model name and API access)"
                    elif "401" in error_msg or "Unauthorized" in error_msg:
                        responses[agent.name] = f"(API authentication error: Check API key)"
                    elif "429" in error_msg or "rate limit" in error_msg.lower():
                        responses[agent.name] = f"(Rate limit exceeded: Try again in a moment)"
                    else:
                        responses[agent.name] = f"(Unable to generate response: {error_msg[:100]})"

            # After all agents have responded in round 0, add all messages to groupchat
            # This ensures no agent could have seen another's response during generation
            if is_first_round and pending_messages:
                for msg in pending_messages:
                    self.groupchat.messages.append(msg)
                logger.info(f"Round 0: Added {len(pending_messages)} independent responses to groupchat")

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
            user_message=user_message,  # Include user's message in round data
        )

        # Update state BEFORE quality evaluation
        if "debate_history" not in self.state:
            self.state["debate_history"] = []
        self.state["debate_history"].append(round_data)

        # Update panel_responses in state so they're included in result event
        self.state["panel_responses"] = responses

        # Run quality evaluation BEFORE emitting event
        # This ensures stances are populated in round_data for the frontend
        if self.evaluators_enabled and self.storage:
            await self._evaluate_round_quality(round_number, responses)

        # Emit debate round event WITH stances populated
        await self._emit_event("debate_round", round=round_data)

        return round_data
    
    async def _evaluate_round_quality(self, round_number: int, responses: Dict[str, str]) -> None:
        """Run quality evaluators on debate round responses.
        
        Extracts:
        - Stances (position, confidence)
        - Arguments (claims, evidence, challenges)
        - Concessions (mind changes)
        - Responsiveness scores (engagement metrics)
        
        Args:
            round_number: Current debate round number
            responses: Dict of panelist_name -> response_text
        """
        thread_id = self.state["thread_id"]
        
        await self._emit_event("status", message="Analyzing debate quality...")
        
        try:
            # Get previous round arguments for responsiveness scoring
            previous_claims = []
            if round_number > 0:
                previous_claims = await self.storage.get_round_arguments(thread_id, round_number - 1)
            
            # Track extracted data for this round
            round_stances = {}
            round_arguments = []
            quality_metrics = QualityMetrics(
                responsiveness_scores={},
                claims_addressed={},
                claims_missed={},
                tags_used={},
                concessions_detected=[],
                evidence_strength={}
            )
            
            # Process each panelist response
            for panelist_name, response in responses.items():
                # Skip error responses
                if not response or response.startswith("("):
                    continue
                
                # 1. Extract stance
                previous_stance = await self.storage.get_previous_stance(
                    thread_id, panelist_name, round_number
                )
                # Get assigned role for this panelist (to force NEUTRAL for Devil's Advocate)
                assigned_roles = self.state.get("assigned_roles") or {}
                assigned_role = assigned_roles.get(panelist_name, {}).get("role")

                stance_data = await self.stance_extractor.extract_stance(
                    panelist_name, response, previous_stance, assigned_role=assigned_role
                )
                round_stances[panelist_name] = stance_data
                
                # Save stance to database
                await self.storage.save_stance(
                    thread_id=thread_id,
                    round_number=round_number,
                    panelist_name=stance_data["panelist_name"],
                    stance=stance_data["stance"],
                    core_claim=stance_data["core_claim"],
                    confidence=stance_data["confidence"],
                    changed_from_previous=stance_data["changed_from_previous"],
                    change_explanation=stance_data.get("change_explanation")
                )
                
                # Emit stance event
                await self._emit_event(
                    "stance_extracted",
                    panelist=panelist_name,
                    stance=stance_data["stance"],
                    confidence=stance_data["confidence"],
                    changed=stance_data["changed_from_previous"]
                )
                
                # 2. Parse arguments
                arguments = await self.argument_parser.parse_arguments(
                    panelist_name, response, previous_claims
                )
                
                # Save arguments to database
                for arg in arguments:
                    arg_id = await self.storage.save_argument_unit(
                        thread_id=thread_id,
                        round_number=round_number,
                        panelist_name=arg["panelist_name"],
                        unit_type=arg["unit_type"],
                        content=arg["content"],
                        target_claim_id=arg.get("target_claim_id"),
                        confidence=arg.get("confidence")
                    )
                    arg["id"] = arg_id
                    round_arguments.append(arg)
                
                # 3. Detect concessions
                concession = await self.concession_detector.detect_concession(
                    panelist_name, response
                )
                
                if concession:
                    # Save as special argument unit
                    concession_id = await self.storage.save_argument_unit(
                        thread_id=thread_id,
                        round_number=round_number,
                        panelist_name=panelist_name,
                        unit_type="concession",
                        content=concession["what_was_conceded"],
                        confidence=1.0,
                        metadata=concession
                    )
                    quality_metrics["concessions_detected"].append(concession_id)
                    
                    # Emit concession event
                    await self._emit_event(
                        "concession_detected",
                        panelist=panelist_name,
                        explanation=concession["explanation"],
                        what_conceded=concession["what_was_conceded"]
                    )
                
                # 4. Score responsiveness (except first round)
                if round_number > 0 and previous_claims:
                    # Get opponent claims only
                    opponent_claims = [
                        claim for claim in previous_claims
                        if claim.get("panelist_name") != panelist_name
                    ]
                    
                    responsiveness = await self.responsiveness_scorer.score_responsiveness(
                        panelist_name, response, opponent_claims
                    )
                    
                    # Save responsiveness score
                    await self.storage.save_responsiveness_score(
                        thread_id=thread_id,
                        round_number=round_number,
                        panelist_name=panelist_name,
                        score=responsiveness["score"],
                        claims_addressed=responsiveness["claims_addressed"],
                        claims_missed=responsiveness["claims_missed"],
                        tags_used=responsiveness["tags_used"],
                        missed_arguments=responsiveness.get("missed_arguments", [])
                    )
                    
                    # Update quality metrics
                    quality_metrics["responsiveness_scores"][panelist_name] = responsiveness["score"]
                    quality_metrics["claims_addressed"][panelist_name] = responsiveness["claims_addressed"]
                    quality_metrics["claims_missed"][panelist_name] = responsiveness["claims_missed"]
                    quality_metrics["tags_used"][panelist_name] = responsiveness["tags_used"]
                    
                    # Emit responsiveness event
                    await self._emit_event(
                        "responsiveness_score",
                        panelist=panelist_name,
                        score=responsiveness["score"],
                        claims_addressed=responsiveness["claims_addressed"],
                        claims_missed=responsiveness["claims_missed"]
                    )
                
                # Calculate evidence strength (count evidence units)
                evidence_count = sum(1 for arg in arguments if arg["unit_type"] == "evidence")
                quality_metrics["evidence_strength"][panelist_name] = min(1.0, evidence_count * 0.2)

            # Calculate scores for each panelist (Phase 3: Human-in-the-loop)
            round_scores: Dict[str, RoundScoreData] = {}
            if self.scoring_enabled:
                await self._calculate_round_scores(
                    round_number, responses, round_stances, round_arguments,
                    quality_metrics, round_scores
                )

            # Update debate history with quality data
            if "debate_history" in self.state and self.state["debate_history"]:
                latest_round = self.state["debate_history"][-1]
                latest_round["stances"] = round_stances
                latest_round["argument_graph"] = round_arguments
                latest_round["quality_metrics"] = quality_metrics
                latest_round["scores"] = round_scores  # Add scores to round data

                logger.info(f"Round {round_number} quality evaluation complete: "
                          f"{len(round_stances)} stances, {len(round_arguments)} arguments, "
                          f"{len(quality_metrics['concessions_detected'])} concessions")
        
        except Exception as e:
            logger.error(f"Error evaluating round quality: {e}", exc_info=True)
            # Don't fail the debate if evaluation fails

    async def _calculate_round_scores(
        self,
        round_number: int,
        responses: Dict[str, str],
        stances: Dict[str, Any],
        arguments: List[Dict[str, Any]],
        quality_metrics: QualityMetrics,
        round_scores: Dict[str, RoundScoreData]
    ) -> None:
        """Calculate debate scores for all panelists in a round.

        Uses the DebateScorer to evaluate each response and emit score events.

        Args:
            round_number: Current round number
            responses: Dict of panelist_name -> response_text
            stances: Dict of panelist_name -> stance_data
            arguments: List of argument units
            quality_metrics: Quality metrics for the round
            round_scores: Dict to populate with scores (output parameter)
        """
        try:
            thread_id = self.state["thread_id"]

            # Get opponent claims for responsiveness scoring
            opponent_claims_by_panelist: Dict[str, List[str]] = {}
            for arg in arguments:
                if arg.get("unit_type") == "claim":
                    panelist = arg.get("panelist_name", "")
                    for other_panelist in responses.keys():
                        if other_panelist != panelist:
                            if other_panelist not in opponent_claims_by_panelist:
                                opponent_claims_by_panelist[other_panelist] = []
                            opponent_claims_by_panelist[other_panelist].append(
                                arg.get("content", "")
                            )

            for panelist_name, response in responses.items():
                # Skip error responses
                if not response or response.startswith("("):
                    continue

                # Get stance data for this panelist
                stance_data = stances.get(panelist_name, {})
                current_stance = stance_data.get("stance")

                # Use assigned role as the declared stance, so scoring can reward consistency
                # and penalize drift from the intended debate stance.
                assigned_role = (self.state.get("assigned_roles") or {}).get(panelist_name, {}).get("role")
                declared_stance = None
                if assigned_role == "PRO":
                    declared_stance = "FOR"
                elif assigned_role == "CON":
                    declared_stance = "AGAINST"
                elif assigned_role == "DEVIL_ADVOCATE":
                    declared_stance = "NEUTRAL"

                # Count evidence and novel arguments
                evidence_count = sum(
                    1 for arg in arguments
                    if arg.get("panelist_name") == panelist_name
                    and arg.get("unit_type") == "evidence"
                )
                novel_count = sum(
                    1 for arg in arguments
                    if arg.get("panelist_name") == panelist_name
                    and arg.get("unit_type") == "claim"
                )

                # Get opponent claims for this panelist
                opponent_claims = opponent_claims_by_panelist.get(panelist_name, [])

                # Calculate score
                score = await self.scorer.score_round(
                    panelist_name=panelist_name,
                    response=response,
                    opponent_claims=opponent_claims,
                    declared_stance=declared_stance,
                    previous_arguments=None,
                    current_stance=current_stance,
                    evidence_count=evidence_count,
                    novel_arguments=novel_count,
                    user_votes=None  # User votes handled separately
                )

                # Convert to RoundScoreData
                round_scores[panelist_name] = RoundScoreData(
                    panelist_name=panelist_name,
                    round_number=round_number,
                    events=[
                        {"category": e.category, "points": e.points, "reason": e.reason}
                        for e in score.events
                    ],
                    round_total=score.round_total,
                    cumulative_total=score.cumulative_total
                )

                # Emit score event
                await self._emit_event(
                    "score_update",
                    panelist=panelist_name,
                    round_total=score.round_total,
                    cumulative_total=score.cumulative_total,
                    events=[
                        {"category": e.category, "points": e.points, "reason": e.reason}
                        for e in score.events
                    ]
                )

                # Check for forced concession
                if self.scorer.should_force_concession(panelist_name):
                    await self._emit_event(
                        "forced_concession_warning",
                        panelist=panelist_name,
                        gap=self.scorer.get_score_gap(panelist_name)
                    )

            # Save scores to storage
            if self.storage:
                await self.storage.save_round_scores(thread_id, round_number, round_scores)

            # Advance scorer to next round
            self.scorer.advance_round()

            logger.info(f"Round {round_number} scoring complete for {len(round_scores)} panelists")

        except Exception as e:
            logger.error(f"Error calculating round scores: {e}", exc_info=True)
            # Don't fail the debate if scoring fails

    async def _generate_responsiveness_feedback(self, round_number: int) -> str:
        """Generate feedback for panelists who scored low on responsiveness.
        
        Identifies panelists who missed opponent arguments and prompts them
        to address those points in the next round.
        
        Args:
            round_number: Round to check for low responsiveness
            
        Returns:
            Feedback string to inject into next round prompt, or empty string
        """
        try:
            debate_history = self.state.get("debate_history", [])
            if round_number >= len(debate_history):
                return ""
            
            round_data = debate_history[round_number]
            quality_metrics = round_data.get("quality_metrics", {})
            responsiveness_scores = quality_metrics.get("responsiveness_scores", {})
            
            # Identify low-scoring panelists (score < 0.5)
            low_scorers = {
                name: score for name, score in responsiveness_scores.items()
                if score < 0.5
            }
            
            if not low_scorers:
                return ""
            
            # Build feedback message
            feedback_parts = []
            for panelist, score in low_scorers.items():
                claims_missed = quality_metrics.get("claims_missed", {}).get(panelist, 0)
                if claims_missed > 0:
                    feedback_parts.append(
                        f"@{panelist}: You missed {claims_missed} opponent argument(s) in the previous round. "
                        f"Please address those points directly or explain why you're not engaging with them."
                    )
            
            if feedback_parts:
                return "\n".join(["RESPONSIVENESS FEEDBACK:"] + feedback_parts)
            
            return ""

        except Exception as e:
            logger.error(f"Error generating responsiveness feedback: {e}")
            return ""

    def _has_valid_responses(self, responses: Dict[str, str]) -> bool:
        """Check if responses dict contains actual panelist responses (not errors).

        Error messages start with "(" like "(Model error: ...)"
        Valid responses are actual panelist text.

        Args:
            responses: Dict of panelist_name -> response_text

        Returns:
            True if at least one valid response exists
        """
        for response in responses.values():
            # Valid responses must be non-empty and not error placeholders
            if response and response.strip() and not response.startswith("("):
                return True
        return False

    async def _check_consensus(self, responses: Dict[str, str]) -> bool:
        """Evidence-weighted consensus checking.

        Logic:
        - User-debate mode: never auto-consensus (user drives)
        - Single panelist: auto-consensus
        - Multiple panelists: evaluate stance alignment + evidence backing
        
        Consensus requires:
        1. Stances align (same position)
        2. Core claims compatible
        3. Evidence-backed positions agree (not just rhetoric)

        Args:
            responses: Dict of panelist_name -> response_text

        Returns:
            Boolean indicating if consensus was reached
        """
        # Participatory mode: never auto-consensus (user drives the debate)
        if self.state.get("debate_mode") == "participatory":
            return False

        # No valid responses: no consensus
        if not self._has_valid_responses(responses):
            return False

        # Single panelist: auto-consensus
        if len(responses) <= 1:
            return True

        # Multiple panelists: evaluate with stance + evidence awareness
        try:
            thread_id = self.state["thread_id"]
            round_number = self.state.get("debate_round", 0)
            
            # If we have stance data from quality evaluation, use it
            if self.evaluators_enabled and self.storage and round_number >= 0:
                # Get latest round data with stances
                debate_history = self.state.get("debate_history", [])
                if debate_history:
                    latest_round = debate_history[-1]
                    stances = latest_round.get("stances", {})
                    quality_metrics = latest_round.get("quality_metrics", {})
                    
                    if stances and len(stances) > 1:
                        # Check stance alignment
                        stance_values = [s["stance"] for s in stances.values()]
                        all_same_stance = len(set(stance_values)) == 1
                        
                        # Check confidence levels (all must be > 0.6 for consensus)
                        confidences = [s["confidence"] for s in stances.values()]
                        high_confidence = all(c >= 0.6 for c in confidences)
                        
                        # Check evidence strength (at least some evidence)
                        evidence_scores = quality_metrics.get("evidence_strength", {})
                        has_evidence = any(score > 0.3 for score in evidence_scores.values())
                        
                        # Consensus if stances align AND high confidence AND evidence-backed
                        if all_same_stance and high_confidence and has_evidence:
                            logger.info(f"Evidence-weighted consensus: stance={stance_values[0]}, "
                                      f"avg_confidence={sum(confidences)/len(confidences):.2f}")
                            return True
                        
                        # No consensus if stances differ or low confidence
                        if not all_same_stance:
                            logger.info(f"No consensus: stances differ {set(stance_values)}")
                            return False
                        
                        # Proceed to LLM evaluation if stances align but other criteria unclear
            
            # Fallback to LLM-based consensus check
            # Format responses for prompt
            responses_text = "\n".join(
                f"- {name}: {resp[:200]}..."
                for name, resp in responses.items()
                if resp and not resp.startswith("(")
            )

            prompt = CONSENSUS_PROMPT.format(responses=responses_text)

            # Get moderator's consensus evaluation
            result = self.moderator.generate_reply(
                messages=[{"role": "user", "content": prompt}],
                sender=None,
            )

            has_consensus = "CONSENSUS: YES" in (result or "")
            
            if has_consensus:
                logger.info("LLM-evaluated consensus reached")
            else:
                logger.info("LLM-evaluated: no consensus")
            
            return has_consensus

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
            # Verify debate history has valid panelist responses
            if "debate_history" not in self.state or not self.state["debate_history"]:
                error_msg = "No debate history available for moderation"
                logger.warning(error_msg)
                return error_msg

            # Check that at least one debate round has valid responses
            has_valid_responses = False
            for round_data in self.state["debate_history"]:
                if self._has_valid_responses(round_data.get("panel_responses", {})):
                    has_valid_responses = True
                    break

            if not has_valid_responses:
                error_msg = "No valid panelist responses found in debate history"
                logger.warning(error_msg)
                return error_msg

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
                    # Get user message (if resuming with input) and clear it after use
                    user_message = self.state.pop("user_message", None)
                    round_result = await self.run_debate_round(question, user_message=user_message)
                    self.state["debate_round"] = self.state.get("debate_round", 0) + 1

                    # Check if panelists provided valid responses
                    if not self._has_valid_responses(round_result["panel_responses"]):
                        error_msg = "All panelists failed to respond. Unable to continue debate."
                        logger.error(error_msg)
                        await self._emit_event("error", message=error_msg)
                        self.state["phase"] = "finished"
                        return self.state

                    # Deterministic phase transition logic based on debate_mode
                    # - autonomous: runs without pauses until end conditions
                    # - supervised: pauses for review/voting
                    # - participatory: pauses for user input
                    debate_mode = self.state.get("debate_mode", "autonomous")

                    if round_result["consensus_reached"]:
                        self.state["phase"] = "moderation"
                    elif self.state.get("debate_round", 0) >= self.state.get("max_rounds", 3):
                        self.state["phase"] = "moderation"
                    elif debate_mode in ("supervised", "participatory"):
                        # Pause for user review or input
                        self.state["phase"] = "paused"
                    else:
                        # autonomous mode - continue to next round
                        self.state["phase"] = "debate"

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
