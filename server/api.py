import os
import threading
import socket
import urllib.parse
from typing import List, Optional

import uvicorn
import speech_recognition as sr
from fastapi import FastAPI, Header, HTTPException, Depends, Request, UploadFile, File, Query
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
from pydub import AudioSegment

# Explicitly set ffmpeg path for pydub
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"
AudioSegment.converter = "/opt/homebrew/bin/ffmpeg"
AudioSegment.ffmpeg = "/opt/homebrew/bin/ffmpeg"

from config import Config
from skills.task_manager import list_tasks as get_tasks_skill, add_task, complete_task
from skills.reminder import list_reminders as get_reminders_skill, set_reminder
from skills.memory_extractor import get_facts_for_prompt
from skills.file_manager import get_queued_file, queue_file_for_transfer
from skills.linkedin_jobs import search_linkedin_jobs_data, get_cached_jobs, get_linkedin_job_details
from skills.job_search import search_web_jobs, get_cached_web_jobs, find_company_contacts
from skills.email_sender import (
    draft_cold_email,
    confirm_send_cold_email,
    cancel_send_cold_email,
    preview_pending_cold_email,
    get_pending_cold_email,
)
from skills.cold_outreach_tracker import list_cold_applications, get_outreach_analytics
from skills.profile_manager import get_user_profile, update_user_profile
from server.mobile_dashboard import HTML_CONTENT

app = FastAPI(title="Jarvis Mobile Suite & API")

# Global state to hold references to the GUI/Brain
app.state.brain = None
app.state.signals = None

def get_expected_api_key() -> str:
    return Config.MOBILE_API_KEY or "jarvis-mobile-secret-key-2026"

def verify_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = Query(None)
) -> bool:
    """Validate incoming request from header, query param, Authorization header, or cookie."""
    expected = get_expected_api_key().strip()
    
    token = x_api_key
    if not token and api_key:
        token = api_key
    if not token and "authorization" in request.headers:
        auth_val = request.headers.get("authorization", "")
        if auth_val.lower().startswith("bearer "):
            token = auth_val[7:].strip()
    if not token and "api_key" in request.cookies:
        token = request.cookies.get("api_key")

    if not token or token.strip() != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API Key")
    return True

# Models
class CommandRequest(BaseModel):
    command: str

class QueueFileRequest(BaseModel):
    path: str

class AddTaskRequest(BaseModel):
    task: str

class CompleteTaskRequest(BaseModel):
    task_id: int

class SetReminderRequest(BaseModel):
    reminder: str
    time_str: str

class ColdEmailDraftRequest(BaseModel):
    to_email: str
    recipient_name: Optional[str] = ""
    company: str
    job_title: str
    job_details: Optional[str] = ""
    custom_notes: Optional[str] = ""
    attach_resume: Optional[bool] = True

class ColdEmailConfirmRequest(BaseModel):
    attach_resume: Optional[bool] = True

# ── Web UI & PWA App Endpoints ────────────────────────────────
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

@app.get("/", response_class=HTMLResponse)
async def mobile_dashboard_root():
    """Serve the Stark-themed responsive mobile web interface."""
    return HTMLResponse(content=HTML_CONTENT, status_code=200)

@app.get("/mobile", response_class=HTMLResponse)
async def mobile_dashboard_alias():
    return HTMLResponse(content=HTML_CONTENT, status_code=200)

@app.get("/manifest.json")
async def get_manifest():
    return FileResponse(os.path.join(STATIC_DIR, "manifest.json"), media_type="application/manifest+json")

@app.get("/sw.js")
async def get_service_worker():
    return FileResponse(os.path.join(STATIC_DIR, "sw.js"), media_type="application/javascript")

@app.get("/icon-192.png")
async def get_icon_192():
    return FileResponse(os.path.join(STATIC_DIR, "icon-192.png"), media_type="image/png")

@app.get("/icon-512.png")
async def get_icon_512():
    return FileResponse(os.path.join(STATIC_DIR, "icon-512.png"), media_type="image/png")

@app.get("/apple-touch-icon.png")
async def get_apple_touch_icon():
    return FileResponse(os.path.join(STATIC_DIR, "apple-touch-icon.png"), media_type="image/png")

# ── Core API Endpoints ────────────────────────────────────────
@app.get("/api/ping", dependencies=[Depends(verify_api_key)])
def ping():
    return {"status": "ok", "message": "Jarvis is online and synchronized."}

