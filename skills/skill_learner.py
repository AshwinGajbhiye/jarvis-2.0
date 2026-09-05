# Jarvis AI — Skill Auto-Extractor
# When Jarvis uses multiple tool calls to solve a complex task,
# this module distills the approach into a reusable "skill" stored on disk.
# Next time a similar task comes up, Jarvis can reference the skill directly.

import json
import os
import datetime
import re
from config import Config

SKILLS_DIR = os.path.join(Config.HISTORY_DIR, "learned_skills")
SKILLS_FILE = os.path.join(SKILLS_DIR, "skills.json")

# Only extract skills when the agent used ≥2 tool calls
MIN_TOOL_CALLS = 2

SKILL_EXTRACT_PROMPT = """You are analyzing an AI assistant's work session. The assistant used {tool_count} tool calls to complete the user's request.

Extract a reusable 'skill' ONLY IF the session contains a concrete, repeatable procedure the assistant could follow to solve a similar problem next time.

Return null (the bare word, no JSON) when the session is NOT a reusable procedure, including:
- A one-off, personal, or context-specific task that won't recur
- A pure question/answer or explanation with no transferable method
- The assistant failed or the approach is not worth repeating
- Casual conversation

When a genuine reusable procedure exists, return a JSON object with:
- "title": short name (under 10 words)
- "problem": what was the challenge (1-2 sentences)
- "solution": what worked (1-2 sentences)
- "steps": array of step-by-step instructions (3-7 short steps)
- "tags": array of relevant keywords (3-5 tags)

Be conservative: if in doubt, return null.
Return ONLY valid JSON (or the bare word null), no markdown fences.

Conversation:
{conversation}"""


def _load_skills() -> list:
    """Load learned skills from disk."""
    os.makedirs(SKILLS_DIR, exist_ok=True)
    if os.path.exists(SKILLS_FILE):
        try:
            with open(SKILLS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_skills(skills: list):
    """Save learned skills to disk."""
    os.makedirs(SKILLS_DIR, exist_ok=True)
    with open(SKILLS_FILE, "w") as f:
        json.dump(skills, f, indent=2)


def _has_duplicate_title(skills: list, title: str) -> bool:
    """Check if a skill with this title already exists."""
    title_lower = title.lower()
    return any(s.get("title", "").lower() == title_lower for s in skills)


def get_relevant_skills(user_input: str) -> str:
    """
    Find skills relevant to the current user query using keyword matching.
    Injected into the system prompt to help Jarvis solve recurring problems faster.
    
    Args:
        user_input: The user's current message
    
    Returns:
        Formatted string of relevant skills, or empty string if none match
    """
    skills = _load_skills()
    if not skills:
        return ""
    
    # Tokenize user input
    user_words = set(re.sub(r"[^\w\s]", "", user_input.lower()).split())
    if not user_words:
        return ""
    
    # Score each skill by tag/title overlap
    scored = []
    for skill in skills:
        tags = set(t.lower() for t in skill.get("tags", []))
        title_words = set(skill.get("title", "").lower().split())
        all_keywords = tags | title_words
        
        overlap = len(user_words & all_keywords)
        if overlap > 0:
            scored.append((overlap, skill))
    
    if not scored:
        return ""
    
    # Return top 2 most relevant skills
    scored.sort(key=lambda x: x[0], reverse=True)
    top_skills = scored[:2]
    
    lines = ["\n\nYou have learned these procedures from previous sessions that may be relevant:"]
    for _, skill in top_skills:
        lines.append(f"\n**Skill: {skill['title']}**")
        lines.append(f"Problem: {skill['problem']}")
        lines.append(f"Solution: {skill['solution']}")
        lines.append("Steps:")
        for i, step in enumerate(skill.get("steps", []), 1):
            lines.append(f"  {i}. {step}")
    
    return "\n".join(lines)


def extract_skill_from_conversation(conversation_messages: list, tool_calls_count: int, llm_client, model: str):
    """
    Background task: Extract a reusable skill from a complex interaction.
    
    Args:
        conversation_messages: List of recent message dicts
        tool_calls_count: How many tool calls were made in this interaction
        llm_client: The genai.Client instance
        model: The model name
    """
    from google.genai import types
    
    if tool_calls_count < MIN_TOOL_CALLS:
        return
    
    existing_skills = _load_skills()
    
    # Format conversation
    conv_text = ""
    for msg in conversation_messages[-12:]:
        role = msg.get("role", "unknown")
        text = msg.get("text", "")
        if text:
            conv_text += f"{role}: {text}\n"
    
    if not conv_text.strip():
        return
    
    prompt = SKILL_EXTRACT_PROMPT.format(
        tool_count=tool_calls_count,
        conversation=conv_text
    )
    
    try:
        response = llm_client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,
            )
        )
        
        raw_text = response.text.strip()
        
        # Handle "null" response
        if raw_text.lower() == "null":
            return
        
        # Strip markdown fences
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        
        skill = json.loads(raw_text)
        
        if not isinstance(skill, dict):
            return
        
        title = skill.get("title", "")
        if not title or _has_duplicate_title(existing_skills, title):
            return
        
        # Validate required fields
        if not all(k in skill for k in ("title", "problem", "solution", "steps")):
            return
        
        skill["learned_at"] = datetime.datetime.now().isoformat()
        skill["uses"] = 0
        
        existing_skills.append(skill)
        _save_skills(existing_skills)
        
    except Exception:
        pass
