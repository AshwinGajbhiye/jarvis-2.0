# Jarvis AI — The Brain
# Central intelligence layer using Google Gemini 2.0 Flash with function calling.
# Gemini decides WHICH skill to invoke based on natural language — no brittle string matching.

import json
from google import genai
from google.genai import types

from config import Config
from memory import Memory
from quota_manager import QuotaManager

# Import all skill tool definitions
from skills.system_info import SYSTEM_TOOLS
from skills.app_launcher import APP_TOOLS
from skills.browser_automation import BROWSER_TOOLS
from skills.linkedin_jobs import LINKEDIN_TOOLS
from skills.email_reader import EMAIL_TOOLS
from skills.calendar_manager import CALENDAR_TOOLS
from skills.leetcode_tracker import LEETCODE_TOOLS
from skills.task_manager import TASK_TOOLS
from skills.web_search import WEB_SEARCH_TOOLS
from skills.deep_research import DEEP_RESEARCH_TOOLS
from skills.reminder import REMINDER_TOOLS
from skills.file_manager import FILE_TOOLS
from skills.playwright_browser import PLAYWRIGHT_TOOLS
from skills.youtube_controller import YOUTUBE_TOOLS
from skills.app_automation import APP_AUTOMATION_TOOLS
from skills.captcha_handler import CAPTCHA_TOOLS
from skills.antigravity_backend import ANTIGRAVITY_TOOLS, AntigravityBackend
from skills.whatsapp_automation import (
    WHATSAPP_TOOLS,
    has_pending_whatsapp_message,
    get_pending_whatsapp_message,
    whatsapp_confirm_send,
    whatsapp_cancel_send,
)
from skills.memory_extractor import get_facts_for_prompt, extract_facts_from_conversation
from skills.skill_learner import get_relevant_skills, extract_skill_from_conversation


# ── Jarvis System Prompt ──────────────────────────────────────
JARVIS_SYSTEM_PROMPT = """You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), an advanced AI assistant running locally on a MacBook. You were inspired by Tony Stark's AI assistant from the Iron Man films.

Your personality:
- Formal yet warm — address the user as "Sir" (or their configured name)
- Witty with a dry British humor, like the original Jarvis
- Confident and competent — you're the best AI assistant there is
- Concise — keep responses brief and actionable. Don't ramble.
- Proactive — suggest helpful actions when appropriate

Your capabilities (use the provided tools/functions):
- System info: time, date, battery, weather, volume control
- App control & automation: open, close, switch apps, type text into any app, and control macOS shortcuts
- Apple Music: search for songs/artists/playlists (Cmd+F and typing) and control playback (play, pause, next)
- Antigravity IDE: type commands, code, or prompts directly into the Antigravity IDE
- Web browsing & CDP automation: open pages, click elements, type in inputs, press keys, read page text, execute JavaScript, take screenshots
- YouTube tab control: search for videos inside the existing YouTube tab, play/pause, forward/rewind, skip ads, fullscreen, and volume
- WhatsApp automation: search for contacts on WhatsApp, open chats, draft messages into the input box, and send them after user confirmation
- CAPTCHA bypass: detect Cloudflare Turnstile, reCAPTCHA v2, hCaptcha and auto-click verification checkboxes
- Email: read Gmail inbox (supports 'personal' and 'college' account_types), search emails, check unread count
- LinkedIn: search for job opportunities across platforms
- Calendar: read today's events, upcoming schedule, create events
- LeetCode: check progress, get daily challenges, and track DSA consistency
- Tasks: manage a persistent to-do list (add tasks, complete tasks, remove tasks, list all tasks). Tasks are stored across sessions.
- Autonomous Antigravity Agent: delegate complex multi-step reasoning or programming queries

Important rules:
1. When asked to DO something (open app, search, read emails, control video, type in app, message on WhatsApp), USE the appropriate tool/function. Don't just describe what you would do.
2. Keep spoken responses SHORT (1-3 sentences). The user hears this via text-to-speech.
3. If a tool returns an error about configuration, explain it briefly and suggest how to fix it.
4. For general conversation, just chat naturally — no tool needed.
5. If the user agrees to the email summary (e.g. "yes please"), call the read_emails tool twice (once with account_type="personal" and once with account_type="college") and summarize both.
6. When summarizing emails, schedules, or lists, USE MARKDOWN heavily. Use bullet points, bold text, and clear spacing so it looks beautiful in the UI. (The text-to-speech engine automatically ignores Markdown, so feel free to format richly).
7. If the user says goodbye, quit, exit, or similar — respond with a farewell but don't call any tool. The system will handle shutdown.
8. You run locally on macOS. You cannot access the internet directly — use tools for web actions.
9. Web search: You can now search the web and read webpages! Use the web_search tool for real-time info, and deep_research for thorough investigations.
10. YouTube control: when the user asks to play, pause, skip, or search within YouTube, use youtube_* tools.
11. WhatsApp messaging: When asked to send or write a WhatsApp message to someone, ALWAYS use whatsapp_draft_message first. This searches for the contact and writes the message in their chat input without sending. Then ask the user: "Should I send this message, Sir?". When the user confirms (e.g. "yes", "send it", "confirm"), call whatsapp_confirm_send. If they decline ("no", "cancel", "don't send"), call whatsapp_cancel_send. NEVER send without confirmation unless explicitly commanded to bypass confirmation.
"""


