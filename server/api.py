import os
import threading
import uvicorn
import speech_recognition as sr
from fastapi import FastAPI, Header, HTTPException, Depends, Request, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional
from pydub import AudioSegment
import urllib.parse
from fastapi.responses import FileResponse

# Explicitly set ffmpeg path for pydub to fix RuntimeWarning
import os
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"
AudioSegment.converter = "/opt/homebrew/bin/ffmpeg"
AudioSegment.ffmpeg = "/opt/homebrew/bin/ffmpeg"

from config import Config
from skills.task_manager import list_tasks as get_tasks_skill, add_task, complete_task
from skills.reminder import list_reminders as get_reminders_skill, set_reminder
from skills.memory_extractor import get_facts_for_prompt
from skills.file_manager import get_queued_file

app = FastAPI(title="Jarvis Mobile API")

# Global state to hold references to the GUI/Brain
app.state.brain = None
app.state.signals = None

def verify_api_key(x_api_key: str = Header(None)):
    if not Config.MOBILE_API_KEY:
        raise HTTPException(status_code=500, detail="Mobile API Key not configured on Mac.")
    if x_api_key != Config.MOBILE_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return True

class CommandRequest(BaseModel):
    command: str

@app.get("/api/ping", dependencies=[Depends(verify_api_key)])
def ping():
    return {"status": "ok", "message": "Jarvis is online."}

@app.post("/api/command", dependencies=[Depends(verify_api_key)])
def execute_command(req: CommandRequest):
    if not app.state.brain:
        raise HTTPException(status_code=500, detail="Brain not connected")
    
    # Emit signal to show user typing in GUI
    if app.state.signals:
        app.state.signals.update_chat.emit("You", req.command, "#00FF00")
        app.state.signals.update_status.emit("Thinking...", "#FFFF00")
        app.state.signals.update_avatar.emit("thinking")
    
    # Process the command
    response = app.state.brain.think(req.command)
    
    # Check if a file was queued
    queued_file = get_queued_file()
    response_data = {"response": response}
    
    if queued_file and os.path.exists(queued_file):
        encoded_path = urllib.parse.quote(queued_file)
        response_data["file_url"] = f"/api/download?path={encoded_path}"
        response_data["file_name"] = os.path.basename(queued_file)

    # Emit signal to show Jarvis response in GUI
    if app.state.signals:
        app.state.signals.update_chat.emit(Config.JARVIS_NAME, response, "#00FFFF")
        app.state.signals.update_status.emit("Online", "#00FF00")
        app.state.signals.update_avatar.emit("idle")
        if hasattr(app.state.brain, 'get_quota_string'):
            app.state.signals.update_quota.emit(app.state.brain.get_quota_string())
            
    return response_data

@app.get("/api/download")
async def download_file(path: str, x_api_key: str = Header(...)):
    if x_api_key != Config.MOBILE_API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    if not os.path.exists(path) or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found on Mac")
        
    return FileResponse(path, filename=os.path.basename(path))

@app.post("/api/voice-command", dependencies=[Depends(verify_api_key)])
async def execute_voice_command(audio: UploadFile = File(...)):
    if not app.state.brain:
        raise HTTPException(status_code=500, detail="Brain not connected")
        
    # Save the uploaded file temporarily
    temp_audio_path = os.path.join(os.path.expanduser("~"), ".jarvis", "temp_mobile_audio_raw")
    temp_wav_path = os.path.join(os.path.expanduser("~"), ".jarvis", "temp_mobile_audio.wav")
    os.makedirs(os.path.dirname(temp_audio_path), exist_ok=True)
    
    with open(temp_audio_path, "wb") as buffer:
        buffer.write(await audio.read())
        
    try:
        # Convert any incoming format (m4a, 3gp, mp4, etc) to standard PCM WAV
        audio_segment = AudioSegment.from_file(temp_audio_path)
        audio_segment.export(temp_wav_path, format="wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert audio format: {e}")
        
    # Process with SpeechRecognition
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(temp_wav_path) as source:
            audio_data = recognizer.record(source)
            # Use Google Web Speech API (free)
            text = recognizer.recognize_google(audio_data, language=Config.STT_LANGUAGE)
            
            # Now execute it exactly like a text command
            if app.state.signals:
                app.state.signals.update_chat.emit("You (Mobile Voice)", text, "#00FF00")
                app.state.signals.update_status.emit("Thinking...", "#FFFF00")
                app.state.signals.update_avatar.emit("thinking")
                
            response = app.state.brain.think(text)
            
            # Check if a file was queued
            queued_file = get_queued_file()
            response_data = {"text_recognized": text, "response": response}
            
            if queued_file and os.path.exists(queued_file):
                encoded_path = urllib.parse.quote(queued_file)
                response_data["file_url"] = f"/api/download?path={encoded_path}"
                response_data["file_name"] = os.path.basename(queued_file)
            
            if app.state.signals:
                app.state.signals.update_chat.emit(Config.JARVIS_NAME, response, "#00FFFF")
                app.state.signals.update_status.emit("Online", "#00FF00")
                app.state.signals.update_avatar.emit("idle")
                if hasattr(app.state.brain, 'get_quota_string'):
                    app.state.signals.update_quota.emit(app.state.brain.get_quota_string())
                    
            return response_data
    except sr.UnknownValueError:
        raise HTTPException(status_code=400, detail="Jarvis could not understand the audio")
    except sr.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Could not request results from Google Speech Recognition service; {e}")
    finally:
        # Clean up
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
        if os.path.exists(temp_wav_path):
            os.remove(temp_wav_path)

@app.get("/api/tasks", dependencies=[Depends(verify_api_key)])
def api_list_tasks():
    tasks = get_tasks_skill()
    return {"tasks": tasks}

@app.get("/api/reminders", dependencies=[Depends(verify_api_key)])
def api_list_reminders():
    reminders = get_reminders_skill()
    return {"reminders": reminders}

@app.get("/api/files", dependencies=[Depends(verify_api_key)])
def list_files(path: str = ""):
    """List files in the user's home directory securely."""
    base_dir = os.path.expanduser("~")
    
    # Prevent directory traversal attacks
    if ".." in path:
        raise HTTPException(status_code=400, detail="Invalid path")
        
    target_dir = os.path.join(base_dir, path)
    
    if not os.path.exists(target_dir):
        raise HTTPException(status_code=404, detail="Directory not found")
        
    if not os.path.isdir(target_dir):
        raise HTTPException(status_code=400, detail="Path is not a directory")
        
    try:
        items = []
        for item in os.listdir(target_dir):
            # Skip hidden files
            if item.startswith('.'):
                continue
            item_path = os.path.join(target_dir, item)
            is_dir = os.path.isdir(item_path)
            items.append({
                "name": item,
                "is_dir": is_dir,
                "path": os.path.join(path, item) if path else item
            })
        return {"current_path": path, "items": sorted(items, key=lambda x: (not x['is_dir'], x['name'].lower()))}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")

def start_api_server(brain, signals):
    app.state.brain = brain
    app.state.signals = signals
    
    thread = threading.Thread(target=_run_server, daemon=True)
    thread.start()
    print("✅ Jarvis Mobile API Server running on port 8000")
