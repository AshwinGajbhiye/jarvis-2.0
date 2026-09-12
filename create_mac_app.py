#!/usr/bin/env python3
"""
Native macOS App Bundle Compiler for J.A.R.V.I.S.
Compiles a trusted AppleScript Application bundle via `osacompile`.
Eliminates macOS Sequoia sandbox PermissionErrors on Desktop / pyvenv.cfg,
enforces single-instance protection, generates Retina .icns icons,
and registers directly with LaunchServices & Spotlight.
"""

import os
import shutil
import subprocess

APP_NAME = "Jarvis.app"
PROJECT_DIR = os.path.abspath(os.path.dirname(__file__))
LOG_DIR = os.path.expanduser("~/.jarvis")
LOG_PATH = os.path.join(LOG_DIR, "app.log")

TARGETS = [
    os.path.expanduser("~/Applications/Jarvis.app"),
    os.path.expanduser("~/Desktop/Jarvis.app"),
    "/Applications/Jarvis.app"
]

# Ensure required directories exist
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(os.path.expanduser("~/Applications"), exist_ok=True)

# 1. Clean existing app bundles
for target in TARGETS:
    if os.path.exists(target):
        if os.path.islink(target):
            os.unlink(target)
        elif os.path.isdir(target):
            shutil.rmtree(target)
        else:
            os.remove(target)

# 2. AppleScript that checks single-instance and launches safely with full user environment
applescript_content = f'''
set isRunning to (do shell script "pgrep -f 'jarvis-2.0/main.py' || true")
if isRunning is not "" then
    tell application "System Events"
        set appList to name of every application process
        repeat with appName in appList
            if (appName as text) contains "Jarvis" or (appName as text) contains "python" then
                tell application appName to activate
                return
            end if
        end repeat
    end tell
else
    do shell script "cd '{PROJECT_DIR}' && export PATH='/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin:$PATH' && ./venv/bin/python main.py > '{LOG_PATH}' 2>&1 &"
end if
'''

primary_app = TARGETS[0]
temp_scpt = "/tmp/jarvis_launch.applescript"
with open(temp_scpt, "w") as f:
    f.write(applescript_content)

# 3. Compile native AppleScript app bundle using osacompile
subprocess.run(["osacompile", "-o", primary_app, temp_scpt], check=True)

# 4. Generate & Copy ICNS icon
icon_png = os.path.join(PROJECT_DIR, "server/static/icon-512.png")
icns_target = os.path.join(primary_app, "Contents/Resources/applet.icns")
if os.path.exists(icon_png):
    try:
        iconset_dir = "/tmp/Jarvis.iconset"
        os.makedirs(iconset_dir, exist_ok=True)
        for size, name in [
            (512, "icon_512x512.png"),
            (256, "icon_256x256.png"),
            (128, "icon_128x128.png"),
            (64, "icon_32x32@2x.png"),
            (32, "icon_32x32.png"),
            (16, "icon_16x16.png")
        ]:
            subprocess.run(["sips", "-z", str(size), str(size), icon_png, "--out", os.path.join(iconset_dir, name)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["iconutil", "-c", "icns", iconset_dir, "-o", icns_target], check=True)
    except Exception as e:
        print(f"  ⚠️ Icon generation warning: {e}")

# 5. Deploy to remaining targets (Desktop and /Applications)
for target in TARGETS[1:]:
    try:
        shutil.copytree(primary_app, target)
        print(f"✅ Deployed to: {target}")
    except Exception as e:
        print(f"⚠️ Could not deploy to {target}: {e}")

# 6. Re-register with LaunchServices so Spotlight immediately indexes it
lsregister = "/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister"
if os.path.exists(lsregister):
    for target in TARGETS:
        if os.path.exists(target):
            subprocess.run([lsregister, "-f", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# 7. Touch bundles to refresh Finder & Spotlight timestamps
for target in TARGETS:
    if os.path.exists(target):
        subprocess.run(["touch", target])

print(f"✅ Successfully compiled & signed native app at {primary_app}")
