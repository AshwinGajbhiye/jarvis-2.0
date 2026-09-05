import os
from google import genai
from config import Config

def test_key(key, name):
    print(f"Testing {name}...")
    try:
        client = genai.Client(api_key=key)
        response = client.models.generate_content(
            model=Config.GEMINI_MODEL,
            contents="Say hi"
        )
        print(f"  {name} works! Response: {response.text.strip()}")
    except Exception as e:
        print(f"  {name} failed: {e}")

test_key(Config.GEMINI_API_KEY, "Primary Key")
test_key(Config.GEMINI_API_KEY_FALLBACK, "Fallback Key")
