import os
import sys
import time
import urllib.parse
from fastapi.testclient import TestClient

# Ensure root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from brain import Brain
from server.api import app, get_expected_api_key

def test_mobile_suite():
    print("🚀 Initializing TestClient for Jarvis Mobile API...")
    brain = Brain()
    app.state.brain = brain
    
    client = TestClient(app)
    api_key = get_expected_api_key()
    print(f"🔑 Using API Key: {api_key}")
    
    # 1. Test Web Dashboard
    print("\n--- 1. Testing Web Dashboard (GET /) ---")
    res = client.get("/")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    assert "J.A.R.V.I.S." in res.text
    assert "QUANTUM COMMUNICATIONS FEED" in res.text
    print("✅ Web Dashboard served successfully (Status 200)")

    # 2. Test Ping with Header and Query Param
    print("\n--- 2. Testing Ping Auth ---")
    # Missing key
    res = client.get("/api/ping")
    assert res.status_code == 401, f"Expected 401, got {res.status_code}"
    # Header auth
    res = client.get("/api/ping", headers={"x-api-key": api_key})
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    # Query param auth
    res = client.get(f"/api/ping?api_key={api_key}")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    print("✅ Header and Query Param authentication verified")

    # 3. Test File Search & Queue via Command
    print("\n--- 3. Testing Mac-to-Mobile File Search Command ---")
    res = client.post(
        "/api/command",
        headers={"x-api-key": api_key},
        json={"command": "send me 5th_sem_result.png to mobile"}
    )
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    data = res.json()
    print("Command response:", data)
    assert "file_url" in data, f"Expected file_url in response: {data}"
    assert "file_name" in data
    assert "5th_sem_result.png" in data["file_name"]
    file_url = data["file_url"]
    print(f"✅ File search queued successfully: {data['file_name']} -> {file_url}")

    # 4. Test File Download via Download Endpoint
    print("\n--- 4. Testing File Download Endpoint ---")
    # Using query param key
    download_req_url = f"{file_url}&api_key={api_key}"
    res = client.get(download_req_url)
    assert res.status_code == 200, f"Download failed: {res.status_code}"
    assert len(res.content) > 0
    print(f"✅ Successfully downloaded {len(res.content)} bytes from Mac")

    # 5. Test Mobile-to-Mac File Upload
    print("\n--- 5. Testing Mobile-to-Mac File Upload (POST /api/upload) ---")
    dummy_content = b"Hello Jarvis! This is a test mobile upload file."
    files = {"file": ("mobile_test_sync.txt", dummy_content, "text/plain")}
    res = client.post(
        "/api/upload?destination=Downloads",
        headers={"x-api-key": api_key},
        files=files
    )
    assert res.status_code == 200, f"Upload failed: {res.status_code} - {res.text}"
    upload_data = res.json()
    print("Upload response:", upload_data)
    uploaded_path = upload_data["saved_path"]
    assert os.path.exists(uploaded_path), f"File not found on Mac: {uploaded_path}"
    with open(uploaded_path, "rb") as f:
        saved_bytes = f.read()
    assert saved_bytes == dummy_content
    print(f"✅ File uploaded to Mac at {uploaded_path} with verified checksum")
    # Clean up test file
    try:
        os.remove(uploaded_path)
    except Exception:
        pass

    # 6. Test Remote File Explorer (GET /api/files)
    print("\n--- 6. Testing Remote File Explorer ---")
    res = client.get("/api/files?path=Desktop", headers={"x-api-key": api_key})
    assert res.status_code == 200
    files_data = res.json()
    assert "items" in files_data
    print(f"✅ Listed {len(files_data['items'])} items in ~/Desktop")

    # 7. Test Tasks Endpoints
    print("\n--- 7. Testing Tasks API ---")
    res = client.post(
        "/api/tasks",
        headers={"x-api-key": api_key},
        json={"task": "Test mobile sync mission"}
    )
    assert res.status_code == 200
    res = client.get("/api/tasks", headers={"x-api-key": api_key})
    assert res.status_code == 200
    tasks_data = res.json()
    print(f"✅ Tasks retrieved: {len(tasks_data.get('tasks', []))} active tasks")

    # 8. Test Telemetry (GET /api/status)
    print("\n--- 8. Testing System Telemetry ---")
    res = client.get("/api/status", headers={"x-api-key": api_key})
    assert res.status_code == 200
    status_data = res.json()
    print("Telemetry:", status_data)
    assert status_data["status"] == "online"
    print("✅ Telemetry active")

    print("\n🎉 ALL MOBILE SUITE AND FILE TRANSFER TESTS PASSED!")

if __name__ == "__main__":
    test_mobile_suite()
