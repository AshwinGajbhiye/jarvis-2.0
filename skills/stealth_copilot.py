"""
Stealth Google Meet Q&A Copilot for J.A.R.V.I.S.
Real-time question answering during Google Meet screen-sharing sessions.

Answer Pipeline (ordered by priority):
  1. Antigravity CLI (`antigravity prompt "..."`) — primary engine
  2. Antigravity Python SDK (AntigravityBackend) — fallback if CLI not found
  3. Local Fast Knowledge Base — instant fallback for common CS topics

Features:
  • Screen-share invisible overlay (NSWindowSharingNone)
  • System audio capture via BlackHole loopback (hears friend's voice)
  • Session context — remembers last 5 Q&A pairs for conversation continuity
  • Streaming output — partial answers rendered word-by-word on the HUD
  • Concurrent request guard — prevents duplicate processing
  • Voice + text input — listen to mic/system audio, or type questions directly
"""

import re
import json
import os
import subprocess
import shutil
import threading
import datetime
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import speech_recognition as sr
from PyQt6.QtCore import QThread, pyqtSignal

from config import Config


# ── Session History (In-Memory, Per Launch) ───────────────────────────────
_session_history: List[Dict[str, str]] = []
_MAX_HISTORY = 5

# ── Concurrent Request Guard ─────────────────────────────────────────────
_is_processing = threading.Lock()


