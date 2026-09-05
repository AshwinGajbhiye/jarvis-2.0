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

## 📄 License

MIT License — Feel free to modify and make it your own!

---

*Built with ❤️ by Ashwin Gajbhiye — Powered by Google Gemini*