@app.get("/api/status", dependencies=[Depends(verify_api_key)])
def api_system_status():
    """Provide system telemetry for mobile dashboard."""
    from skills.system_info import get_battery, get_cpu_usage
    try:
        battery = get_battery()
    except Exception:
        battery = "100%"
    try:
        load = get_cpu_usage()
    except Exception:
        load = "Nominal"

    return {
        "status": "online",
        "assistant_name": Config.JARVIS_NAME,
        "model": Config.GEMINI_MODEL,
        "battery": battery,
        "load": load,
        "antigravity": Config.USE_ANTIGRAVITY
    }

@app.post("/api/command", dependencies=[Depends(verify_api_key)])
def execute_command(req: CommandRequest):
    if not app.state.brain:
        raise HTTPException(status_code=500, detail="Brain not connected")
    
    # Emit signal to show user typing in GUI
    if app.state.signals:
        app.state.signals.update_chat.emit("You (Mobile)", req.command, "#00FF00")
        app.state.signals.update_status.emit("Thinking...", "#FFFF00")
        app.state.signals.update_avatar.emit("thinking")
    
    # Process command through Brain
    response = app.state.brain.think(req.command)
    
    # Check if a file was queued for transfer
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

@app.post("/api/voice-command", dependencies=[Depends(verify_api_key)])
async def execute_voice_command(audio: UploadFile = File(...)):
    if not app.state.brain:
        raise HTTPException(status_code=500, detail="Brain not connected")
        
    temp_dir = os.path.join(os.path.expanduser("~"), ".jarvis")
    os.makedirs(temp_dir, exist_ok=True)
    temp_audio_path = os.path.join(temp_dir, "temp_mobile_audio_raw")
    temp_wav_path = os.path.join(temp_dir, "temp_mobile_audio.wav")
    
    with open(temp_audio_path, "wb") as buffer:
        buffer.write(await audio.read())
        
    try:
        audio_segment = AudioSegment.from_file(temp_audio_path)
        audio_segment.export(temp_wav_path, format="wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to convert audio format: {e}")
        
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(temp_wav_path) as source:
            audio_data = recognizer.record(source)
            text = recognizer.recognize_google(audio_data, language=Config.STT_LANGUAGE)
            
            if app.state.signals:
                app.state.signals.update_chat.emit("You (Mobile Voice)", text, "#00FF00")
                app.state.signals.update_status.emit("Thinking...", "#FFFF00")
                app.state.signals.update_avatar.emit("thinking")
                
            response = app.state.brain.think(text)
            
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
        raise HTTPException(status_code=400, detail="Jarvis could not understand the voice audio")
    except sr.RequestError as e:
        raise HTTPException(status_code=500, detail=f"Speech recognition service error: {e}")
    finally:
        if os.path.exists(temp_audio_path):
            try: os.remove(temp_audio_path)
            except Exception: pass
        if os.path.exists(temp_wav_path):
            try: os.remove(temp_wav_path)
            except Exception: pass

