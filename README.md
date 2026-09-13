# 🤖 J.A.R.V.I.S. — Just A Rather Very Intelligent System

> *"At your service, Sir."*

A fully local, voice-interactive AI assistant for macOS, inspired by Tony Stark's AI companion from Iron Man. Powered by Google Gemini 2.0 Flash with function calling for intelligent command routing.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 **AI Brain** | Google Gemini 2.0 Flash with function calling — understands natural language, no brittle string matching |
| 🎤 **Voice Commands** | Speak to Jarvis naturally via microphone |
| 🔊 **Voice Responses** | Responds in a British "Daniel" voice (macOS native TTS) |
| 📧 **Email Reader** | Reads your Gmail inbox, searches by sender/keyword, AI-powered summaries |
| 💻 **App Control** | Open/close/switch macOS apps — VS Code, Chrome, Brave, Calendar, Spotify, etc. |
| 🔍 **Web Search** | Google, YouTube, GitHub, StackOverflow search via voice |
| 💼 **Job Finder** | Search LinkedIn, Naukri, Indeed, Glassdoor for opportunities |
| 📅 **Calendar** | Read today's events, upcoming schedule, create events |
| 🌤️ **Weather** | Current weather via wttr.in |
| 🔋 **System Info** | Battery, CPU, memory, volume control |
| 📱 **Mobile App (Expo Go)** | Native mobile app for iOS/Android with two-way file transfer, voice commands, and remote explorer |
| 💬 **Conversation** | Natural conversation with context memory |

---

## 🚀 Quick Start

```bash
# 1. Install portaudio (for microphone)
brew install portaudio

# 2. Create virtual environment
cd ~/Desktop/jarvis
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# 5. Launch!
python main.py
```

---

## 🗣️ Example Commands

```
"What time is it?"
"Open VS Code"
"Search Google for Python async tutorial"
"Read my emails"
"Any emails from GitHub?"
"Find me React developer jobs in Pune"
"What's on my calendar today?"
"Open Brave and search for machine learning"
"What's the weather in Mumbai?"
"Set volume to 40"
"Close Spotify"
"Jarvis, quit"
```

---

## 📁 Project Structure

```
jarvis/
├── main.py              # Entry point — boot sequence + event loop
├── brain.py             # Gemini AI + function calling engine
├── memory.py            # Conversation history
├── config.py            # Environment configuration
├── voice/
│   ├── tts.py           # Text-to-Speech (macOS say)
│   └── stt.py           # Speech-to-Text (Google Speech)
├── skills/
│   ├── system_info.py   # Time, battery, weather, volume
│   ├── app_launcher.py  # macOS app control
│   ├── browser_automation.py  # Web search
│   ├── linkedin_jobs.py # Job search
│   ├── email_reader.py  # Gmail API
│   └── calendar_manager.py   # macOS Calendar
├── utils/
│   └── helpers.py       # Shared utilities
├── requirements.txt
├── .env.example
├── SETUP.md
└── README.md
```

---

## 🔑 API Keys Needed

| Key | Required | Cost | Get It |
|-----|----------|------|--------|
| Gemini API Key | ✅ Yes | Free (60 req/min) | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| Gmail OAuth | Optional | Free | [See SETUP.md](SETUP.md) |

---

## 🛡️ Privacy

- **100% local execution** — your voice and commands stay on your Mac
- Gemini API calls send only the conversation text (no files, no system data)
- Gmail uses OAuth2 — Jarvis never sees your Google password
- No data is stored in the cloud — conversation history lives in `~/.jarvis/`

---

## 🕵️ Google Meet Stealth Copilot

A real-time, screen-share-invisible Q&A assistant for Google Meet calls. Jarvis listens to questions during your meeting, generates answers via Antigravity, and displays them in a private overlay that **only you can see** — completely invisible to screen sharing, screen recording, and screenshots.

### How It Works

1. **Press `⌥S`** to toggle the Stealth HUD (or say "stealth mode" to Jarvis)
2. **Press `⌥A`** to listen for a question via microphone/system audio
3. **Or type** your question directly in the HUD input box
4. Jarvis generates an answer and displays it in the overlay with a streaming typing animation
5. The answer is **invisible to everyone else** on the Google Meet call

### Hotkey Cheat Sheet

| Hotkey | Action |
|--------|--------|
| `⌥S` or `⌘⇧S` | Toggle Stealth HUD visibility |
| `⌥A` or `⌘⇧A` | Listen for question & generate answer |
| `Enter` | Submit typed question |
| `Esc` | Hide HUD |

### System Audio Capture (Optional — Hear Friend's Voice)

By default, Jarvis listens through your physical microphone. To capture your friend's voice directly from Google Meet's audio output, install a virtual audio loopback driver:

```bash
# One-time setup (BlackHole — free, open-source)
brew install blackhole-2ch
```

Then create a **Multi-Output Device** in macOS:
1. Open **Audio MIDI Setup** (Spotlight → "Audio MIDI Setup")
2. Click **"+"** at the bottom → **Create Multi-Output Device**
3. Check both **"BlackHole 2ch"** and your speakers/headphones
4. Set the Multi-Output Device as your system sound output in System Settings

Jarvis will automatically detect BlackHole and switch to system audio capture. The HUD shows `🔊 System Audio (BlackHole)` when active, or `🎤 Physical Mic Only` when using the default microphone.

### Answer Pipeline

Jarvis uses a cascading answer pipeline for maximum speed and reliability:

1. **Local Knowledge Base** (instant, <50ms) — Flash answer for common CS topics
2. **Antigravity CLI** (`antigravity prompt`) — Primary engine for full answers
3. **Antigravity Python SDK** — Fallback if CLI is not installed
4. **Deterministic Synthesis** — Last-resort generic answer

---

## 📄 License

MIT License — Feel free to modify and make it your own!

---

*Built with ❤️ by Ashwin Gajbhiye — Powered by Google Gemini*
