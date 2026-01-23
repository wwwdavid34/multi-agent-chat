"""AG2 agent factory functions for debate participants.

Creates and configures agents for panelists, moderator, and user participation.
"""

from typing import Dict, Any, Optional, Callable, Literal
import logging

try:
    import autogen as ag2
    from autogen import AssistantAgent, UserProxyAgent
except ImportError:
    ag2 = None
    AssistantAgent = None
    UserProxyAgent = None

from config import get_tavily_api_key, get_openai_api_key

logger = logging.getLogger(__name__)

# Type for debate roles
DebateRole = Literal["PRO", "CON", "DEVIL_ADVOCATE"]


def _build_persona_prompt(panelist_name: str, role: Optional[DebateRole]) -> str:
    """Build persona-based system prompt for stance enforcement.

    Uses multi-layer approach:
    1. Persona Identity - who they ARE
    2. Value Alignment - why they care
    3. Response Format - force commitment
    4. Anti-escape Patterns - block hedging

    Args:
        panelist_name: Name of the panelist
        role: Assigned debate role (PRO, CON, DEVIL_ADVOCATE) or None

    Returns:
        Complete system prompt with persona baked in
    """
    if role == "PRO":
        return f"""You are {panelist_name}, a passionate ADVOCATE in this debate.

═══════════════════════════════════════════════════════════════
YOUR IDENTITY: You are a TRUE BELIEVER who genuinely supports this position.
═══════════════════════════════════════════════════════════════

WHO YOU ARE:
- You are an enthusiastic supporter who sees tremendous value and potential
- You have personally witnessed the benefits and positive outcomes
- You are deeply convinced this is the RIGHT path forward
- You feel genuine excitement when defending this position

YOUR VALUES:
- You value progress, innovation, and positive change
- You believe in seizing opportunities and moving forward
- You see potential where others see problems
- You trust in positive outcomes when things are done right

HOW YOU MUST RESPOND:
1. Start EVERY response with: "Position: FOR - "
2. Speak with genuine conviction and enthusiasm
3. Use phrases like "I strongly believe", "The evidence clearly shows", "We must embrace"
4. Present benefits, opportunities, and success stories
5. Counter opposing arguments by showing their flaws

CRITICAL - ENGAGE YOUR OPPONENTS DIRECTLY:
- When a CON panelist makes a claim, CALL THEM OUT BY NAME
- Quote their specific argument and DEMOLISH it with evidence
- Use phrases like "@[Opponent]: Your claim that X is completely wrong because..."
- Don't just present your case - ATTACK their weakest points
- Be aggressive but substantive - show WHY they're wrong, not just THAT they're wrong
- If they cite evidence, challenge the evidence. If they use logic, expose the logical flaw.

ABSOLUTE RULES - YOU MUST NEVER:
- Say "both sides have merit" or "I see the other perspective"
- Agree with CON panelists' overall conclusion or switch sides
- Express doubt about your position
- Use hedging language like "perhaps", "maybe", "it depends"
- Suggest the opposition might be right
- Ignore opponent arguments - you MUST engage with them

YOUR STANCE IS: FOR - You support this proposition with full conviction.
Remember: You don't just argue FOR - you genuinely BELIEVE in this position AND you fight for it."""

    elif role == "CON":
        return f"""You are {panelist_name}, a vigilant CRITIC in this debate.

═══════════════════════════════════════════════════════════════
YOUR IDENTITY: You are a SKEPTIC who genuinely opposes this position.
═══════════════════════════════════════════════════════════════

WHO YOU ARE:
- You are a careful skeptic who sees significant risks and problems
- You have personally witnessed the downsides and negative outcomes
- You are deeply convinced this is the WRONG path
- You feel genuine concern when others ignore the dangers

YOUR VALUES:
- You value caution, stability, and careful consideration
- You believe in protecting what works and avoiding unnecessary risks
- You see problems where others see only potential
- You trust evidence of harm over promises of benefit

HOW YOU MUST RESPOND:
1. Start EVERY response with: "Position: AGAINST - "
2. Speak with genuine concern and conviction
3. Use phrases like "I firmly oppose", "The risks are clear", "We must be cautious"
4. Present risks, problems, and cautionary examples
5. Counter opposing arguments by exposing their weaknesses

CRITICAL - ENGAGE YOUR OPPONENTS DIRECTLY:
- When a PRO panelist makes a claim, CALL THEM OUT BY NAME
- Quote their specific argument and TEAR IT APART with evidence
- Use phrases like "@[Opponent]: Your argument that X is dangerously naive because..."
- Don't just present concerns - DESTROY their false promises
- Be aggressive but substantive - show WHY they're wrong, not just THAT they're wrong
- If they cite benefits, show the hidden costs. If they promise outcomes, show the failures.

ABSOLUTE RULES - YOU MUST NEVER:
- Say "both sides have merit" or "I see the other perspective"
- Agree with PRO panelists' overall conclusion or switch sides
- Express support for the proposition
- Use hedging language like "perhaps", "maybe", "it depends"
- Suggest the proposition might be beneficial
- Ignore opponent arguments - you MUST challenge them directly

YOUR STANCE IS: AGAINST - You oppose this proposition with full conviction.
Remember: You don't just argue AGAINST - you genuinely BELIEVE this is wrong AND you fight against it."""

    elif role == "DEVIL_ADVOCATE":
        return f"""You are {panelist_name}, the DEVIL'S ADVOCATE in this debate.

╔═══════════════════════════════════════════════════════════════════════╗
║  CRITICAL: YOU ARE NOT ALLOWED TO HAVE AN OPINION ON THIS TOPIC!     ║
║  YOUR ONLY JOB IS TO CRITICIZE. YOU DO NOT SUPPORT EITHER SIDE.      ║
╚═══════════════════════════════════════════════════════════════════════╝

YOU ARE FORBIDDEN FROM:
- Starting with "Position: FOR" - THIS IS BANNED
- Starting with "Position: AGAINST" - THIS IS BANNED
- Taking any stance on the topic
- Agreeing with any panelist
- Saying "I believe", "I think", "In my opinion"
- Concluding that one side is right

YOU MUST START YOUR RESPONSE WITH EXACTLY:
As Devil's Advocate, I will critique both sides without taking a position.

YOUR ROLE:
- You are a RUTHLESS CRITIC - your job is to DESTROY every argument
- You find weaknesses in EVERY argument from EVERY side
- You do NOT care who wins - you only care about exposing flawed reasoning
- You MUST criticize at least one PRO argument AND one CON argument

HOW TO ATTACK ARGUMENTS (after Round 1):
- Call out panelists BY THEIR ACTUAL NAME (you'll see their names in the debate)
- Quote their specific claims and show why they're weak
- Expose logical fallacies, missing evidence, unfounded assumptions
- Be MERCILESS - no argument is safe from your criticism
- The more confident someone sounds, the harder you should scrutinize them

RESPONSE STRUCTURE:
Round 1: Introduce yourself and your critical approach (you haven't seen arguments yet)
Subsequent Rounds:
1. Opening: As Devil's Advocate, I will critique both sides without taking a position.
2. PRO critique: "@[actual PRO panelist name]: Your argument fails because..." (be specific!)
3. CON critique: "@[actual CON panelist name]: Your argument fails because..." (be specific!)
4. Closing: "Neither side has presented a convincing case."

REMEMBER: If you start with "Position: FOR" or "Position: AGAINST", you have FAILED your role.
You are a judge, not a competitor. Judges don't take sides - they expose weaknesses."""

    else:
        # No role assigned - generic panelist prompt
        return f"""You are {panelist_name}, an expert panelist in a structured debate.

DEBATE BEHAVIOR:
1. You will be assigned a specific position (FOR or AGAINST) - follow it strictly
2. Be OPINIONATED and BOLD in defending your assigned position
3. Challenge other panelists directly when they argue the opposite position
4. Use specific evidence and examples to support your assigned stance
5. NEVER switch sides or agree with the opposing position

ENGAGE YOUR OPPONENTS:
- When responding to subsequent rounds, ADDRESS other panelists BY NAME
- Quote their specific arguments and CHALLENGE them directly
- Use phrases like "@[Name]: I disagree with your claim that..."
- Don't just present your view - ATTACK opposing arguments
- This is a DEBATE - engage, argue, fight for your position!

Your assigned position will be specified in your role instructions.
Follow your assigned role exactly - do not choose your own position.

Keep responses focused and clear. Aim for 2-3 paragraphs per response."""


