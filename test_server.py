import threading
import uvicorn
from fastapi import FastAPI
import time

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

def _run_server():
    try:
        uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
    except Exception as e:
        print(f"UVICORN THREAD ERROR: {e}")

thread = threading.Thread(target=_run_server, daemon=True)
thread.start()

print("Started thread. Waiting 5s...")
time.sleep(5)
print("Done.")