# ── Built-in Fast Technical Knowledge Base (Zero Latency Fallback) ────────
COMMON_CS_QUESTIONS = {
    "tcp": {
        "direct": "TCP is a connection-oriented, reliable protocol that guarantees in-order packet delivery using three-way handshakes and congestion control.",
        "points": [
            "Reliability: Uses sequence numbers, ACKs, and retransmissions.",
            "Use Cases: Web browsing (HTTP/HTTPS), email (SMTP), file transfers (FTP).",
            "Trade-off: Higher latency and protocol overhead compared to UDP."
        ]
    },
    "udp": {
        "direct": "UDP is a lightweight, connectionless protocol that sends datagrams without establishing a handshake or guaranteeing delivery order, prioritizing speed over reliability.",
        "points": [
            "Low Latency: Zero handshake round-trips and minimal header overhead.",
            "Use Cases: Live video streaming, VoIP, DNS lookups, and online multiplayer gaming.",
            "Trade-off: Packets may arrive out-of-order or drop without retransmission."
        ]
    },
    "quicksort": {
        "direct": "QuickSort is a divide-and-conquer sorting algorithm with an average time complexity of O(N log N), though it degrades to O(N²) in the worst case when an unbalanced pivot is chosen.",
        "points": [
            "In-place: Requires O(log N) auxiliary stack space.",
            "Pivot Selection: Using randomized pivot or median-of-three prevents O(N²) degradation.",
            "Cache Efficiency: Excellent spatial locality makes it faster in practice than MergeSort."
        ]
    },
    "mergesort": {
        "direct": "MergeSort is a stable divide-and-conquer sorting algorithm that guarantees O(N log N) time complexity across all worst, best, and average cases, at the cost of O(N) extra memory.",
        "points": [
            "Guaranteed O(N log N): Independent of the input array order.",
            "Space Complexity: Requires O(N) temporary buffer memory.",
            "Stability: Maintains relative ordering of duplicate elements, ideal for linked lists."
        ]
    },
    "process vs thread": {
        "direct": "A process is an isolated execution environment with its own dedicated memory space, whereas threads exist within a process and share its heap, memory, and open file descriptors.",
        "points": [
            "Overhead: Thread creation and context switching are significantly cheaper than process switching.",
            "Fault Isolation: If one thread crashes, the whole process may crash; process crashes are isolated.",
            "Communication: Threads communicate via shared memory; processes require IPC (pipes, sockets, shared memory)."
        ]
    },
    "deadlock": {
        "direct": "A deadlock is a state where two or more processes are permanently blocked because each is holding a resource that another process needs.",
        "points": [
            "Coffman Conditions: Mutual exclusion, Hold and wait, No preemption, and Circular wait.",
            "Resolution: Deadlock detection and recovery, prevention by ordering resource locks, or banker's algorithm.",
            "Prevention: Enforce strict global locking hierarchy across all threads."
        ]
    },
    "virtual memory": {
        "direct": "Virtual memory provides each process with the illusion of a large, contiguous address space while mapping virtual pages to physical frames via page tables and the Memory Management Unit (MMU).",
        "points": [
            "Isolation & Protection: Prevents processes from reading or writing into another process's memory.",
            "Paging & Swapping: Inactive pages are temporarily swapped to disk to free physical RAM.",
            "TLB: Translation Lookaside Buffer caches virtual-to-physical address mappings for hardware-speed lookups."
        ]
    },
    "rest vs graphql": {
        "direct": "REST organizes data into fixed resource endpoints with standard HTTP verbs, whereas GraphQL exposes a single flexible endpoint where clients query precisely the exact fields they need.",
        "points": [
            "Over/Under-fetching: GraphQL eliminates over-fetching; REST often requires multiple roundtrips.",
            "Caching: REST benefits from universal HTTP-level caching; GraphQL requires application-level caching.",
            "Schema: GraphQL enforces a strict strongly-typed schema on all requests and mutations."
        ]
    },
    "sql vs nosql": {
        "direct": "SQL databases are relational, schema-enforced systems prioritizing ACID transactions, while NoSQL databases provide flexible schema designs optimized for high-throughput horizontal scaling.",
        "points": [
            "SQL: Structured tables with relations, ideal for financial and transactional integrity.",
            "NoSQL: Document, key-value, or graph models, ideal for rapid prototyping and partitioned data.",
            "Scaling: SQL scales vertically with larger servers; NoSQL natively scales horizontally across clusters."
        ]
    },
    "binary search": {
        "direct": "Binary search is an O(log N) search algorithm that works on sorted arrays by repeatedly dividing the search interval in half.",
        "points": [
            "Prerequisite: The array must be sorted for binary search to work correctly.",
            "Time Complexity: O(log N) — each comparison eliminates half the remaining elements.",
            "Variants: Lower bound, upper bound, and rotated sorted array searches."
        ]
    },
    "hash table": {
        "direct": "A hash table maps keys to values using a hash function, providing O(1) average-case lookup, insertion, and deletion.",
        "points": [
            "Collision Handling: Chaining (linked lists at each bucket) or open addressing (linear/quadratic probing).",
            "Load Factor: Rehashing occurs when load factor exceeds threshold (typically 0.75).",
            "Use Cases: Dictionaries, caches, symbol tables, and database indexing."
        ]
    },
    "osi model": {
        "direct": "The OSI model is a 7-layer conceptual framework for network communication: Physical, Data Link, Network, Transport, Session, Presentation, and Application.",
        "points": [
            "Layers 1-4: Physical (bits), Data Link (frames), Network (packets/routing), Transport (segments/TCP/UDP).",
            "Layers 5-7: Session (connections), Presentation (encryption/compression), Application (HTTP/SMTP).",
            "TCP/IP Model: Simplified to 4 layers — Link, Internet, Transport, Application."
        ]
    }
}


def _build_context_string(history: List[Dict[str, str]]) -> str:
    """Build a conversation context string from session history."""
    if not history:
        return ""

    lines = ["Previous Q&A context from this session:"]
    for entry in history[-_MAX_HISTORY:]:
        lines.append(f"Q: {entry.get('question', '')}")
        lines.append(f"A: {entry.get('answer', '')}")
        lines.append("")
    return "\n".join(lines)


def _add_to_history(question: str, answer: str):
    """Add a Q&A pair to session history."""
    global _session_history
    _session_history.append({
        "question": question.strip(),
        "answer": answer.strip(),
        "timestamp": datetime.datetime.now().isoformat()
    })
    # Keep only the last N entries
    if len(_session_history) > _MAX_HISTORY:
        _session_history = _session_history[-_MAX_HISTORY:]


def get_session_history() -> List[Dict[str, str]]:
    """Return the current session's Q&A history (for HUD display)."""
    return list(_session_history)


def _detect_antigravity_cli() -> Optional[str]:
    """Detect if the antigravity CLI is available on PATH."""
    for cmd in ["antigravity", "agy"]:
        path = shutil.which(cmd)
        if path:
            return path
    return None


