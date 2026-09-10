# Jarvis AI — Antigravity SDK Intelligence Backend
# Uses Google Antigravity SDK (Agent + LocalAgentConfig) as an autonomous AI brain.
# Executes tools natively and generates conversational responses.

import asyncio
import threading
import os
from typing import List, Callable, Optional, Dict, Any

from config import Config

try:
    from google.antigravity import Agent, LocalAgentConfig
    HAS_ANTIGRAVITY = True
except ImportError:
    HAS_ANTIGRAVITY = False


class AntigravityBackend:
    """
    Thread-safe wrapper around google.antigravity.Agent for Jarvis.
    Runs an asyncio event loop in a dedicated background worker thread so that
    synchronous callers (GUI, CLI, voice listeners) can call .chat() safely.
    """

    def __init__(self, api_key: str = "", model: str = "", system_prompt: str = "", tools: Optional[List[Callable]] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.model = model or getattr(Config, "ANTIGRAVITY_MODEL", "gemini-2.5-flash")
        self.system_prompt = system_prompt
        self.tools = tools or []
        
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._agent = None
        self._ready = threading.Event()
        self._initialized = False

    def start(self) -> bool:
        """Start the background event loop thread."""
        if not HAS_ANTIGRAVITY:
            print("  ⚠️  google-antigravity is not installed.")
            return False
            
        if self._thread and self._thread.is_alive():
            return True

        self._ready.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="AntigravityWorker")
        self._thread.start()
        self._ready.wait(timeout=5.0)
        self._initialized = True
        return True

    def _run_loop(self):
        """Worker thread entry point."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._ready.set()
        self._loop.run_forever()

    async def _async_chat(self, user_message: str) -> str:
        """Send message using an Antigravity Agent instance."""
        config = LocalAgentConfig(
            api_key=self.api_key,
            model=self.model,
            tools=self.tools if self.tools else None,
            system_instructions=self.system_prompt if self.system_prompt else None,
        )
        
        async with Agent(config) as agent:
            response = await agent.chat(user_message)
            return await response.text()

    def chat(self, user_message: str, timeout: float = 60.0) -> str:
        """
        Synchronously send a chat message to the Antigravity Agent and get the full answer.
        Executes any tool calls autonomously.
        """
        if not self._initialized:
            self.start()

        if not self._loop or not self._loop.is_running():
            raise RuntimeError("Antigravity background event loop is not running.")

        future = asyncio.run_coroutine_threadsafe(self._async_chat(user_message), self._loop)
        return future.result(timeout=timeout)

    def stop(self):
        """Stop the background worker."""
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=2.0)
        self._initialized = False


# ── Standalone tool definition for Jarvis to query Antigravity ────────

_global_antigravity_instance: Optional[AntigravityBackend] = None

def get_antigravity_instance() -> AntigravityBackend:
    global _global_antigravity_instance
    if _global_antigravity_instance is None:
        _global_antigravity_instance = AntigravityBackend()
        _global_antigravity_instance.start()
    return _global_antigravity_instance


def query_antigravity_agent(prompt: str) -> str:
    """
    Delegate a complex coding, reasoning, or research query to the autonomous Antigravity Agent.
    
    Args:
        prompt: The task, coding question, or research instruction.
    """
    try:
        backend = get_antigravity_instance()
        return backend.chat(prompt)
    except Exception as e:
        return f"Antigravity Agent error: {e}"


ANTIGRAVITY_TOOLS = [
    {
        "name": "query_antigravity_agent",
        "description": "Delegate complex reasoning, autonomous planning, coding, or problem-solving tasks to the Antigravity Agent.",
        "function": query_antigravity_agent,
        "parameters": {
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "The complex instruction, programming problem, or deep research query",
                }
            },
            "required": ["prompt"],
        },
    }
]
