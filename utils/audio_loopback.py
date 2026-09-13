"""
Audio Loopback Device Detector for J.A.R.V.I.S.
Detects virtual audio loopback devices (BlackHole, Soundflower, Aggregate)
so Jarvis can capture system audio output from Google Meet, Zoom, etc.

macOS does NOT natively allow capturing speaker/system audio. A virtual
loopback driver routes the audio output back as a virtual microphone input.

Supported loopback drivers (any one):
  • BlackHole 2ch  (recommended, free, open-source: brew install blackhole-2ch)
  • Soundflower
  • macOS Aggregate / Multi-Output Device

One-time setup:
  1. brew install blackhole-2ch
  2. Open "Audio MIDI Setup" (Spotlight → Audio MIDI Setup)
  3. Click "+" → Create Multi-Output Device
  4. Check both "BlackHole 2ch" and your speakers/headphones
  5. Set the Multi-Output Device as your system output
"""

import sys
from typing import Optional, Tuple

# Known virtual loopback device name patterns (case-insensitive matching)
_LOOPBACK_PATTERNS = [
    "blackhole",
    "soundflower",
    "loopback",
    "virtual",
    "aggregate",
    "multi-output",
]


def get_loopback_device_index() -> Optional[int]:
    """
    Scan audio input devices and return the index of the first virtual
    loopback device found.

    Returns:
        Device index (int) if a loopback is detected, None otherwise.
    """
    try:
        import pyaudio
    except ImportError:
        print("  ⚠️  pyaudio not installed — cannot detect audio devices.")
        return None

    pa = None
    try:
        pa = pyaudio.PyAudio()
        device_count = pa.get_device_count()

        for i in range(device_count):
            try:
                info = pa.get_device_info_by_index(i)
            except Exception:
                continue

            name = info.get("name", "").lower()
            max_input_channels = info.get("maxInputChannels", 0)

            # Must be an input device (has input channels)
            if max_input_channels < 1:
                continue

            for pattern in _LOOPBACK_PATTERNS:
                if pattern in name:
                    print(f"  🔊 Loopback audio device detected: '{info['name']}' (index={i}, channels={max_input_channels})")
                    return i

    except Exception as e:
        print(f"  ⚠️  Error scanning audio devices: {e}")
    finally:
        if pa:
            try:
                pa.terminate()
            except Exception:
                pass

    return None


def get_loopback_status() -> Tuple[bool, str, Optional[int]]:
    """
    Get full loopback status for display in the HUD.

    Returns:
        Tuple of (is_available, status_text, device_index)
    """
    idx = get_loopback_device_index()
    if idx is not None:
        return True, "🔊 System Audio (BlackHole)", idx
    else:
        return False, "🎤 Physical Mic Only", None


def get_device_name(device_index: int) -> str:
    """Get the human-readable name of an audio device by index."""
    try:
        import pyaudio
        pa = pyaudio.PyAudio()
        info = pa.get_device_info_by_index(device_index)
        name = info.get("name", f"Device {device_index}")
        pa.terminate()
        return name
    except Exception:
        return f"Device {device_index}"


def list_input_devices() -> str:
    """List all available audio input devices. Useful for debugging."""
    try:
        import pyaudio
    except ImportError:
        return "pyaudio not installed."

    pa = None
    lines = ["Available Audio Input Devices:"]
    try:
        pa = pyaudio.PyAudio()
        for i in range(pa.get_device_count()):
            try:
                info = pa.get_device_info_by_index(i)
                if info.get("maxInputChannels", 0) > 0:
                    name = info.get("name", "Unknown")
                    channels = info.get("maxInputChannels", 0)
                    rate = int(info.get("defaultSampleRate", 0))
                    is_loopback = any(p in name.lower() for p in _LOOPBACK_PATTERNS)
                    marker = " ← LOOPBACK" if is_loopback else ""
                    lines.append(f"  [{i}] {name} ({channels}ch, {rate}Hz){marker}")
            except Exception:
                continue
    except Exception as e:
        lines.append(f"  Error: {e}")
    finally:
        if pa:
            try:
                pa.terminate()
            except Exception:
                pass

    return "\n".join(lines) if len(lines) > 1 else "No audio input devices found."
