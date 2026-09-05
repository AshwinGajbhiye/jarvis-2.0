# Jarvis AI — Web Search Skill
# Gives Jarvis the ability to search the web and fetch webpage content.
# Uses DuckDuckGo (free, no API key required).

import requests
from bs4 import BeautifulSoup


def web_search(query: str, max_results: int = 5) -> str:
    """
    Search the web using DuckDuckGo and return results.
    
    Args:
        query: Search query string
        max_results: Number of results to return (default 5)
    
    Returns:
        Formatted search results with titles, URLs, and snippets
    """
    try:
        from ddgs import DDGS
        
        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append(r)
        
        if not results:
            return f"No search results found for '{query}'."
        
        lines = [f"**🔍 Web Search Results for: '{query}'**\n"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "No title")
            url = r.get("href", r.get("link", ""))
            snippet = r.get("body", r.get("snippet", ""))
            lines.append(f"**{i}. {title}**")
            lines.append(f"   {snippet}")
            lines.append(f"   🔗 {url}\n")
        
        return "\n".join(lines)
    
    except ImportError:
        return "Web search is not available. Please install: pip install duckduckgo-search"
    except Exception as e:
        return f"Search failed: {str(e)}"


def fetch_webpage(url: str) -> str:
    """
    Fetch and extract the main text content from a webpage.
    
    Args:
        url: The URL to fetch
    
    Returns:
        Extracted text content from the page (truncated to ~3000 chars)
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Remove script and style elements
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        
        # Get text content
        text = soup.get_text(separator="\n", strip=True)
        
        # Clean up excessive whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        cleaned = "\n".join(lines)
        
        # Truncate to prevent overwhelming the context window
        if len(cleaned) > 3000:
            cleaned = cleaned[:3000] + "\n\n... [Content truncated — page is very long]"
        
        return f"**📄 Content from {url}:**\n\n{cleaned}"
    
    except Exception as e:
        return f"Failed to fetch webpage: {str(e)}"


# ── Tool Definitions for Gemini ──────────────────────────────
WEB_SEARCH_TOOLS = [
    {
        "name": "web_search",
        "description": "Search the web using DuckDuckGo. Use when the user asks to search for something online, find information, look up current events, research a topic, or when you need real-time data you don't have in training.",
        "function": web_search,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 5, max 10)",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_webpage",
        "description": "Fetch and read the text content of a specific webpage/URL. Use when the user asks to read a page, get details from a link, or when you need to extract information from a specific URL.",
        "function": fetch_webpage,
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL to fetch (must start with http:// or https://)",
                },
            },
            "required": ["url"],
        },
    },
]
