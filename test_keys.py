#!/usr/bin/env python3
"""Quick test to verify both API keys work with gemini-2.0-flash-lite."""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from google import genai

keys = {
    "Primary":  os.getenv("GEMINI_API_KEY", ""),
    "Fallback": os.getenv("GEMINI_API_KEY_FALLBACK", ""),
}
model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")

print(f"Model: {model}\n")

for label, key in keys.items():
    if not key:
        print(f"  ❌ {label}: NOT SET")
        continue

    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=model,
            contents="Say hello in one sentence."
        )
        print(f"  ✅ {label}: Working — {response.text.strip()[:80]}")
    except Exception as e:
        print(f"  ❌ {label}: FAILED — {e}")

print("\nDone. If both keys show ✅, you're good to run Jarvis!")
