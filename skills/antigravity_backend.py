# Jarvis AI — Antigravity SDK Intelligence Backend
# Uses Google Antigravity SDK (Agent + LocalAgentConfig) as an autonomous AI brain.
# Executes tools natively and generates conversational responses.

import asyncio
import threading
import os
from typing import List, Callable, Optional, Dict, Any, Union

from config import Config

try:
    from google.antigravity import Agent, LocalAgentConfig
    from google.antigravity.types import Image as AgyImage
    HAS_ANTIGRAVITY = True
except ImportError:
    HAS_ANTIGRAVITY = False
    AgyImage = None


class AntigravityBackend:
    """
    Thread-safe wrapper around google.antigravity.Agent for Jarvis.
    Maintains a persistent, warm Agent session on a dedicated background asyncio
    worker thread for instant, sub-second responses and native conversation memory.
    """

    def __init__(self, api_key: str = "", model: str = "", system_prompt: str = "", tools: Optional[List[Callable]] = None):
        self.api_key = api_key or Config.GEMINI_API_KEY
        self.fallback_api_key = Config.GEMINI_API_KEY_FALLBACK
        self.model = model or getattr(Config, "ANTIGRAVITY_MODEL", "gemini-3.5-flash-lite")
        self.system_prompt = system_prompt
        self.tools = tools or []
        
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[threading.Thread] = None
        self._agent = None
        self._ready = threading.Event()
        self._initialized = False

    def start(self) -> bool:
        """Start the background event loop thread and warm up the persistent Agent."""
        if not HAS_ANTIGRAVITY:
            print("  ⚠️  google-antigravity is not installed.")
            return False
            
        if self._thread and self._thread.is_alive() and self._initialized:
            return True

        self._ready.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="AntigravityWorker")
        self._thread.start()
        success = self._ready.wait(timeout=10.0)
        self._initialized = success and (self._agent is not None)
        return self._initialized

    def _create_agent(self, active_key: Optional[str] = None):
        """Create an Agent instance with LocalAgentConfig."""
        key = active_key or self.api_key or os.environ.get("GEMINI_API_KEY", "")
        config = LocalAgentConfig(
            api_key=key if key else None,
            model=self.model,
            tools=self.tools if self.tools else None,
            system_instructions=self.system_prompt if self.system_prompt else None,
        )
        return Agent(config)

    def _run_loop(self):
        """Worker thread entry point: spins up loop and warms up the Agent session."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._agent = self._create_agent()
            self._loop.run_until_complete(self._agent.__aenter__())
        except Exception as e:
            print(f"  ⚠️ Antigravity warm session init warning: {e}")
            self._agent = None
        finally:
            self._ready.set()
        self._loop.run_forever()

    async def _async_chat(self, user_message: str, image_path: Optional[str] = None) -> str:
        """Send message using the persistent warm Antigravity Agent instance."""
        if self._agent is None:
            self._agent = self._create_agent()
            await self._agent.__aenter__()

        # Prepare payload: multimodal if image_path provided
        payload: Union[str, list] = user_message
        if image_path and os.path.exists(image_path) and AgyImage:
            try:
                with open(image_path, "rb") as f:
                    img_data = f.read()
                agy_img = AgyImage(data=img_data, mime_type="image/png")
                payload = [user_message, agy_img]
            except Exception as img_err:
                print(f"  ⚠️ Could not attach image to Antigravity prompt: {img_err}")
                payload = user_message

        try:
            response = await self._agent.chat(payload)
            return await response.text()
        except Exception as e:
            err_str = str(e).lower()
            # If rate limited (429) and fallback key exists, switch keys
            if any(term in err_str for term in ["429", "quota", "exhausted"]) and self.fallback_api_key:
                print("  ⚡ Antigravity Agent switching to fallback Gemini API key...")
                try:
                    await self._agent.__aexit__(None, None, None)
                except Exception:
                    pass
                self._agent = self._create_agent(active_key=self.fallback_api_key)
                await self._agent.__aenter__()
                response = await self._agent.chat(payload)
                return await response.text()

            # Otherwise attempt one recovery restart of the agent
            try:
                await self._agent.__aexit__(None, None, None)
            except Exception:
                pass
            self._agent = self._create_agent()
            await self._agent.__aenter__()
            response = await self._agent.chat(payload)
            return await response.text()

    def chat(self, user_message: str, image_path: Optional[str] = None, timeout: float = 45.0) -> str:
        """
        Synchronously send a chat message to the Antigravity Agent and get the full answer.
        Uses persistent session for sub-second responses and native conversation memory.
        """
        if not self._initialized or not self._agent:
            self.start()

        if not self._loop or not self._loop.is_running():
            raise RuntimeError("Antigravity background event loop is not running.")

        future = asyncio.run_coroutine_threadsafe(self._async_chat(user_message, image_path=image_path), self._loop)
        return future.result(timeout=timeout)

    def stop(self):
        """Stop the background worker and cleanly exit the Agent session."""
        if self._loop and self._loop.is_running() and self._agent:
            async def _close():
                try:
                    await self._agent.__aexit__(None, None, None)
                except Exception:
                    pass
            try:
                fut = asyncio.run_coroutine_threadsafe(_close(), self._loop)
                fut.result(timeout=3.0)
            except Exception:
                pass
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
