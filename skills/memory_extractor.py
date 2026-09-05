# Jarvis AI — Memory Extractor
# Automatically extracts durable personal facts from conversations.
# Inspired by Odysseus's memory_extractor.py.
# Facts persist across sessions in ~/.jarvis/history/user_facts.json.

import json
import os
import datetime
import re
from config import Config

FACTS_FILE = os.path.join(Config.HISTORY_DIR, "user_facts.json")

# Categories for extracted facts
VALID_CATEGORIES = {"identity", "preference", "fact", "contact", "project", "goal"}

EXTRACT_PROMPT = """Analyze the conversation below and extract ONLY durable personal facts about the user that would be useful across many future conversations.

Good examples: name, job title, city, university, family members, long-term projects, strong preferences, skills, tools they use.
Bad examples: what they asked about today, temporary moods, generic statements, things the assistant said, one-off tasks, opinions on the current topic.

Rules:
- MAX 2 facts per conversation — only the most important
- Only extract facts the USER stated or clearly implied
- Each fact must be a single short sentence (under 15 words)
- If a fact is similar to something likely already known, skip it
- If nothing durable was revealed, return []

Return a JSON array of objects with 'text' and 'category' fields.
Categories: 'identity', 'preference', 'fact', 'contact', 'project', 'goal'

Return ONLY valid JSON, no markdown fences.

Conversation:
{conversation}

Existing known facts (DO NOT re-extract these):
{existing_facts}"""


def _load_facts() -> list:
    """Load existing user facts from disk."""
    os.makedirs(Config.HISTORY_DIR, exist_ok=True)
    if os.path.exists(FACTS_FILE):
        try:
            with open(FACTS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_facts(facts: list):
    """Save user facts to disk."""
    os.makedirs(Config.HISTORY_DIR, exist_ok=True)
    with open(FACTS_FILE, "w") as f:
        json.dump(facts, f, indent=2)


def get_facts_for_prompt() -> str:
    """
    Get all stored facts formatted for injection into the system prompt.
    Called on boot to give Jarvis persistent memory of the user.
    
    Returns:
        Formatted string of facts, or empty string if none exist.
    """
    facts = _load_facts()
    if not facts:
        return ""
    
    lines = ["\n\nThings you remember about the user from previous conversations:"]
    for f in facts:
        category = f.get("category", "fact")
        text = f.get("text", "")
        lines.append(f"- [{category}] {text}")
    
    return "\n".join(lines)


def _clean_fact(text: str) -> str:
    """Clean and validate a single fact string."""
    text = re.sub(r"\s+", " ", text or "").strip(" .,!?:;\"'`""''")
    if not text or len(text) > 100:
        return ""
    if re.search(r"https?://|@|[{}<>]", text):
        return ""
    return text


def _is_duplicate(new_fact: str, existing_facts: list) -> bool:
    """Check if a fact is too similar to an existing one."""
    new_lower = new_fact.lower()
    for f in existing_facts:
        existing = f.get("text", "").lower()
        # Exact match
        if new_lower == existing:
            return True
        # High word overlap (>70%)
        new_words = set(new_lower.split())
        existing_words = set(existing.split())
        if new_words and existing_words:
            overlap = len(new_words & existing_words) / max(len(new_words), len(existing_words))
            if overlap > 0.7:
                return True
    return False


def extract_facts_from_conversation(conversation_messages: list, llm_client, model: str):
    """
    Background task: Extract facts from recent conversation messages.
    
    Args:
        conversation_messages: List of recent message dicts with 'role' and 'text'
        llm_client: The genai.Client instance
        model: The model name to use
    """
    from google.genai import types
    
    if not conversation_messages or len(conversation_messages) < 2:
        return
    
    existing_facts = _load_facts()
    
    # Format conversation for the prompt
    conv_text = ""
    for msg in conversation_messages[-6:]:  # Last 6 messages
        role = msg.get("role", "unknown")
        text = msg.get("text", "")
        if text:
            conv_text += f"{role}: {text}\n"
    
    if not conv_text.strip():
        return
    
    # Format existing facts for dedup
    existing_text = "\n".join(f"- {f['text']}" for f in existing_facts) if existing_facts else "None"
    
    prompt = EXTRACT_PROMPT.format(
        conversation=conv_text,
        existing_facts=existing_text
    )
    
    try:
        response = llm_client.models.generate_content(
            model=model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1,  # Low temperature for factual extraction
            )
        )
        
        raw_text = response.text.strip()
        
        # Strip markdown fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        
        new_facts = json.loads(raw_text)
        
        if not isinstance(new_facts, list):
            return
        
        added = 0
        for fact in new_facts[:2]:  # Max 2 per extraction
            if not isinstance(fact, dict):
                continue
            text = _clean_fact(fact.get("text", ""))
            category = fact.get("category", "fact")
            
            if not text:
                continue
            if category not in VALID_CATEGORIES:
                category = "fact"
            if _is_duplicate(text, existing_facts):
                continue
            
            existing_facts.append({
                "text": text,
                "category": category,
                "extracted_at": datetime.datetime.now().isoformat(),
            })
            added += 1
        
        if added > 0:
            _save_facts(existing_facts)
            
    except Exception:
        # Silently fail — this is a background enhancement, not critical
        pass