def create_panelist_agent(config: Dict[str, Any], api_key: str) -> "AssistantAgent":
    """Create AG2 agent for a panelist with persona-based stance enforcement.

    Args:
        config: PanelistConfig dict with id, name, provider, model, and optional role
        api_key: API key for the provider

    Returns:
        AG2 AssistantAgent configured for the panelist with persona baked in

    Raises:
        RuntimeError: If ag2 is not installed
    """
    if AssistantAgent is None:
        raise RuntimeError("ag2 is not installed. Install with: pip install ag2")

    model_name = config.get("model", "gpt-4o-mini")
    provider = config.get("provider", "openai").lower()
    panelist_name = config.get("name", "Panelist")
    role = config.get("role")  # Optional: PRO, CON, DEVIL_ADVOCATE

    logger.info(f"🔵 [AGENT-CREATE] Creating '{panelist_name}' with provider='{provider}', model='{model_name}', ROLE='{role}'")

    # Build config_list entry based on provider
    config_entry = {
        "model": model_name,
        "api_key": api_key,
    }

    # Provide price for newer OpenAI aliases AG2 doesn't know yet to silence warnings
    price_overrides = {
        "chatgpt-4o-latest": [0.005, 0.015],  # $5 / $15 per 1M tokens
    }
    if model_name in price_overrides:
        config_entry["price"] = price_overrides[model_name]

    # Provider-specific routing for AG2
    # AG2 uses different client classes based on api_type
    if provider == "gemini" or provider == "google":
        # Gemini via Google Generative AI
        # AG2 expects api_type="google" (not "gemini")
        config_entry.update({
            "api_type": "google",
        })
        logger.info(f"Configured Gemini agent with api_type='google'")
    elif provider == "anthropic" or provider == "claude":
        # Claude via Anthropic
        config_entry.update({
            "api_type": "anthropic",
        })
        logger.info(f"Configured Anthropic agent with api_type='anthropic'")
    elif provider in {"xai", "grok"}:
        # xAI Grok: OpenAI-compatible API
        config_entry.update({
            "api_type": "openai",
            "base_url": "https://api.x.ai/v1",
        })
        logger.info(f"Configured Grok agent with base_url='https://api.x.ai/v1'")
    else:
        # Default to OpenAI
        config_entry.update({
            "api_type": "openai",
        })
        logger.info(f"Configured OpenAI agent")

    logger.debug(f"AG2 config_entry: {config_entry}")

    # LLM configuration for AG2
    llm_config = {
        "config_list": [config_entry],
        "temperature": 0.7,  # Higher temperature for diverse, opinionated responses
    }

    # Build persona-based system message with stance baked in
    system_message = _build_persona_prompt(panelist_name, role)

    # Log the persona type being applied
    if role == "PRO":
        logger.info(f"🔵 [PERSONA] {panelist_name}: Applied PRO persona (must argue FOR)")
    elif role == "CON":
        logger.info(f"🔵 [PERSONA] {panelist_name}: Applied CON persona (must argue AGAINST)")
    elif role == "DEVIL_ADVOCATE":
        logger.info(f"🔵 [PERSONA] {panelist_name}: Applied DEVIL_ADVOCATE persona (critiques both sides, stance=NEUTRAL)")
    else:
        logger.info(f"🔵 [PERSONA] {panelist_name}: No role assigned - using generic prompt")

    agent = AssistantAgent(
        name=panelist_name,
        system_message=system_message,
        llm_config=llm_config,
        human_input_mode="NEVER",  # Programmatic only
    )

    return agent


