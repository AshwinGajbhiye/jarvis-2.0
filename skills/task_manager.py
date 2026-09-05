# Jarvis AI — Task Manager Skill
# Persistent task/to-do list stored in ~/.jarvis/history/tasks.json
# Tasks survive across restarts and conversations.

import json
import os
import datetime
from config import Config


TASKS_FILE = os.path.join(Config.HISTORY_DIR, "tasks.json")


def _load_tasks() -> list:
    """Load tasks from disk."""
    os.makedirs(Config.HISTORY_DIR, exist_ok=True)
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def _save_tasks(tasks: list):
    """Save tasks to disk."""
    os.makedirs(Config.HISTORY_DIR, exist_ok=True)
    with open(TASKS_FILE, "w") as f:
        json.dump(tasks, f, indent=2)


def add_task(task: str, priority: str = "normal", due_date: str = "") -> str:
    """
    Add a new task to the to-do list.
    
    Args:
        task: The task description
        priority: 'high', 'normal', or 'low'
        due_date: Optional due date in YYYY-MM-DD format. If empty, defaults to today.
    
    Returns:
        Confirmation message
    """
    tasks = _load_tasks()

    if not due_date:
        due_date = datetime.datetime.now().strftime("%Y-%m-%d")

    next_id = max((t["id"] for t in tasks), default=0) + 1

    new_task = {
        "id": next_id,
        "task": task,
        "priority": priority.lower(),
        "due_date": due_date,
        "completed": False,
        "created_at": datetime.datetime.now().isoformat(),
    }

    tasks.append(new_task)
    _save_tasks(tasks)

    return f"Task added: '{task}' (Priority: {priority}, Due: {due_date})"


def complete_task(task_id: int) -> str:
    """
    Mark a task as completed by its ID number.
    
    Args:
        task_id: The ID number of the task to complete
    
    Returns:
        Confirmation message
    """
    tasks = _load_tasks()

    for t in tasks:
        if t["id"] == task_id:
            t["completed"] = True
            t["completed_at"] = datetime.datetime.now().isoformat()
            _save_tasks(tasks)
            
            # Intercept NeetCode Roadmap tasks and update progress automatically
            if t["task"].startswith("NeetCode Roadmap:"):
                parts = t["task"].split(" - ")
                if len(parts) > 1:
                    problem_name = parts[-1].strip()
                    try:
                        from skills.leetcode_tracker import mark_neetcode_problem_solved
                        mark_neetcode_problem_solved(problem_name)
                    except Exception:
                        pass
                        
            return f"Task #{task_id} marked as complete: '{t['task']}'"

    return f"No task found with ID #{task_id}."


def remove_task(task_id: int) -> str:
    """
    Remove a task from the list by its ID number.
    
    Args:
        task_id: The ID number of the task to remove
    
    Returns:
        Confirmation message
    """
    tasks = _load_tasks()
    original_len = len(tasks)
    tasks = [t for t in tasks if t["id"] != task_id]

    if len(tasks) < original_len:
        _save_tasks(tasks)
        return f"Task #{task_id} removed from the list."
    return f"No task found with ID #{task_id}."


def list_tasks(show_completed: bool = False) -> str:
    """
    List all tasks, optionally including completed ones.
    
    Args:
        show_completed: If True, also show completed tasks
    
    Returns:
        Formatted task list
    """
    tasks = _load_tasks()

    if not tasks:
        return "Your task list is empty, Sir. No pending tasks."

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    # Separate today's tasks and future tasks
    today_tasks = [t for t in tasks if t["due_date"] == today and (not t["completed"] or show_completed)]
    future_tasks = [t for t in tasks if t["due_date"] != today and (not t["completed"] or show_completed)]

    lines = []

    if today_tasks:
        lines.append("**📋 Today's Tasks:**")
        for t in today_tasks:
            status = "✅" if t["completed"] else "⬜"
            priority_icon = {"high": "🔴", "normal": "🟡", "low": "🟢"}.get(t["priority"], "🟡")
            lines.append(f"  {status} #{t['id']} {priority_icon} {t['task']}")

    if future_tasks:
        lines.append("\n**📅 Upcoming Tasks:**")
        for t in sorted(future_tasks, key=lambda x: x["due_date"]):
            status = "✅" if t["completed"] else "⬜"
            priority_icon = {"high": "🔴", "normal": "🟡", "low": "🟢"}.get(t["priority"], "🟡")
            lines.append(f"  {status} #{t['id']} {priority_icon} {t['task']} (Due: {t['due_date']})")

    if not lines:
        return "All tasks are completed! Well done, Sir."

    return "\n".join(lines)


def get_today_tasks_for_panel() -> list:
    """
    Get today's incomplete tasks as a list of dicts for the GUI panel.
    This is called directly by the GUI, not by Gemini.
    
    Returns:
        List of task dicts with 'id', 'task', 'priority', 'completed'
    """
    tasks = _load_tasks()
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    return [t for t in tasks if t["due_date"] == today]


def clear_completed_tasks() -> str:
    """Remove all completed tasks from the list."""
    tasks = _load_tasks()
    remaining = [t for t in tasks if not t["completed"]]
    removed_count = len(tasks) - len(remaining)
    _save_tasks(remaining)
    return f"Cleared {removed_count} completed task(s) from the list."


# ── Tool Definitions for Gemini ──────────────────────────────
TASK_TOOLS = [
    {
        "name": "add_task",
        "description": "Add a new task or to-do item to the user's task list. Use this when the user says 'add task', 'remind me to', 'I need to', 'put X on my list', etc.",
        "function": add_task,
        "parameters": {
            "type": "object",
            "properties": {
                "task": {
                    "type": "string",
                    "description": "The task description",
                },
                "priority": {
                    "type": "string",
                    "description": "Priority level: 'high', 'normal', or 'low'. Default is 'normal'.",
                    "enum": ["high", "normal", "low"],
                },
                "due_date": {
                    "type": "string",
                    "description": "Due date in YYYY-MM-DD format. Leave empty for today.",
                },
            },
            "required": ["task"],
        },
    },
    {
        "name": "complete_task",
        "description": "Mark a task as completed by its ID number. Use when the user says 'done with task X', 'completed task X', 'mark X as done', etc.",
        "function": complete_task,
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "The ID number of the task to complete",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "remove_task",
        "description": "Remove/delete a task from the list by its ID number.",
        "function": remove_task,
        "parameters": {
            "type": "object",
            "properties": {
                "task_id": {
                    "type": "integer",
                    "description": "The ID number of the task to remove",
                },
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "list_tasks",
        "description": "Show all tasks on the to-do list. Use when the user asks 'what are my tasks', 'show my to-do list', 'what do I need to do today', etc.",
        "function": list_tasks,
        "parameters": {
            "type": "object",
            "properties": {
                "show_completed": {
                    "type": "boolean",
                    "description": "Whether to include completed tasks. Default is False.",
                },
            },
        },
    },
    {
        "name": "clear_completed_tasks",
        "description": "Remove all completed tasks from the list to clean up.",
        "function": clear_completed_tasks,
        "parameters": {},
    },
]
