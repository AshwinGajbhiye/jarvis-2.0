# 🛠️ Jarvis AI — Setup Guide

## Prerequisites

- macOS (tested on macOS 26.3 Tahoe)
- Python 3.11+ (you have 3.13.1 ✅)
- Homebrew (you have it ✅)

---

## Step 1: Install System Dependencies

PyAudio needs the `portaudio` library for microphone access:

```bash
brew install portaudio
```

## Step 2: Create Virtual Environment

```bash
cd ~/Desktop/jarvis
python3 -m venv venv
source venv/bin/activate
```

## Step 3: Install Python Packages

```bash
pip install -r requirements.txt
```

> **Note**: If PyAudio fails to install, try:
> ```bash
> pip install --global-option='build_ext' --global-option='-I/opt/homebrew/include' --global-option='-L/opt/homebrew/lib' pyaudio
> ```
> Or skip it — Jarvis will work in keyboard-only mode.

## Step 4: Configure API Keys

### 4a: Gemini API Key (Required)

1. Go to [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey)
2. Click "Create API Key"
3. Copy the key
4. Create your `.env` file:

```bash
cp .env.example .env
```

5. Edit `.env` and paste your key:
```
GEMINI_API_KEY=AIzaSy_your_actual_key_here
```

### 4b: Gmail Setup (Optional — for email features)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project (or create one)
3. Enable the **Gmail API**:
   - APIs & Services → Library → Search "Gmail API" → Enable
4. Configure **OAuth consent screen**:
   - APIs & Services → OAuth consent screen
   - User Type: External → Create
   - App name: "Jarvis AI"
   - Add your email as a test user
5. Create **OAuth credentials**:
   - APIs & Services → Credentials → Create Credentials → OAuth client ID
   - Application type: Desktop app
   - Download the JSON file
6. Rename it to `credentials.json` and place in the project root:
```bash
mv ~/Downloads/client_secret_*.json ~/Desktop/jarvis/credentials.json
```

> The first time you use email features, a browser window will open for you to
> sign in. After that, a `token.json` is saved and auto-refreshed.

## Step 5: Run Jarvis!

```bash
cd ~/Desktop/jarvis
source venv/bin/activate
python main.py
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `ModuleNotFoundError: No module named 'pyaudio'` | `brew install portaudio && pip install pyaudio` |
| `No microphone found` | Grant Terminal microphone access in System Settings → Privacy |
| `Gmail authentication error` | Delete `token.json` and re-run — it will re-authenticate |
| `Gemini API rate limit` | Wait 60 seconds — free tier is 60 req/min |
| `say: command not found` | You're not on macOS — TTS only works on Mac |
