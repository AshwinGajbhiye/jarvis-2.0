"""
Meeting & Lecture Analyzer for J.A.R.V.I.S.
Processes recorded audio using Google Gemini Multimodal Audio,
extracts executive summaries, key technical concepts, questions/answers,
and automatically synchronizes action items & homework to task_manager.py.
"""

import os
import re
import json
import datetime
from typing import Dict, Any, List, Optional

from google import genai
from google.genai import types

from config import Config
from skills.task_manager import add_task, list_tasks
from skills.meeting_recorder import get_meeting_recorder

NOTES_DIR = os.path.expanduser("~/.jarvis/notes")


def analyze_meeting_audio(audio_path: str, title: str = "Class / Meeting") -> Dict[str, Any]:
    """
    Ingest recorded audio file into Gemini 2.0 Flash,
    extract executive notes and action items, and auto-sync to task manager.
    
    Args:
        audio_path: Absolute path to the .wav audio file.
        title: Title or context of the meeting/class.
        
    Returns:
        Dictionary containing summary, key concepts, action items added, and saved note path.
    """
    if not os.path.exists(audio_path):
        return {
            "success": False,
            "error": f"Audio file not found: {audio_path}",
            "markdown": "❌ Audio recording file could not be found."
        }

    os.makedirs(NOTES_DIR, exist_ok=True)
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")

    prompt = f"""You are J.A.R.V.I.S., analyzing a recorded lecture, class, or meeting titled "{title}".
Today's date is {today_str}.

Analyze the provided audio recording carefully. Listen to what the speaker/professor/attendees are discussing and extract all important information into a clean JSON object.

Extract the following JSON structure:
{{
  "title": "Descriptive title of the lecture or meeting",
  "executive_summary": [
    "Key takeaway 1",
    "Key takeaway 2",
    "Key takeaway 3"
  ],
  "key_concepts": [
    "Important concept, formula, algorithm, theorem, or architectural decision explained",
    "Another key point or concept"
  ],
  "action_items": [
    {{
      "task": "Clear, actionable description of assignment, homework, milestone, or task mentioned",
      "priority": "high" or "normal" or "low",
      "due_date": "YYYY-MM-DD (estimate based on context e.g. 'due next Monday', or empty if unspecified)",
      "context": "Why or where this task was assigned"
    }}
  ],
  "q_and_a": [
    {{
      "question": "Question asked by student or attendee",
      "answer": "Answer given"
    }}
  ],
  "follow_up_email": "Optional polite follow-up or recap email if appropriate"
}}

Rules:
1. Capture all assignments, homework, project deadlines, and action items accurately.
2. If technical terms, code libraries, or formulas are mentioned, capture them precisely.
3. Return ONLY valid JSON, enclosed in ```json ``` codeblock or raw JSON.
"""

    api_key = Config.GEMINI_API_KEY or Config.GEMINI_API_KEY_FALLBACK
    if not api_key:
        return {
            "success": False,
            "error": "No GEMINI_API_KEY found.",
            "markdown": "❌ Cannot analyze meeting: GEMINI_API_KEY is not configured."
        }

    client = genai.Client(api_key=api_key)
    uploaded_file = None

    try:
        print(f"  📤 Uploading meeting audio to Gemini ({os.path.basename(audio_path)})...")
        uploaded_file = client.files.upload(file=audio_path)
        print(f"  🧠 Processing meeting audio with Gemini 2.0 Flash...")

        response = client.models.generate_content(
            model=Config.GEMINI_MODEL or "gemini-2.0-flash",
            contents=[uploaded_file, prompt]
        )

        raw_text = response.text or ""
        data = _extract_json_from_response(raw_text)

    except Exception as e:
        print(f"  ❌ Gemini audio analysis error: {e}")
        return {
            "success": False,
            "error": str(e),
            "markdown": f"⚠️ Meeting analysis encountered an error: {e}"
        }
    finally:
        # Clean up cloud file to maintain zero clutter
        if uploaded_file and hasattr(uploaded_file, "name"):
            try:
                client.files.delete(name=uploaded_file.name)
            except Exception:
                pass

    if not data:
        # Fallback if raw text wasn't pure JSON
        return {
            "success": True,
            "title": title,
            "markdown": raw_text,
            "action_items_added": []
        }

    # ── Auto-Sync Action Items to task_manager.py ─────────────
    action_items = data.get("action_items", [])
    added_tasks = []
    
    for item in action_items:
        task_desc = item.get("task", "").strip()
        priority = item.get("priority", "normal")
        due_date = item.get("due_date", "")

        if task_desc:
            # Prefix with class/meeting context if helpful
            formatted_task = f"[{data.get('title', title)}] {task_desc}"
            try:
                add_msg = add_task(formatted_task, priority=priority, due_date=due_date)
                added_tasks.append({
                    "task": formatted_task,
                    "priority": priority,
                    "due_date": due_date,
                    "message": add_msg
                })
            except Exception as err:
                print(f"  ⚠️ Could not add task '{task_desc}': {err}")

    # ── Format Rich Markdown Document ─────────────────────────
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    file_timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    meeting_title = data.get("title", title)

    md_lines = [
        f"# 🎙️ {meeting_title}",
        f"*Recorded & Analyzed by J.A.R.V.I.S. on {timestamp}*\n",
        "## 📋 Executive Summary"
    ]

    for bullet in data.get("executive_summary", []):
        md_lines.append(f"* {bullet}")

    if data.get("key_concepts"):
        md_lines.append("\n## 🧠 Key Concepts & Topics Explained")
        for concept in data.get("key_concepts", []):
            md_lines.append(f"* **{concept}**" if ":" not in concept else f"* {concept}")

    if action_items:
        md_lines.append(f"\n## ⚡ Action Items & Assignments ({len(added_tasks)} auto-synced to Tasks)")
        for item in action_items:
            p_icon = {"high": "🔴", "normal": "🟡", "low": "🟢"}.get(item.get("priority", "normal"), "🟡")
            due = f" *(Due: {item.get('due_date')})*" if item.get('due_date') else ""
            md_lines.append(f"* {p_icon} **{item.get('task')}**{due}")
            if item.get("context"):
                md_lines.append(f"  ↳ *Context: {item.get('context')}*")

    if data.get("q_and_a"):
        md_lines.append("\n## ❓ Questions & Answers")
        for qa in data.get("q_and_a", []):
            md_lines.append(f"* **Q:** {qa.get('question')}")
            md_lines.append(f"  ↳ **A:** {qa.get('answer')}")

    if data.get("follow_up_email"):
        md_lines.append("\n## 📧 Drafted Follow-Up Email")
        md_lines.append("```text")
        md_lines.append(data.get("follow_up_email"))
        md_lines.append("```")

    full_markdown = "\n".join(md_lines)

    # Save to disk
    note_path = os.path.join(NOTES_DIR, f"meeting_{file_timestamp}.md")
    try:
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(full_markdown)
        print(f"  📝 Saved lecture/meeting notes to: {note_path}")
    except Exception as e:
        print(f"  ⚠️ Error saving note file: {e}")

    return {
        "success": True,
        "title": meeting_title,
        "markdown": full_markdown,
        "summary": data.get("executive_summary", []),
        "action_items_added": added_tasks,
        "note_file": note_path
    }