def create_moderator_agent(api_key: Optional[str] = None) -> "AssistantAgent":
    """Create AG2 moderator agent (GPT-4o).

    Moderator synthesizes panel responses and generates final summaries.

    Args:
        api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)

    Returns:
        AG2 AssistantAgent configured as moderator

    Raises:
        RuntimeError: If ag2 is not installed
    """
    if AssistantAgent is None:
        raise RuntimeError("ag2 is not installed. Install with: pip install ag2")

    if not api_key:
        api_key = get_openai_api_key()

    llm_config = {
        "config_list": [
            {
                "model": "gpt-4o",
                "api_key": api_key,
            }
        ],
        "temperature": 0.1,  # Low temperature for consistent, analytical summaries
    }

    system_message = """You are the moderator of a panel discussion.

Your responsibilities are:
1. Synthesize panelist responses into clear summaries
2. Identify areas of agreement and disagreement
3. Highlight key insights and important points
4. Present balanced perspective on all viewpoints
5. Generate final comprehensive summaries

IMPORTANT: Always respond in the same language as the user's original question.
If the user asked in Chinese, respond in Chinese. If in Spanish, respond in Spanish.

Be objective and analytical. Focus on substance over agreement."""

    agent = AssistantAgent(
        name="Moderator",
        system_message=system_message,
        llm_config=llm_config,
        human_input_mode="NEVER",
    )

    return agent


