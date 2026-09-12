#!/usr/bin/env python3
import os
import stat
import shutil

APP_NAME = "Jarvis.app"
PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
APP_DIR = os.path.expanduser("~/Applications")
DESKTOP_DIR = os.path.expanduser("~/Desktop")

PRIMARY_APP_PATH = os.path.join(APP_DIR, APP_NAME)
DESKTOP_APP_PATH = os.path.join(DESKTOP_DIR, APP_NAME)

os.makedirs(APP_DIR, exist_ok=True)
os.makedirs(os.path.expanduser("~/.jarvis"), exist_ok=True)

# Remove existing app bundles if they exist
for target in [PRIMARY_APP_PATH, DESKTOP_APP_PATH]:
    if os.path.exists(target):
        if os.path.islink(target):
            os.unlink(target)
        elif os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)

# Create directory structure
macos_dir = os.path.join(PRIMARY_APP_PATH, "Contents", "MacOS")
os.makedirs(macos_dir, exist_ok=True)

# Create the executable wrapper script
wrapper_script = os.path.join(macos_dir, "Jarvis")
log_path = os.path.expanduser("~/.jarvis/app_error.log")

with open(wrapper_script, "w") as f:
    f.write(f'''#!/bin/bash
# Move to project directory
cd "{PROJECT_DIR}"

# Set full system PATH
export PATH="/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH"

# Run Jarvis GUI
exec "{PROJECT_DIR}/venv/bin/python" "{PROJECT_DIR}/main.py" >> "{log_path}" 2>&1
''')

# Make the wrapper executable
os.chmod(wrapper_script, os.stat(wrapper_script).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

# Create Info.plist with LSUIElement=false so it activates normally in Dock and screen
plist_path = os.path.join(PRIMARY_APP_PATH, "Contents", "Info.plist")
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
    <key>CFBundleShortVersionString</key>
    <string>2.0</string>
    <key>LSUIElement</key>
    <false/>
    <key>NSMicrophoneUsageDescription</key>
    <string>Jarvis needs access to your microphone to listen for voice commands.</string>
</dict>
</plist>
''')

# Copy to Desktop so user has a direct, clickable app on Desktop
shutil.copytree(PRIMARY_APP_PATH, DESKTOP_APP_PATH)

print(f"✅ Successfully created {PRIMARY_APP_PATH}")
print(f"✅ Successfully created {DESKTOP_APP_PATH}")