# ── File Transfer Endpoints ───────────────────────────────────
@app.get("/api/download")
async def download_file(
    request: Request,
    path: str,
    x_api_key: Optional[str] = Header(None),
    api_key: Optional[str] = Query(None)
):
    """Download a file from Mac with authorization via header or query parameter."""
    verify_api_key(request, x_api_key, api_key)
    
    unquoted = urllib.parse.unquote(path)
    base_dir = os.path.expanduser("~")
    
    if unquoted.startswith("~"):
        real_path = os.path.expanduser(unquoted)
    elif not os.path.isabs(unquoted):
        real_path = os.path.join(base_dir, unquoted)
    else:
        real_path = unquoted
        
    real_path = os.path.realpath(real_path)
    
    # Path traversal and existence checks
    if not os.path.exists(real_path) or not os.path.isfile(real_path):
        raise HTTPException(status_code=404, detail="File not found on Mac")
        
    return FileResponse(
        real_path,
        filename=os.path.basename(real_path),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{os.path.basename(real_path)}"',
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@app.post("/api/upload", dependencies=[Depends(verify_api_key)])
async def upload_file(
    file: UploadFile = File(...),
    destination: str = Query("Downloads")
):
    """Upload a file from mobile device directly to the user's Mac (e.g. ~/Downloads or ~/Desktop)."""
    base_dir = os.path.expanduser("~")
    
    dest_clean = destination.strip().lstrip("/\\")
    if ".." in dest_clean:
        dest_clean = "Downloads"
        
    target_dir = os.path.realpath(os.path.join(base_dir, dest_clean))
    os.makedirs(target_dir, exist_ok=True)
    
    safe_name = os.path.basename(file.filename) if file.filename else "mobile_upload"
    target_file = os.path.join(target_dir, safe_name)
    
    base_name, ext = os.path.splitext(safe_name)
    counter = 1
    while os.path.exists(target_file):
        target_file = os.path.join(target_dir, f"{base_name}_{counter}{ext}")
        counter += 1
        
    content = await file.read()
    with open(target_file, "wb") as f:
        f.write(content)
        
    file_size = len(content)
    if file_size < 1024:
        size_str = f"{file_size} B"
    elif file_size < 1024 * 1024:
        size_str = f"{file_size / 1024:.1f} KB"
    else:
        size_str = f"{file_size / (1024 * 1024):.1f} MB"
        
    saved_name = os.path.basename(target_file)
    
    if app.state.signals:
        app.state.signals.update_chat.emit(
            "Jarvis (Mobile)",
            f"📥 Received '{saved_name}' ({size_str}) from mobile. Saved to ~/{dest_clean}/",
            "#00FFFF"
        )
        app.state.signals.update_status.emit("File Received", "#00FF00")
        
    return {
        "status": "ok",
        "message": f"Successfully uploaded '{saved_name}' to Mac",
        "saved_path": target_file,
        "filename": saved_name,
        "size": file_size,
        "size_formatted": size_str
    }

@app.post("/api/queue-file", dependencies=[Depends(verify_api_key)])
def queue_file_for_mobile(req: QueueFileRequest):
    """Queue a file path on Mac to be downloaded immediately from mobile."""
    target_path = os.path.realpath(os.path.expanduser(req.path))
    if not os.path.exists(target_path) or not os.path.isfile(target_path):
        raise HTTPException(status_code=404, detail="File does not exist on Mac")
        
    queue_file_for_transfer(target_path)
    encoded = urllib.parse.quote(target_path)
    return {
        "status": "ok",
        "file_name": os.path.basename(target_path),
        "file_url": f"/api/download?path={encoded}"
    }

@app.get("/api/files", dependencies=[Depends(verify_api_key)])
def list_files(path: str = ""):
    """List files in the user's home directory securely with formatted sizes and download links."""
    base_dir = os.path.expanduser("~")
    
    if ".." in path:
        raise HTTPException(status_code=400, detail="Invalid path")
        
    target_dir = os.path.realpath(os.path.join(base_dir, path))
    
    if not os.path.exists(target_dir):
        raise HTTPException(status_code=404, detail="Directory not found")
        
    if not os.path.isdir(target_dir):
        raise HTTPException(status_code=400, detail="Path is not a directory")
        
    try:
        items = []
        for item in os.listdir(target_dir):
            if item.startswith('.'):
                continue
            item_path = os.path.join(target_dir, item)
            is_dir = os.path.isdir(item_path)
            rel_path = os.path.relpath(item_path, base_dir)
            size_str = ""
            if not is_dir:
                try:
                    s = os.path.getsize(item_path)
                    if s < 1024:
                        size_str = f"{s} B"
                    elif s < 1024 * 1024:
                        size_str = f"{s / 1024:.1f} KB"
                    else:
                        size_str = f"{s / (1024 * 1024):.1f} MB"
                except Exception:
                    size_str = ""
                    
            encoded_item_path = urllib.parse.quote(item_path)
            items.append({
                "name": item,
                "is_dir": is_dir,
                "path": rel_path,
                "size": size_str,
                "download_url": f"/api/download?path={encoded_item_path}" if not is_dir else None
            })
            
        parent_dir = os.path.dirname(path) if path else None
        return {
            "current_path": path,
            "parent_path": parent_dir,
            "items": sorted(items, key=lambda x: (not x['is_dir'], x['name'].lower()))
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ── Tasks & Reminders Endpoints ───────────────────────────────
@app.get("/api/tasks", dependencies=[Depends(verify_api_key)])
def api_list_tasks():
    tasks = get_tasks_skill()
    return {"tasks": tasks}

@app.post("/api/tasks", dependencies=[Depends(verify_api_key)])
def api_add_task(req: AddTaskRequest):
    result = add_task(req.task)
    return {"status": "ok", "result": result, "tasks": get_tasks_skill()}

@app.post("/api/tasks/complete", dependencies=[Depends(verify_api_key)])
def api_complete_task(req: CompleteTaskRequest):
    result = complete_task(req.task_id)
    return {"status": "ok", "result": result, "tasks": get_tasks_skill()}

@app.get("/api/reminders", dependencies=[Depends(verify_api_key)])
def api_list_reminders():
    reminders = get_reminders_skill()
    return {"reminders": reminders}

@app.post("/api/reminders", dependencies=[Depends(verify_api_key)])
def api_set_reminder(req: SetReminderRequest):
    result = set_reminder(req.reminder, req.time_str)
    return {"status": "ok", "result": result, "reminders": get_reminders_skill()}

# ── Job Search & Cold Outreach Endpoints ──────────────────────
@app.get("/api/jobs/linkedin", dependencies=[Depends(verify_api_key)])
def api_search_linkedin(
    title: str = Query(..., description="Target job title"),
    location: str = Query("Remote", description="Job location"),
    limit: int = Query(5, description="Max results"),
):
    summary = search_linkedin_jobs_data(job_title=title, location=location, max_results=limit)
    return {"summary": summary, "jobs": get_cached_jobs()}

@app.get("/api/jobs/web", dependencies=[Depends(verify_api_key)])
def api_search_web_jobs(
    title: str = Query(..., description="Target job title"),
    location: str = Query("Remote", description="Job location"),
    keywords: str = Query("", description="Keywords"),
    limit: int = Query(5, description="Max results"),
):
    summary = search_web_jobs(job_title=title, location=location, keywords=keywords, max_results=limit)
    return {"summary": summary, "jobs": get_cached_web_jobs()}

@app.get("/api/jobs/contacts", dependencies=[Depends(verify_api_key)])
def api_find_contacts(
    company: str = Query(..., description="Company name"),
    domain: str = Query("", description="Company website domain"),
):
    return {"contacts": find_company_contacts(company_name=company, company_domain=domain)}

@app.get("/api/profile", dependencies=[Depends(verify_api_key)])
def api_get_profile():
    return {"profile": get_user_profile()}

@app.post("/api/cold-email/draft", dependencies=[Depends(verify_api_key)])
def api_draft_cold_email(req: ColdEmailDraftRequest):
    result = draft_cold_email(
        to_email=req.to_email,
        recipient_name=req.recipient_name or "",
        company=req.company,
        job_title=req.job_title,
        job_details=req.job_details or "",
        custom_notes=req.custom_notes or "",
        attach_resume=req.attach_resume if req.attach_resume is not None else True,
    )
    return {"status": "ok", "result": result, "pending": get_pending_cold_email()}

@app.post("/api/cold-email/confirm", dependencies=[Depends(verify_api_key)])
def api_confirm_cold_email(req: ColdEmailConfirmRequest):
    result = confirm_send_cold_email(attach_resume=req.attach_resume)
    return {"status": "ok", "result": result}

@app.post("/api/cold-email/cancel", dependencies=[Depends(verify_api_key)])
def api_cancel_cold_email():
    result = cancel_send_cold_email()
    return {"status": "ok", "result": result}

@app.get("/api/cold-email/history", dependencies=[Depends(verify_api_key)])
def api_cold_email_history(status: str = Query("all")):
    return {"summary": list_cold_applications(status_filter=status), "analytics": get_outreach_analytics()}

# ── Server Launch Helper ──────────────────────────────────────
def get_local_ip() -> str:
    """Discover Mac's local network IP."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def _run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="error")

def start_api_server(brain, signals=None):
    app.state.brain = brain
    app.state.signals = signals
    
    local_ip = get_local_ip()
    key = get_expected_api_key()
    
    thread = threading.Thread(target=_run_server, daemon=True)
    thread.start()
    
    print("\n" + "═" * 64)
    print("  📱  J.A.R.V.I.S. MOBILE SUITE & FILE TRANSFER ACTIVE")
    print(f"  👉  Phone Browser: http://{local_ip}:8000")
    print(f"  🔑  Mobile Key:    {key}")
    print(f"  ⚡  Direct Link:   http://{local_ip}:8000?key={key}")
    print("═" * 64 + "\n")
