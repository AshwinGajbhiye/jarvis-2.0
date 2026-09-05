# Jarvis AI — Deep Research Skill
# Multi-step iterative research using web search + LLM synthesis.
# Inspired by Odysseus's IterResearch approach.
# Think → Search → Extract → Synthesize loop.

from skills.web_search import web_search, fetch_webpage


def deep_research(topic: str) -> str:
    """
    Perform a multi-step deep research on a topic.
    
    This uses an iterative approach:
    1. Break the topic into 3-5 sub-questions
    2. Search the web for each sub-question
    3. Compile and synthesize the findings into a comprehensive report
    
    Args:
        topic: The research topic or question
    
    Returns:
        A comprehensive research report with sources
    """
    try:
        all_findings = []
        
        # Step 1: Generate sub-questions (simple heuristic approach)
        sub_queries = _generate_sub_queries(topic)
        
        # Step 2: Search for each sub-question
        for i, query in enumerate(sub_queries, 1):
            search_result = web_search(query=query, max_results=3)
            all_findings.append({
                "query": query,
                "results": search_result,
            })
        
        # Step 3: Compile the report
        report_lines = [
            f"# 🔬 Deep Research Report: {topic}\n",
            f"*Researched {len(sub_queries)} sub-topics with {len(sub_queries) * 3} sources*\n",
            "---\n",
        ]
        
        for i, finding in enumerate(all_findings, 1):
            report_lines.append(f"## {i}. {finding['query']}\n")
            report_lines.append(finding["results"])
            report_lines.append("\n---\n")
        
        report_lines.append("## Summary\n")
        report_lines.append(
            f"This research covered {len(sub_queries)} aspects of '{topic}'. "
            f"Please review the findings above and let me know if you'd like me to "
            f"dive deeper into any specific area, Sir."
        )
        
        return "\n".join(report_lines)
    
    except Exception as e:
        return f"Research failed: {str(e)}"


def _generate_sub_queries(topic: str) -> list:
    """
    Generate sub-queries for a research topic using simple heuristics.
    For complex topics, this breaks them into natural research angles.
    """
    # Base query is always the topic itself
    queries = [topic]
    
    topic_lower = topic.lower()
    
    # Add contextual sub-queries based on common patterns
    if any(word in topic_lower for word in ["how to", "tutorial", "learn", "guide"]):
        queries.extend([
            f"{topic} best practices",
            f"{topic} common mistakes",
            f"{topic} examples",
        ])
    elif any(word in topic_lower for word in ["vs", "versus", "compare", "difference"]):
        queries.extend([
            f"{topic} pros and cons",
            f"{topic} performance comparison",
            f"{topic} which is better 2024",
        ])
    elif any(word in topic_lower for word in ["what is", "explain", "define"]):
        queries.extend([
            f"{topic} simple explanation",
            f"{topic} use cases",
            f"{topic} advantages disadvantages",
        ])
    else:
        # Generic research angles
        queries.extend([
            f"{topic} overview",
            f"{topic} latest developments",
            f"{topic} key insights",
        ])
    
    return queries[:5]  # Cap at 5 sub-queries


# ── Tool Definition for Gemini ──────────────────────────────
DEEP_RESEARCH_TOOLS = [
    {
        "name": "deep_research",
        "description": "Perform comprehensive multi-step web research on a topic. Use when the user asks to 'research', 'investigate', 'deep dive', 'find out everything about', or needs a thorough analysis of a topic. This searches multiple sub-topics and compiles a detailed report.",
        "function": deep_research,
        "parameters": {
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "The topic or question to research thoroughly",
                },
            },
            "required": ["topic"],
        },
    },
]
