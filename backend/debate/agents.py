"""AG2 agent factory functions for debate participants.

Creates and configures agents for panelists, moderator, and user participation.
"""

from typing import Dict, Any, Optional, Callable
import logging

try:
    import ag2
    from ag2 import AssistantAgent, UserProxyAgent
except ImportError:
    ag2 = None
    AssistantAgent = None
    UserProxyAgent = None

from config import get_tavily_api_key, get_openai_api_key

logger = logging.getLogger(__name__)


def create_panelist_agent(config: Dict[str, Any], api_key: str) -> "AssistantAgent":
    """Create AG2 agent for a panelist.

    Args:
        config: PanelistConfig dict with id, name, provider, model
        api_key: API key for the provider

    Returns:
        AG2 AssistantAgent configured for the panelist

    Raises:
        RuntimeError: If ag2 is not installed
    """
    if AssistantAgent is None:
        raise RuntimeError("ag2 is not installed. Install with: pip install ag2")

    model_name = config.get("model", "gpt-4o-mini")
    panelist_name = config.get("name", "Panelist")

    # LLM configuration for AG2
    llm_config = {
        "config_list": [
            {
                "model": model_name,
                "api_key": api_key,
            }
        ],
        "temperature": 0.2,  # Slightly opinionated but consistent
    }

    # System message for panelist role
    system_message = f"""You are {panelist_name}, an expert panelist in a structured discussion.

Your role is to:
1. Provide thoughtful, substantive responses to the topic
2. Consider different perspectives
3. Be respectful to other panelists
4. Support your positions with reasoning
5. Engage constructively with differing viewpoints

Keep responses focused and clear. Aim for 2-3 paragraphs per response."""

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