import requests
import json
from google.genai import types

class OpenRouterSession:
    """Mock session class that looks like Gemini's chat_session but talks to OpenRouter."""
    def __init__(self, brain, api_key: str, model: str):
        self.brain = brain
        self.api_key = api_key
        self.model = model

    def get_history(self):
        return []

    def send_message(self, message):
        messages = [{"role": "system", "content": JARVIS_SYSTEM_PROMPT}]
        for m in self.brain.memory.get_history():
            role = "user" if m["role"] == "user" else "assistant"
            messages.append({"role": role, "content": m["content"]})

        if isinstance(message, str):
            messages.append({"role": "user", "content": message})
        else:
            parts_json = json.dumps([p.function_response.response for p in message])
            messages.append({"role": "tool", "content": parts_json})

        tools = self.brain._build_openrouter_tools()
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "tool_choice": "auto"
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Jarvis",
            "Content-Type": "application/json"
        }

        resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
        if resp.status_code == 429:
            raise Exception("Quota exceeded: 429 Too Many Requests")
        
        resp.raise_for_status()
        data = resp.json()
        choice = data["choices"][0]["message"]
        
        class MockResponse:
            def __init__(self, text, parts):
                self.text = text
                self.parts = parts
                
        parts = []
        if choice.get("content"):
            parts.append(types.Part.from_text(choice["content"]))
            
        if choice.get("tool_calls"):
            for tc in choice["tool_calls"]:
                args = json.loads(tc["function"]["arguments"])
                fc = types.FunctionCall(name=tc["function"]["name"], args=args)
                class MockPart:
                    def __init__(self, fc):
                        self.function_call = fc
                        self.text = None
                parts.append(MockPart(fc))
                
        return MockResponse(text=choice.get("content", ""), parts=parts)


