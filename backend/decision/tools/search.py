"""Web search tool for expert agents.

Wraps the Tavily search API behind a LangChain ``@tool`` so that expert
agents can retrieve up-to-date information when analysing decision options.
"""

from __future__ import annotations

import os

from langchain_core.tools import tool


def create_search_tool():
    """Return a LangChain tool that performs web searches via Tavily."""

    @tool("web_search")
    def web_search(query: str) -> str:
        """Search the web for current information on a topic.

        Use this tool when you need real-time data, recent statistics, pricing,
        or any other facts that may not be in your training data.

        Args:
            query: The search query string.
        """
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return "Error: TAVILY_API_KEY environment variable is not set."

        # Lazy import so the module can be loaded without tavily installed
        from tavily import TavilyClient  # type: ignore[import-untyped]

        client = TavilyClient(api_key=api_key)
        results = client.search(query, max_results=5, search_depth="advanced")

        formatted_parts: list[str] = []
        for idx, result in enumerate(results.get("results", []), start=1):
            title = result.get("title", "No title")
            url = result.get("url", "")
            content = result.get("content", "")
            formatted_parts.append(
                f"[{idx}] {title}\n    URL: {url}\n    {content}"
            )

        return "\n\n".join(formatted_parts) if formatted_parts else "No results found."

    return web_search