def _extract_json_from_response(text: str) -> Optional[Dict[str, Any]]:
    """Extract and parse JSON from Gemini's response."""
    # Try finding markdown code block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        raw_json = match.group(1).strip()
    else:
        raw_json = text.strip()

    try:
        return json.loads(raw_json)
    except Exception:
        # Try finding the first { and last }
        start = raw_json.find('{')
        end = raw_json.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(raw_json[start:end+1])
            except Exception:
                pass
    return None


# ── AI Brain Skill Functions & Tool Definitions ───────────────

def start_meeting_recording(title: str = "Class / Meeting") -> str:
    """
    Start recording a class, lecture, or meeting session in the background.
    """
    rec = get_meeting_recorder()
    ok, msg = rec.start(title)
    if ok:
        return f"Recording started for '{title}', Sir. Focus on your class; I will capture all key concepts and deadlines."
    else:
        return f"Could not start recording: {msg}"


def stop_meeting_recording() -> str:
    """
    Stop the active meeting recording, analyze with Gemini, and auto-sync action items to tasks.
    """
    rec = get_meeting_recorder()
    if not rec.is_recording():
        return "There is no active meeting or class recording in progress, Sir."

    out_path, duration, title = rec.stop()
    if not out_path or duration < 1.0:
        return f"Recording for '{title}' was too short to analyze ({duration:.1f} seconds)."

    result = analyze_meeting_audio(out_path, title=title)
    if not result.get("success"):
        return f"Completed recording for '{title}' ({duration:.1f}s), but analysis failed: {result.get('error')}"

    num_tasks = len(result.get("action_items_added", []))
    summary_bullets = "\n".join(f"• {s}" for s in result.get("summary", [])[:3])
    
    return f"""### 🎙️ Lecture / Meeting Notes: {result.get('title')}
*(Duration: {int(duration // 60)}m {int(duration % 60)}s | {num_tasks} action items synced to tasks)*

{summary_bullets}

Full structured notes saved to `{result.get('note_file')}`.
"""


def list_meeting_notes() -> str:
    """
    List all previously saved class and meeting notes.
    """
    if not os.path.exists(NOTES_DIR):
        return "No meeting notes found, Sir."

    files = sorted(
        [f for f in os.listdir(NOTES_DIR) if f.endswith(".md")],
        reverse=True
    )
    if not files:
        return "No meeting or lecture notes recorded yet."

    lines = ["Here are your recent class and meeting notes:"]
    for f in files[:10]:
        path = os.path.join(NOTES_DIR, f)
        try:
            with open(path, "r", encoding="utf-8") as file:
                first_line = file.readline().strip().replace("# 🎙️ ", "")
                lines.append(f"• **{first_line}** (`{f}`)")
        except Exception:
            lines.append(f"• `{f}`")

    return "\n".join(lines)


def get_latest_meeting_summary() -> str:
    """
    Read the summary of the most recently recorded meeting or lecture.
    """
    if not os.path.exists(NOTES_DIR):
        return "No meeting notes found."

    files = sorted(
        [f for f in os.listdir(NOTES_DIR) if f.endswith(".md")],
        reverse=True
    )
    if not files:
        return "You have not recorded any meetings or classes yet, Sir."

    latest_path = os.path.join(NOTES_DIR, files[0])
    try:
        with open(latest_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Could not read latest note: {e}"


MEETING_TOOLS = [
    {
        "name": "start_meeting_recording",
        "description": "Start recording a Google Meet, Zoom call, lecture, or class in the background to extract notes and action items.",
        "function": start_meeting_recording,
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "The title or subject of the meeting/class (e.g. 'Operating Systems Lecture' or 'Sprint Planning')"
                }
            },
            "required": []
        }
    },
    {
        "name": "stop_meeting_recording",
        "description": "Stop the active meeting/class recording, process the audio with Gemini, extract notes, and auto-sync assignments/action items to tasks.",
        "function": stop_meeting_recording,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "list_meeting_notes",
        "description": "List past saved class notes, meeting minutes, and lecture summaries.",
        "function": list_meeting_notes,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "get_latest_meeting_summary",
        "description": "Read the full study notes and summary of the most recently recorded meeting or class.",
        "function": get_latest_meeting_summary,
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
]