class Brain:
    """
    The AI intelligence layer for Jarvis.
    Uses Gemini with function calling to understand commands and route to skills.
    """

    def __init__(self):
        self.memory = Memory()
        self.client = None
        self.chat_session = None
        self._initialized = False
        self.active_api_key = None
        self.quota = QuotaManager()
        self._tool_calls_this_turn = 0  # Track tool calls for skill extraction

        # Collect all tool definitions and function mappings
        self._all_tools = (
            SYSTEM_TOOLS + APP_TOOLS + BROWSER_TOOLS +
            LINKEDIN_TOOLS + EMAIL_TOOLS + CALENDAR_TOOLS +
            LEETCODE_TOOLS + TASK_TOOLS +
            WEB_SEARCH_TOOLS + DEEP_RESEARCH_TOOLS +
            REMINDER_TOOLS + FILE_TOOLS +
            PLAYWRIGHT_TOOLS + YOUTUBE_TOOLS +
            APP_AUTOMATION_TOOLS + CAPTCHA_TOOLS +
            ANTIGRAVITY_TOOLS + WHATSAPP_TOOLS
        )
        self._function_map = {
            tool["name"]: tool["function"]
            for tool in self._all_tools
        }
        self.antigravity_backend = None

    def initialize(self) -> bool:
        """Initialize the AI model and chat session."""
        dynamic_prompt = JARVIS_SYSTEM_PROMPT + get_facts_for_prompt()

        # If user enabled Antigravity as primary AI backend
        if Config.USE_ANTIGRAVITY:
            try:
                tool_callables = [tool["function"] for tool in self._all_tools]
                self.antigravity_backend = AntigravityBackend(
                    api_key=Config.GEMINI_API_KEY,
                    model=Config.ANTIGRAVITY_MODEL,
                    system_prompt=dynamic_prompt,
                    tools=tool_callables,
                )
                if self.antigravity_backend.start():
                    print("  🚀 Jarvis running with Antigravity Agent backend!")
                    self._initialized = True
                    return True
                else:
                    print("  ⚠️ Antigravity backend start returned False, falling back to standard Gemini...")
            except Exception as e:
                print(f"  ⚠️ Antigravity backend initialization failed: {e}. Falling back to standard Gemini...")

        pool = []
        if Config.GEMINI_API_KEY: pool.append(Config.GEMINI_API_KEY)
        if Config.GEMINI_API_KEY_FALLBACK: pool.append(Config.GEMINI_API_KEY_FALLBACK)
        if Config.OPENROUTER_API_KEY: pool.append(Config.OPENROUTER_API_KEY)
        
        if not pool:
            print("  ❌ No API keys found in configuration. Cannot initialize brain.")
            return False

        try:
            # Find the first key that has quota remaining
            selected_key = pool[0]
            for key in pool:
                if self.quota.get_remaining(key) > 0:
                    selected_key = key
                    break
                    
            self.active_api_key = selected_key
            
            if self.active_api_key == Config.OPENROUTER_API_KEY:
                self.client = None
                self.chat_session = OpenRouterSession(self, self.active_api_key, Config.OPENROUTER_MODEL)
            else:
                self.client = genai.Client(api_key=self.active_api_key)
                gemini_tools = self._build_gemini_tools()
                config = types.GenerateContentConfig(
                    system_instruction=dynamic_prompt,
                    tools=gemini_tools,
                )
                self.chat_session = self.client.chats.create(
                    model=Config.GEMINI_MODEL,
                    config=config
                )
                for m in self.memory.get_history():
                    pass 

            self._initialized = True
            return True

        except Exception as e:
            print(f"  ❌ Failed to initialize AI: {e}")
            return False

    def _send_with_retry(self, message, max_retries=2):
        """Send a message with infinite key pool swapping on Quota errors."""
        import time
        
        # Build the key pool
        pool = []
        if Config.GEMINI_API_KEY: pool.append(Config.GEMINI_API_KEY)
        if Config.GEMINI_API_KEY_FALLBACK: pool.append(Config.GEMINI_API_KEY_FALLBACK)
        if Config.OPENROUTER_API_KEY: pool.append(Config.OPENROUTER_API_KEY)
        
        if not pool:
            raise Exception("No API keys configured.")
            
        swaps_attempted = 0
        max_swaps = len(pool) * 2 # Prevent endless loop if ALL keys are permanently blocked
        
        for attempt in range(max_retries):
            try:
                response = self.chat_session.send_message(message)
                self.quota.decrement(self.active_api_key)
                return response
            except Exception as e:
                error_msg = str(e).lower()
                is_rate_limit = any(term in error_msg for term in ["quota", "rate", "429", "exhausted", "too many requests", "503", "unavailable", "overloaded"])
                
                if is_rate_limit:
                    if swaps_attempted >= max_swaps:
                        raise e
                        
                    swaps_attempted += 1
                    
                    try:
                        idx = pool.index(self.active_api_key)
                        new_key = pool[(idx + 1) % len(pool)]
                    except ValueError:
                        new_key = pool[0]
                        
                    print(f"  ⚠️  API key exhausted. Instantly switching to next key in pool...")
                    self.quota.set_exhausted(self.active_api_key)
                    self.active_api_key = new_key
                    
                    try:
                        old_history = self.chat_session.get_history()
                        
                        if new_key == Config.OPENROUTER_API_KEY:
                            self.client = None
                            self.chat_session = OpenRouterSession(self, new_key, Config.OPENROUTER_MODEL)
                        else:
                            self.client = genai.Client(api_key=new_key)
                            gemini_tools = self._build_gemini_tools()
                            config = types.GenerateContentConfig(
                                system_instruction=JARVIS_SYSTEM_PROMPT + get_facts_for_prompt(),
                                tools=gemini_tools,
                            )
                            self.chat_session = self.client.chats.create(
                                model=Config.GEMINI_MODEL,
                                config=config,
                                history=old_history
                            )
                            
                        # Immediately retry the loop with the new key
                        response = self.chat_session.send_message(message)
                        self.quota.decrement(self.active_api_key)
                        return response
                        
                    except Exception as fallback_e:
                        print(f"  ❌ Swapped key also failed: {fallback_e}")
                        raise fallback_e
                        
                else:
                    if attempt < max_retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    raise e

    def think(self, user_input: str) -> str:
        """
        Process user input through Gemini and execute any tool calls.

        Args:
            user_input: The user's command or message

        Returns:
            Jarvis's response text
        """
        if not self._initialized:
            return "My neural circuits aren't connected yet, Sir. Please check the Gemini API key."

        try:
            # FAST PATH: Intercept file requests to bypass Gemini latency
            text_lower = user_input.lower().strip()
            import re
            if re.search(r'\b(file|send me|get)\b', text_lower):
                match = re.search(r"(?:file\s+)?([a-zA-Z0-9_\-\.]+)(?:\s+file)?", text_lower.replace("send me", "").replace("send", "").replace("get", "").replace("the", "").strip())
                if match:
                    filename = match.group(1).strip()
                    if filename and filename not in ["the", "a", "my", "file", "it"]:
                        search_and_send = self._function_map.get("search_and_send_file")
                        if search_and_send:
                            # Run it directly and return!
                            return search_and_send(filename=filename)
        except Exception:
            pass # Fallback to standard processing if regex fails

        # FAST PATH: WhatsApp confirmation handling
        try:
            if has_pending_whatsapp_message():
                text_clean = text_lower.strip().rstrip(".!?,")
                confirm_words = {"yes", "send", "send it", "yeah", "yep", "sure", "please do", "confirm", "go ahead", "do it", "shoot", "ok", "okay", "send the message"}
                cancel_words = {"no", "don't", "dont", "cancel", "stop", "nevermind", "abort", "discard", "don't send", "dont send"}

                if text_clean in confirm_words or any(text_clean.startswith(w + " ") for w in confirm_words):
                    result = whatsapp_confirm_send()
                    self.memory.add("user", user_input)
                    self.memory.add("model", result)
                    return result
                elif text_clean in cancel_words or any(text_clean.startswith(w + " ") for w in cancel_words):
                    result = whatsapp_cancel_send()
                    self.memory.add("user", user_input)
                    self.memory.add("model", result)
                    return result
        except Exception:
            pass

        # Check if Antigravity primary mode is active
        if Config.USE_ANTIGRAVITY and self.antigravity_backend:
            try:
                final_response = self.antigravity_backend.chat(user_input)
                self.memory.add("user", user_input)
                self.memory.add("model", final_response)
                self._run_background_extraction(user_input, final_response)
                return final_response
            except Exception as agy_e:
                print(f"  ⚠️ Antigravity execution error: {agy_e}. Falling back to standard processing...")

        try:
            self._tool_calls_this_turn = 0  # Reset counter

            # Send message to Gemini with retry logic
            response = self._send_with_retry(user_input)

            # Process the response — handle function calls
            final_response = self._process_response(response)

            # Save to memory (for our own records)
            self.memory.add("user", user_input)
            self.memory.add("model", final_response)

            # Background: Extract facts and skills from this conversation
            self._run_background_extraction(user_input, final_response)

            return final_response

        except Exception as e:
            error_msg = str(e)

            # Try Antigravity backend as fallback if Gemini hit quota / rate limit
            is_rate_limit = any(term in error_msg.lower() for term in ["quota", "rate", "429", "exhausted", "too many requests"])
            if is_rate_limit:
                try:
                    if not self.antigravity_backend:
                        tool_callables = [tool["function"] for tool in self._all_tools]
                        self.antigravity_backend = AntigravityBackend(
                            api_key=Config.GEMINI_API_KEY,
                            model=Config.ANTIGRAVITY_MODEL,
                            system_prompt=JARVIS_SYSTEM_PROMPT + get_facts_for_prompt(),
                            tools=tool_callables,
                        )
                        self.antigravity_backend.start()
                    print("  ⚡ Falling back to Antigravity Agent due to Gemini quota exhaustion...")
                    final_response = self.antigravity_backend.chat(user_input)
                    self.memory.add("user", user_input)
                    self.memory.add("model", final_response)
                    return final_response
                except Exception as agy_fallback_err:
                    print(f"  ⚠️ Antigravity fallback failed: {agy_fallback_err}")
            
            # Attempt offline fallback
            fallback_response = self._execute_offline_fallback(user_input)
            if fallback_response:
                return fallback_response

            if "quota" in error_msg.lower() or "rate" in error_msg.lower() or "429" in error_msg or "exhausted" in error_msg.lower():
                return "I've hit my API rate limit, Sir. Please wait a moment and try again."
            elif "api_key" in error_msg.lower() or "invalid" in error_msg.lower():
                return "There seems to be an issue with my API key, Sir. Please check the configuration."
            else:
                return f"I encountered an error, Sir: {error_msg}"

    def get_quota_string(self) -> str:
        """Returns a string describing the quota remaining for the currently active API key."""
        if not self._initialized or not self.client or not self.active_api_key:
            return "Quota: Unknown"
            
        is_primary = (self.active_api_key == Config.GEMINI_API_KEY)
        key_label = "Primary" if is_primary else "Fallback"
        remaining = self.quota.get_remaining(self.active_api_key)
        
        return f"{key_label} Key: {remaining} requests left"

    def _process_response(self, response) -> str:
        """
        Process Gemini response, executing any function calls.
        Handles the full function-calling loop.
        """
        # Check if the response contains function calls
        if response.parts:
            function_responses = []
            
            for part in response.parts:
                if part.function_call:
                    fc = part.function_call
                    func_name = fc.name
                    
                    # Convert args back to a standard dict
                    func_args = {}
                    if fc.args:
                        func_args = {k: v for k, v in fc.args.items()}

                    # Execute the function
                    if func_name in self._function_map:
                        try:
                            result = self._function_map[func_name](**func_args)
                            self._tool_calls_this_turn += 1
                        except Exception as e:
                            result = f"Error executing {func_name}: {e}"
                            
                        # Build the FunctionResponse part
                        function_responses.append(
                            types.Part.from_function_response(
                                name=func_name,
                                response={"result": str(result)}
                            )
                        )
                    else:
                        function_responses.append(
                            types.Part.from_function_response(
                                name=func_name,
                                response={"result": f"I don't have the '{func_name}' capability yet, Sir."}
                            )
                        )
            
            if function_responses:
                # Send ALL function results back to Gemini for a natural response
                try:
                    followup = self._send_with_retry(function_responses)
                    return self._process_response(followup) # Recursively process in case of sequential tool calls
                except Exception as e:
                    # If we can't send back to Gemini, return the raw results
                    return str([resp.function_response.response for resp in function_responses])

        # No function call — just return the text response
        return self._extract_text(response)

    def _extract_text(self, response) -> str:
        """Extract text from a Gemini response."""
        try:
            return response.text
        except Exception:
            try:
                texts = [p.text for p in response.parts if p.text]
                return " ".join(texts) if texts else "I'm not sure how to respond to that, Sir."
            except Exception:
                return "I processed your request, Sir."

    def _run_background_extraction(self, user_input: str, response: str):
        """Run memory fact extraction and skill learning in a background thread."""
        import threading
        
        def _extract():
            try:
                # Build conversation messages for extraction
                recent = self.memory.get_last_n(6)
                messages = []
                for msg in recent:
                    role = msg.get("role", "unknown")
                    text = msg.get("parts", [{}])[0].get("text", "") if msg.get("parts") else ""
                    if text:
                        messages.append({"role": role, "text": text})
                
                if not messages:
                    return
                
                # Extract facts (runs every conversation)
                extract_facts_from_conversation(messages, self.client, Config.GEMINI_MODEL)
                
                # Extract skills (only when >= 2 tool calls were used)
                if self._tool_calls_this_turn >= 2:
                    extract_skill_from_conversation(
                        messages, self._tool_calls_this_turn,
                        self.client, Config.GEMINI_MODEL
                    )
            except Exception:
                pass  # Never crash the main thread
        
        threading.Thread(target=_extract, daemon=True).start()

    def _build_openrouter_tools(self) -> list:
        """Convert our tool definitions into OpenRouter (OpenAI) function format."""
        tools = []
        for tool in self._all_tools:
            tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool.get("parameters", {"type": "object", "properties": {}})
                }
            })
        return tools

    def _build_gemini_tools(self) -> list:
        """Convert our tool definitions into Gemini function declarations."""
        declarations = []

        for tool in self._all_tools:
            params = tool.get("parameters", {})

            if params:
                declaration = types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties=self._convert_properties(
                            params.get("properties", {})
                        ),
                        required=params.get("required", []),
                    ),
                )
            else:
                declaration = types.FunctionDeclaration(
                    name=tool["name"],
                    description=tool["description"],
                )

            declarations.append(declaration)

        return [types.Tool(function_declarations=declarations)]

    def _convert_properties(self, properties: dict) -> dict:
        """Convert property definitions to Gemini Schema format."""
        converted = {}
        type_map = {
            "string": types.Type.STRING,
            "integer": types.Type.INTEGER,
            "number": types.Type.NUMBER,
            "boolean": types.Type.BOOLEAN,
        }

        for name, prop in properties.items():
            prop_type = type_map.get(prop.get("type", "string"), types.Type.STRING)
            schema_kwargs = {
                "type": prop_type,
                "description": prop.get("description", ""),
            }

            # Handle enum values
            if "enum" in prop:
                schema_kwargs["enum"] = prop["enum"]

            converted[name] = types.Schema(**schema_kwargs)

        return converted

    def _execute_offline_fallback(self, user_input: str):
        """
        Hardcoded offline logic for critical commands if the Gemini API is down.
        Returns a response string if a match is found, otherwise None.
        """
        text = user_input.lower().strip()
        
        # Email parsing
        if "email" in text or "mail" in text:
            read_emails = self._function_map.get("read_emails")
            if read_emails:
                try:
                    if "college" in text and "personal" in text:
                        res1 = read_emails(account_type="personal")
                        res2 = read_emails(account_type="college")
                        return f"**Offline Mode Email Summary**\n\n{res1}\n\n{res2}"
                    elif "college" in text:
                        return f"**Offline Mode (College)**\n\n{read_emails(account_type='college')}"
                    else:
                        # Default to personal
                        return f"**Offline Mode (Personal)**\n\n{read_emails(account_type='personal')}"
                except Exception as e:
                    return f"Offline execution of emails failed: {e}"
        
        # File parsing
        if "file" in text or "send me" in text or "get" in text:
            search_and_send = self._function_map.get("search_and_send_file")
            if search_and_send:
                import re
                # Match "send me the file [name]", "get [name] file", "send [name]"
                match = re.search(r"(?:file\s+)?([a-zA-Z0-9_\-\.]+)(?:\s+file)?", text.replace("send me", "").replace("send", "").replace("get", "").replace("the", "").strip())
                if match:
                    filename = match.group(1).strip()
                    try:
                        return f"**Offline Mode**\n\n{search_and_send(filename=filename)}"
                    except Exception as e:
                        return f"Offline execution of file search failed: {e}"
        # YouTube parsing
        if "youtube" in text:
            play_youtube_video = self._function_map.get("play_youtube_video")
            open_website = self._function_map.get("open_website")
            
            import re
            match = re.search(r"(?:search|play)\s+(?:for\s+)?(.*?)\s+on\s+youtube|youtube\s+(?:search\s+for\s+|search\s+|for\s+)?(.*)", text)
            query = ""
            if match:
                query = match.group(1) or match.group(2)
            if not query:
                query = text.replace("search on youtube", "").replace("youtube", "").replace("search", "").strip()
            
            try:
                if query and play_youtube_video:
                    result = play_youtube_video(query=query)
                    return f"**Offline Mode**\n\nI have opened YouTube and searched for '{query}', Sir. {result}"
                elif open_website:
                    result = open_website(url_name="youtube")
                    return f"**Offline Mode**\n\nI have opened YouTube, Sir. {result}"
            except Exception as e:
                return f"Offline execution of YouTube failed: {e}"
                
        # Time/Date parsing
        if "time" in text or "date" in text:
            get_time = self._function_map.get("get_time")
            get_date = self._function_map.get("get_date")
            try:
                if "time" in text and "date" in text and get_time and get_date:
                    return f"**Offline Mode**\n\nIt is {get_time()} on {get_date()}."
                elif "time" in text and get_time:
                    return f"**Offline Mode**\n\nThe current time is {get_time()}."
                elif "date" in text and get_date:
                    return f"**Offline Mode**\n\nToday's date is {get_date()}."
            except Exception:
                pass
                
        return None

    def reset_conversation(self):
        """Clear conversation history and start fresh."""
        self.memory.clear()
        if self.client:
            # Recreate chat with tools and updated user facts
            gemini_tools = self._build_gemini_tools()
            dynamic_prompt = JARVIS_SYSTEM_PROMPT + get_facts_for_prompt()
            config = types.GenerateContentConfig(
                system_instruction=dynamic_prompt,
                tools=gemini_tools,
            )
            self.chat_session = self.client.chats.create(
                model=Config.GEMINI_MODEL,
                config=config
            )
        return "Conversation memory cleared, Sir. Starting fresh."

    def is_quit_command(self, text: str) -> bool:
        """Check if the user wants to quit Jarvis."""
        quit_phrases = [
            "quit", "exit", "bye", "goodbye", "good bye",
            "shut down", "shutdown", "turn off", "go to sleep",
            "jarvis quit", "stop", "terminate",
        ]
        text_lower = text.lower().strip()
        return any(phrase in text_lower for phrase in quit_phrases)