def _build_cli_prompt(question: str, history: List[Dict[str, str]]) -> str:
    """Build the full prompt string for the CLI/SDK call."""
    context = _build_context_string(history)
    return f"""You are J.A.R.V.I.S., an elite real-time copilot helping a student during a live Google Meet discussion.
Someone just asked: "{question}"

{context}

Output a high-grade response:
1. "direct_answer": Exactly 1 or 2 crisp, natural sentences that can be immediately spoken aloud. No preamble like "Sure" or "The answer is".
2. "key_points": 2 or 3 short bullet points with technical specifics (formulas, complexities, key terms, or trade-offs) for follow-up elaboration.

Return strictly valid JSON:
{{
  "direct_answer": "...",
  "key_points": ["...", "..."]
}}"""


def answer_via_gemini_api(question: str, image_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Direct ultra-low latency answer generation using Google Gemini 2.5 Flash.
    Supports both text questions and screen snippet images (Req 3 & 4).
    """
    if not Config.GEMINI_API_KEY:
        return {"direct_answer": "", "key_points": [], "source": ""}

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=Config.GEMINI_API_KEY)
        context = _build_context_string(_session_history)

        contents = []
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                img_bytes = f.read()
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/png"))
            prompt = f"""You are J.A.R.V.I.S., an elite real-time copilot helping a student during a live Google Meet interview.
The friend shared this screen with a question.
Extract and solve the question in the image:
1. "direct_answer": Exactly 1 or 2 crisp, natural sentences to be spoken aloud.
2. "key_points": 2-3 short bullet points with technical specifics, complexity (O(N)), or code solution.

Return strictly valid JSON:
{{
  "direct_answer": "...",
  "key_points": ["...", "..."]
}}"""
            contents.append(prompt)
        else:
            prompt = f"""You are J.A.R.V.I.S., an elite real-time copilot helping a student during a live Google Meet discussion.
Someone just asked: "{question}"

{context}

Output a high-grade response:
1. "direct_answer": Exactly 1 or 2 crisp, natural sentences that can be immediately spoken aloud. No preamble like "Sure" or "The answer is".
2. "key_points": 2 or 3 short bullet points with technical specifics (formulas, complexities, key terms, or code/trade-offs) for follow-up elaboration.

Return strictly valid JSON:
{{
  "direct_answer": "...",
  "key_points": ["...", "..."]
}}"""
            contents.append(prompt)

        model_name = getattr(Config, "GEMINI_MODEL", "gemini-3.5-flash-lite")
        if not model_name or "flash" not in model_name.lower():
            model_name = "gemini-3.5-flash-lite"

        response = client.models.generate_content(
            model=model_name,
            contents=contents
        )

        if response and response.text:
            parsed = _extract_json_answer(response.text.strip())
            if parsed and parsed.get("direct_answer"):
                source_label = "Gemini Vision" if image_path else "Gemini 2.5 Flash"
                return {
                    "direct_answer": parsed["direct_answer"],
                    "key_points": parsed.get("key_points", []),
                    "source": source_label
                }
    except Exception as e:
        print(f"  ⚠️ Gemini API direct answer error: {e}")

    return {"direct_answer": "", "key_points": [], "source": ""}


def answer_via_antigravity_cli(question: str) -> Dict[str, Any]:
    """
    Try answering via Antigravity CLI subprocess.
    Falls back to SDK if CLI is not found.

    Returns:
        Dict with keys: direct_answer, key_points, source
    """
    cli_path = _detect_antigravity_cli()

    if cli_path:
        try:
            prompt = _build_cli_prompt(question, _session_history)
            proc = subprocess.Popen(
                [cli_path, "prompt", prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={**os.environ, "NO_COLOR": "1"}
            )
            stdout, stderr = proc.communicate(timeout=30)

            if proc.returncode == 0 and stdout.strip():
                parsed = _extract_json_answer(stdout.strip())
                if parsed and parsed.get("direct_answer"):
                    return {
                        "direct_answer": parsed["direct_answer"],
                        "key_points": parsed.get("key_points", []),
                        "source": "Antigravity CLI"
                    }
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except Exception:
                pass
            print("  ⚠️ Antigravity CLI timed out after 30s.")
        except Exception as e:
            print(f"  ⚠️ Antigravity CLI error: {e}")

    # ── Fallback: Antigravity Python SDK ──────────────────────────
    return _answer_via_sdk(question)


def answer_via_antigravity_sdk(question: str, image_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Primary: use the Antigravity Python SDK (AntigravityBackend) in-memory Agent.
    Supports both text questions and screen snippet images.
    """
    try:
        from skills.antigravity_backend import get_antigravity_instance
        backend = get_antigravity_instance()
        if backend:
            if not getattr(backend, "_initialized", False) or not getattr(backend, "_agent", None):
                backend.start()
            prompt = _build_cli_prompt(question, _session_history)
            raw_response = backend.chat(prompt, image_path=image_path, timeout=25.0)
            parsed = _extract_json_answer(raw_response)
            if parsed and parsed.get("direct_answer"):
                return {
                    "direct_answer": parsed["direct_answer"],
                    "key_points": parsed.get("key_points", []),
                    "source": "Antigravity SDK"
                }
    except Exception as e:
        print(f"  ⚠️ Antigravity SDK error: {e}")

    return {
        "direct_answer": "",
        "key_points": [],
        "source": "Failed"
    }


def _answer_via_sdk(question: str) -> Dict[str, Any]:
    """Backward-compatible alias for answer_via_antigravity_sdk."""
    return answer_via_antigravity_sdk(question)


def answer_from_local_kb(question: str) -> Dict[str, Any]:
    """
    Instant-response from local knowledge base. Zero latency.
    Returns empty result if no match found.
    """
    q_lower = question.lower().strip()

    for key, data in COMMON_CS_QUESTIONS.items():
        if key in q_lower or all(w in q_lower for w in key.split()):
            return {
                "direct_answer": data["direct"],
                "key_points": data["points"],
                "source": "Local Fast Knowledge"
            }

    return {"direct_answer": "", "key_points": [], "source": ""}


def answer_question_superfast(question: str) -> Dict[str, Any]:
    """
    Generate an immediate, high-grade answer using parallel execution:
    1. Local KB (instant) — shows flash answer immediately
    2. Antigravity CLI/SDK (2-20s) — replaces with full answer when ready

    Returns the best available answer.
    """
    clean_q = question.strip()
    if not clean_q:
        return {
            "direct_answer": "Please repeat the question or speak closer to the microphone, Sir.",
            "key_points": ["Waiting for audio input."],
            "source": "Local Fallback"
        }

    # ── Parallel Execution: Local KB + Gemini API + CLI/SDK ───────
    best_result = {"direct_answer": "", "key_points": [], "source": ""}

    with ThreadPoolExecutor(max_workers=3) as executor:
        future_local = executor.submit(answer_from_local_kb, clean_q)
        future_gemini = executor.submit(answer_via_gemini_api, clean_q)
        future_cli = executor.submit(answer_via_antigravity_cli, clean_q)

        # Local KB finishes instantly — use it as initial answer
        try:
            local_result = future_local.result(timeout=0.3)
            if local_result.get("direct_answer"):
                best_result = local_result
        except Exception:
            pass

        # Wait for Gemini API answer (lightning fast, high quality)
        try:
            gemini_result = future_gemini.result(timeout=10.0)
            if gemini_result.get("direct_answer"):
                best_result = gemini_result
        except Exception:
            pass

        # Fallback: CLI/SDK if Gemini didn't return
        if not best_result.get("direct_answer") or best_result.get("source") == "Local Fast Knowledge":
            try:
                cli_result = future_cli.result(timeout=15.0)
                if cli_result.get("direct_answer"):
                    best_result = cli_result
            except Exception as e:
                print(f"  ⚠️ CLI/SDK parallel execution error: {e}")

    # ── Final Fallback: Deterministic Synthesis ───────────────────
    if not best_result.get("direct_answer"):
        match = re.search(
            r"(?:what is|what are|explain|how does|why does|define)\s+([a-zA-Z0-9\s]+?)(?:\?|$)",
            clean_q.lower()
        )
        topic = match.group(1).strip() if match else clean_q
        best_result = {
            "direct_answer": f"{topic.title()} is a fundamental concept in software engineering used to optimize execution efficiency, manage state, and ensure system modularity.",
            "key_points": [
                f"Core Role: Ensures predictable behavior and resource isolation in {topic}.",
                "Best Practice: Minimize unnecessary state mutations and optimize time/space complexity.",
                "Alternative: Evaluate trade-offs based on operational requirements and throughput."
            ],
            "source": "Deterministic Synthesis"
        }

    # Save to session history
    _add_to_history(clean_q, best_result.get("direct_answer", ""))

    return best_result


def _extract_json_answer(text: str) -> Optional[Dict[str, Any]]:
    """Extract direct_answer and key_points from model text."""
    try:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        raw = match.group(1).strip() if match else text.strip()
        return json.loads(raw)
    except Exception:
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            try:
                return json.loads(text[start:end+1])
            except Exception:
                pass
    return None


class StealthQuestionWorker(QThread):
    """
    Background worker that:
    1. Captures audio from system loopback (friend's voice) or physical mic
    2. Transcribes speech using Google Speech Recognition (free, zero API keys)
    3. Generates answers via Antigravity CLI → SDK → Local KB (cascading fallback)
    4. Emits signals to update the screen-share-invisible HUD
    """
    listening_started = pyqtSignal(str)
    question_transcribed = pyqtSignal(str)
    answer_ready = pyqtSignal(str, str, list)      # question, direct_answer, key_points
    partial_answer_ready = pyqtSignal(str, str, list)  # quick local KB answer
    answer_source = pyqtSignal(str)                 # source label for HUD badge
    error_occurred = pyqtSignal(str)
    audio_device_info = pyqtSignal(str)             # audio source badge text

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manual_question: Optional[str] = None
        self.manual_image_path: Optional[str] = None
        self._loopback_device_index: Optional[int] = None
        self._loopback_checked = False

    def ask_text_question(self, question_text: str):
        """Trigger question answering directly with text query (no voice capture)."""
        self.manual_question = question_text
        if not self.isRunning():
            self.start()

    def ask_image_question(self, image_path: str):
        """Trigger question answering directly from a screen snippet image (Req 4)."""
        self.manual_image_path = image_path
        if not self.isRunning():
            self.start()

    def _detect_loopback_once(self):
        """Check for system audio loopback device (cached after first check)."""
        if self._loopback_checked:
            return

        try:
            from utils.audio_loopback import get_loopback_status
            is_available, status_text, device_index = get_loopback_status()
            self._loopback_device_index = device_index
            self.audio_device_info.emit(status_text)

            if not is_available:
                print("  ℹ️ No loopback audio device found. Using physical microphone.")
                print("  💡 For system audio capture, install BlackHole: brew install blackhole-2ch")
        except Exception as e:
            print(f"  ⚠️ Audio loopback detection error: {e}")

        self._loopback_checked = True

    def run(self):
        """Execute listening & answering in background thread."""
        # Concurrent request guard — skip if already processing
        if not _is_processing.acquire(blocking=False):
            self.error_occurred.emit("Already processing a question. Please wait.")
            return

        try:
            self._run_inner()
        finally:
            _is_processing.release()

    def _run_inner(self):
        """Core execution logic (protected by the processing lock)."""
        question_text = ""

        # ── Handle Screen Snippet Question (Req 4) ────────────
        if self.manual_image_path:
            img_path = self.manual_image_path
            self.manual_image_path = None
            self.audio_device_info.emit("✂️ Screen Snippet")
            self.listening_started.emit("🔍 Reading & solving question from screen...")
            # Primary: Antigravity Python SDK; Fallback: direct Gemini API
            res = answer_via_antigravity_sdk("Solve the question in this screen snippet", image_path=img_path)
            if not res.get("direct_answer"):
                res = answer_via_gemini_api("Solve the question in this screen snippet", image_path=img_path)
            q_text = "Screen Snippet Question"
            if res.get("direct_answer"):
                ans = res["direct_answer"]
                pts = res.get("key_points", [])
                src = res.get("source", "Antigravity SDK")
            else:
                ans = "Could not extract question from the screen snippet. Please try selecting again or type your question."
                pts = ["Ensure question text is clearly selected"]
                src = "Vision Fallback"
            _add_to_history(q_text, ans)
            self.question_transcribed.emit(q_text)
            self.answer_source.emit(src)
            self.answer_ready.emit(q_text, ans, pts)
            return

        if self.manual_question:
            question_text = self.manual_question
            self.manual_question = None
            self.audio_device_info.emit("⌨️ Text Input")
        else:
            # ── Detect loopback audio device ─────────────────────
            self._detect_loopback_once()

            self.listening_started.emit("🎙️ Listening for question... (Speak now)")

            recognizer = sr.Recognizer()
            # Lower energy threshold for better sensitivity when picking up
            # a friend's voice through speakers (physical mic) or loopback device
            recognizer.energy_threshold = 35
            recognizer.dynamic_energy_threshold = True
            # Shorter pause threshold so Jarvis detects end-of-speech faster
            recognizer.pause_threshold = 1.5

            try:
                # Use loopback device if available, otherwise physical mic
                mic_kwargs = {}
                if self._loopback_device_index is not None:
                    mic_kwargs["device_index"] = self._loopback_device_index

                with sr.Microphone(**mic_kwargs) as source:
                    # Longer calibration for more stable baseline in noisy Meet environments
                    recognizer.adjust_for_ambient_noise(source, duration=1.2)
                    # Increased timeout (15s) and phrase limit (30s) to allow
                    # friend to finish longer questions before cutting off
                    audio = recognizer.listen(source, timeout=15, phrase_time_limit=30)

                self.listening_started.emit("⚡ Transcribing question...")
                question_text = recognizer.recognize_google(
                    audio, language=Config.STT_LANGUAGE or "en-US"
                )
            except sr.WaitTimeoutError:
                loopback_hint = ""
                if self._loopback_device_index is None:
                    loopback_hint = (
                        "\n\n💡 To hear your friend's voice from Google Meet, install BlackHole:\n"
                        "   brew install blackhole-2ch\n"
                        "   Then set up a Multi-Output Device in Audio MIDI Setup."
                    )
                self.error_occurred.emit(
                    "No voice detected within 15 seconds. "
                    "Type your question in the box above, "
                    f"or check your audio input device.{loopback_hint}"
                )
                return
            except sr.UnknownValueError:
                self.error_occurred.emit(
                    "Audio was unclear. Press ⌥A to retry, or type your question above."
                )
                return
            except OSError as e:
                # Specific handling for mic-in-use contention (common with wakeword)
                self.error_occurred.emit(
                    f"Microphone access error: {e}. "
                    "The mic may be in use by another process. Press ⌥A to retry."
                )
                return
            except Exception as e:
                self.error_occurred.emit(
                    f"Audio capture error ({e}). Type your question in the box above."
                )
                return

        if not question_text or not question_text.strip():
            self.error_occurred.emit(
                "No audio detected. Type your question or check your audio input device."
            )
            return

        self.question_transcribed.emit(question_text)

        # ── Generate Answer (Parallel: Local KB instant + CLI/SDK full) ──
        # Step 1: Fire local KB instantly for a flash answer
        local_result = answer_from_local_kb(question_text)
        if local_result.get("direct_answer"):
            self.partial_answer_ready.emit(
                question_text,
                local_result["direct_answer"],
                local_result.get("key_points", [])
            )
            self.answer_source.emit(local_result.get("source", "Local"))

        # Step 2: Primary engine: Antigravity Python SDK (warm persistent agent)
        full_result = answer_via_antigravity_sdk(question_text)
        if not full_result.get("direct_answer"):
            full_result = answer_via_gemini_api(question_text)
        if not full_result.get("direct_answer"):
            full_result = answer_via_antigravity_cli(question_text)

        if full_result.get("direct_answer"):
            final_answer = full_result["direct_answer"]
            final_points = full_result.get("key_points", [])
            source = full_result.get("source", "Unknown")
        elif local_result.get("direct_answer"):
            # CLI/SDK failed but we have a local answer — keep it
            final_answer = local_result["direct_answer"]
            final_points = local_result.get("key_points", [])
            source = local_result.get("source", "Local Fallback")
        else:
            # Both failed — use deterministic synthesis
            result = answer_question_superfast(question_text)
            final_answer = result.get("direct_answer", "I couldn't generate an answer. Please try typing the question.")
            final_points = result.get("key_points", [])
            source = result.get("source", "Fallback")

        # Save to session history
        _add_to_history(question_text, final_answer)

        self.answer_source.emit(source)
        self.answer_ready.emit(question_text, final_answer, final_points)
