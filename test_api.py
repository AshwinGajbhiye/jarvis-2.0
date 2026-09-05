import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

print(f"Testing key: {api_key}")
genai.configure(api_key=api_key)

try:
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content("Hello, this is a test.")
    print("Success! Response:")
    print(response.text)
except Exception as e:
    print("Error encountered:")
    print(type(e).__name__)
    print(str(e))
