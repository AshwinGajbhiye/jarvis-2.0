#!/usr/bin/env python3
import os
import stat
import shutil

APP_NAME = "Jarvis.app"
DEST_DIR = os.path.expanduser("~/Desktop")
APP_PATH = os.path.join(DEST_DIR, APP_NAME)
PROJECT_DIR = "/Users/ashwingajbhiye/jarvis"

# Ensure the destination Applications directory exists
import os
os.makedirs(DEST_DIR, exist_ok=True)

# Remove existing app if it exists
if os.path.exists(APP_PATH):
    import shutil
    shutil.rmtree(APP_PATH)

# Create directory structure
macos_dir = os.path.join(APP_PATH, "Contents", "MacOS")
os.makedirs(macos_dir)

# Create the executable wrapper script
import stat
wrapper_script = os.path.join(macos_dir, "Jarvis")
with open(wrapper_script, "w") as f:
    f.write(f'''#!/bin/bash
# Move to the project directory
cd {PROJECT_DIR}

# Run Jarvis and log output to help debug. Force arm64 execution.
exec arch -arm64 {PROJECT_DIR}/venv/bin/python main.py > {PROJECT_DIR}/app_error.log 2>&1
''')

# Make the wrapper executable
os.chmod(wrapper_script, os.stat(wrapper_script).st_mode | stat.S_IEXEC)

# Create the Info.plist
# LSUIElement = true ensures it runs as a background agent (no Dock icon)
plist_path = os.path.join(APP_PATH, "Contents", "Info.plist")
with open(plist_path, "w") as f:
    f.write('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>Jarvis</string>
    <key>CFBundleIdentifier</key>
    <string>com.ashwingajbhiye.jarvis</string>
    <key>CFBundleName</key>
    <string>Jarvis</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSUIElement</key>
    <true/>
    <key>NSMicrophoneUsageDescription</key>
    <string>Jarvis needs access to your microphone to listen for commands.</string>
</dict>
</plist>
''')

print(f"✅ Successfully created {APP_PATH}")
print("You can now add it to Login Items to start automatically on boot.")


