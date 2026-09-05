# Jarvis AI — LeetCode Tracking Skill
import requests
import os
from config import Config

def _run_graphql_query(query: str, variables: dict):
    url = "https://leetcode.com/graphql"
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://leetcode.com"
    }
    payload = {
        "query": query,
        "variables": variables
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def check_leetcode_progress(username: str = None) -> str:
    """
    Check the LeetCode progress for a user, including total problems solved and recent submissions.
    If no username is provided, it uses the configured username.
    """
    username = username or Config.LEETCODE_USERNAME
    if not username:
        return "I don't have a LeetCode username configured, Sir. Please add LEETCODE_USERNAME to your .env file."
    
    query = """
    query getUserProfile($username: String!) {
      matchedUser(username: $username) {
        username
        submitStats: submitStatsGlobal {
          acSubmissionNum {
            difficulty
            count
            submissions
          }
        }
      }
      recentAcSubmissionList(username: $username, limit: 1) {
        title
        timestamp
      }
    }
    """
    
    data = _run_graphql_query(query, {"username": username})
    if "error" in data:
        return f"I encountered an error connecting to LeetCode, Sir: {data['error']}"
        
    if not data.get("data") or not data["data"].get("matchedUser"):
        return f"I could not find a LeetCode profile for '{username}', Sir."
        
    user_data = data["data"]["matchedUser"]
    stats = user_data["submitStats"]["acSubmissionNum"]
    
    total_solved = 0
    easy, medium, hard = 0, 0, 0
    for stat in stats:
        diff = stat["difficulty"]
        if diff == "All":
            total_solved = stat["count"]
        elif diff == "Easy":
            easy = stat["count"]
        elif diff == "Medium":
            medium = stat["count"]
        elif diff == "Hard":
            hard = stat["count"]
            
    recent_submissions = data["data"].get("recentAcSubmissionList", [])
    
    msg = f"LeetCode Progress for {username}:\n"
    msg += f"Total Solved: {total_solved} (Easy: {easy}, Medium: {medium}, Hard: {hard})\n"
    
    if recent_submissions:
        import datetime
        recent = recent_submissions[0]
        title = recent.get("title", "Unknown")
        ts = int(recent.get("timestamp", 0))
        date_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %I:%M %p")
        msg += f"Most recent accepted submission: '{title}' on {date_str}."
    else:
        msg += "No recent accepted submissions found."
        
    return msg

def get_daily_challenge() -> str:
    """
    Fetch today's official LeetCode Daily Challenge.
    """
    query = """
    query questionOfToday {
      activeDailyCodingChallengeQuestion {
        date
        link
        question {
          title
          difficulty
          topicTags {
            name
          }
        }
      }
    }
    """
    data = _run_graphql_query(query, {})
    if "error" in data:
        return f"Error fetching daily challenge: {data['error']}"
        
    try:
        challenge = data["data"]["activeDailyCodingChallengeQuestion"]
        date = challenge["date"]
        link = "https://leetcode.com" + challenge["link"]
        q = challenge["question"]
        title = q["title"]
        difficulty = q["difficulty"]
        topics = ", ".join([t["name"] for t in q["topicTags"]])
        
        msg = f"Today's LeetCode Daily Challenge ({date}):\n"
        msg += f"**{title}** ({difficulty})\n"
        msg += f"Topics: {topics}\n"
        msg += f"Link: {link}"
        return msg
    except Exception as e:
        return "Could not parse the daily challenge data."

def sync_daily_dsa_task() -> None:
    """
    Fetch today's LeetCode Daily Challenge and automatically add it 
    to the task list if it isn't already there.
    """
    import datetime
    from skills.task_manager import _load_tasks, add_task

    query = """
    query questionOfToday {
      activeDailyCodingChallengeQuestion {
        date
        question {
          title
          difficulty
        }
      }
    }
    """
    data = _run_graphql_query(query, {})
    if "error" in data:
        return
        
    try:
        challenge = data["data"]["activeDailyCodingChallengeQuestion"]
        today = challenge["date"]  # e.g., "2026-07-08"
        title = challenge["question"]["title"]
        difficulty = challenge["question"]["difficulty"]
        
        task_desc = f"LeetCode Daily: {title} ({difficulty})"
        
        # Check if it already exists
        tasks = _load_tasks()
        exists = False
        for t in tasks:
            if t["due_date"] == today and "LeetCode Daily" in t["task"]:
                exists = True
                break
                
        if not exists:
            # Add it with high priority
            add_task(task=task_desc, priority="high", due_date=today)
            
    except Exception:
        pass


# ── NeetCode Roadmap Tracking ─────────────────────────────────

NEETCODE_PROGRESS_FILE = os.path.join(Config.HISTORY_DIR, "neetcode_progress.json")

def _load_neetcode_progress() -> list:
    """Load solved NeetCode problems from disk."""
    if os.path.exists(NEETCODE_PROGRESS_FILE):
        try:
            import json
            with open(NEETCODE_PROGRESS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def _save_neetcode_progress(solved: list):
    """Save solved NeetCode problems to disk."""
    import json
    os.makedirs(Config.HISTORY_DIR, exist_ok=True)
    with open(NEETCODE_PROGRESS_FILE, "w") as f:
        json.dump(solved, f, indent=2)

def mark_neetcode_problem_solved(problem_name: str) -> None:
    """Mark a specific NeetCode problem as solved."""
    solved = _load_neetcode_progress()
    if problem_name not in solved:
        solved.append(problem_name)
        _save_neetcode_progress(solved)

def sync_neetcode_tasks() -> None:
    """
    Ensure there are 5 uncompleted NeetCode questions in the task manager.
    Follows the NeetCode roadmap order.
    """
    from skills.task_manager import _load_tasks, add_task
    from skills.neetcode_150_data import NEETCODE_150_ROADMAP
    
    solved = _load_neetcode_progress()
    tasks = _load_tasks()
    
    # Count how many NeetCode tasks are already pending
    pending_neetcode_tasks = []
    for t in tasks:
        if not t["completed"] and t["task"].startswith("NeetCode Roadmap:"):
            # Extract problem name: "NeetCode Roadmap: Arrays & Hashing - Two Sum"
            parts = t["task"].split(" - ")
            if len(parts) > 1:
                pending_neetcode_tasks.append(parts[-1].strip())
    
    # We want exactly 5 active tasks
    needed = 5 - len(pending_neetcode_tasks)
    if needed <= 0:
        return
        
    # Find the next 'needed' unsolved problems in the roadmap
    to_add = []
    for topic, problems in NEETCODE_150_ROADMAP.items():
        for prob in problems:
            if prob not in solved and prob not in pending_neetcode_tasks:
                to_add.append((topic, prob))
                if len(to_add) == needed:
                    break
        if len(to_add) == needed:
            break
            
    # Add them to the task manager
    import datetime
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    for topic, prob in to_add:
        desc = f"NeetCode Roadmap: {topic} - {prob}"
        add_task(task=desc, priority="high", due_date=today)


def get_neetcode_status_and_next_questions() -> str:
    """
    Check NeetCode profile progress and return the next 5 unsolved questions from different topics.
    """
    from skills.neetcode_150_data import NEETCODE_150_ROADMAP
    solved = _load_neetcode_progress()
    
    total_neetcode = sum(len(probs) for probs in NEETCODE_150_ROADMAP.values())
    total_solved = len(solved)
    
    msg = f"**NeetCode 150 Progress:**\n"
    msg += f"You have solved **{total_solved} / {total_neetcode}** questions.\n\n"
    
    msg += "**Your Next 5 Recommended Questions (Cross-Topic):**\n"
    
    next_questions = []
    # Try to get 1 unsolved question from each topic until we hit 5
    for topic, problems in NEETCODE_150_ROADMAP.items():
        for prob in problems:
            if prob not in solved:
                next_questions.append((topic, prob))
                break # Move to next topic to ensure variety
                
        if len(next_questions) == 5:
            break
            
    # If we still don't have 5 (maybe only 1 topic left with unsolved problems), just fill the rest
    if len(next_questions) < 5:
        for topic, problems in NEETCODE_150_ROADMAP.items():
            for prob in problems:
                if prob not in solved and (topic, prob) not in next_questions:
                    next_questions.append((topic, prob))
                if len(next_questions) == 5:
                    break
            if len(next_questions) == 5:
                break
                
    if not next_questions:
        msg += "Congratulations, Sir! You have completed the entire NeetCode 150 Roadmap!"
        return msg
        
    for i, (topic, prob) in enumerate(next_questions, 1):
        msg += f"{i}. **{prob}** (Topic: {topic})\n"
        
    return msg


LEETCODE_TOOLS = [
    {
        "name": "check_leetcode_progress",
        "description": "Check the user's LeetCode progress, total problems solved, and their most recent accepted submission.",
        "function": check_leetcode_progress,
        "parameters": {
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "Optional LeetCode username. If omitted, uses the default configured user.",
                }
            }
        },
    },
    {
        "name": "get_daily_challenge",
        "description": "Get today's official LeetCode daily coding challenge question.",
        "function": get_daily_challenge,
    },
    {
        "name": "get_neetcode_status_and_next_questions",
        "description": "Check the user's NeetCode profile progress, count how many questions they have solved, and return the next 5 unsolved questions from different topics.",
        "function": get_neetcode_status_and_next_questions,
    }
]