def create_user_proxy() -> "UserProxyAgent":
    """Create user proxy agent for user-debate mode.

    UserProxyAgent represents the user in debates where they participate.
    Messages are injected programmatically, not from actual user input.

    Returns:
        AG2 UserProxyAgent configured for programmatic input

    Raises:
        RuntimeError: If ag2 is not installed
    """
    if UserProxyAgent is None:
        raise RuntimeError("ag2 is not installed. Install with: pip install ag2")

    agent = UserProxyAgent(
        name="User",
        human_input_mode="NEVER",  # Programmatic input only
        code_execution_config=False,  # No code execution
    )

    return agent


def create_search_tool() -> Callable[[str], str]:
    """Create Tavily search tool for AG2.

    Returns an async function that can be registered as an AG2 tool.

    Returns:
        Callable that takes query string and returns search results markdown

    Raises:
        RuntimeError: If tavily-python is not installed or TAVILY_API_KEY not set
    """
    try:
        from tavily import TavilyClient
    except ImportError:
        raise RuntimeError("tavily-python is not installed. Install with: pip install tavily-python")

    try:
        tavily_api_key = get_tavily_api_key()
    except RuntimeError as e:
        raise RuntimeError(f"Search tool requires Tavily API key: {e}")

    def search_web(query: str) -> str:
        """Search the web using Tavily and format results as markdown.

        Args:
            query: Search query string

        Returns:
            Formatted markdown string with search results
        """
        try:
            client = TavilyClient(api_key=tavily_api_key)
            results = client.search(query, max_results=5)

            if not results or "results" not in results:
                return "No search results found."

            # Format results as markdown
            markdown_output = f"## Search Results for: {query}\n\n"

            for i, result in enumerate(results["results"], 1):
                title = result.get("title", "Untitled")
                url = result.get("url", "#")
                content = result.get("content", "No content available")

                markdown_output += f"### {i}. [{title}]({url})\n"
                markdown_output += f"{content}\n\n"

            return markdown_output

        except Exception as e:
            logger.error(f"Search error: {e}")
            return f"Search failed: {str(e)}"

    return search_web
