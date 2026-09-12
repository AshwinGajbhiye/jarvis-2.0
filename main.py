#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════╗
# ║           J.A.R.V.I.S. — Just A Rather Very Intelligent System  ║
# ║              A Personal AI Assistant for macOS                   ║
# ║                  Inspired by Tony Stark                          ║
# ╚══════════════════════════════════════════════════════════════════╝

import sys
import time
import signal
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from brain import Brain
from voice.tts import speak, stop_speaking
from voice.stt import listen, is_mic_available
from utils.helpers import get_greeting

# ── Try to import rich for beautiful terminal output ─────────
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich.spinner import Spinner
    from rich.table import Table
    from rich.markdown import Markdown

    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False
    console = None


# ── Terminal Colors (fallback if rich is not available) ───────
class Colors:
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    WHITE = "\033[97m"
    DIM = "\033[2m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


# ── ASCII Art ─────────────────────────────────────────────────
JARVIS_LOGO = f"""{Colors.CYAN}
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
{Colors.DIM}  Just A Rather Very Intelligent System{Colors.RESET}
"""


def print_styled(text: str, color: str = Colors.WHITE):
    """Print with color."""
    print(f"{color}{text}{Colors.RESET}")


def boot_sequence():
    """Display the Jarvis startup sequence."""
    if sys.stdout.isatty():
        os.system("clear")
    print(JARVIS_LOGO)
    time.sleep(0.3)

    boot_steps = [
        ("Initializing neural pathways", "🧠"),
        ("Loading voice interface", "🎤"),
        ("Connecting to knowledge base", "🌐"),
        ("Activating skill modules", "⚡"),
        ("Calibrating personality matrix", "🤖"),
    ]

    for step, icon in boot_steps:
        if HAS_RICH:
            console.print(f"  {icon}  {step}...", style="dim cyan")
        else:
            print_styled(f"  {icon}  {step}...", Colors.CYAN)
        time.sleep(0.25)

    print()


def print_status_panel(mic_available: bool):
    """Print the system status panel."""
    if HAS_RICH:
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="cyan")
        table.add_column(style="white")

        table.add_row("🤖 Model", Config.GEMINI_MODEL)
        table.add_row("🗣️  Voice", Config.JARVIS_VOICE)
        table.add_row("🎤 Microphone", "✅ Ready" if mic_available else "❌ Not available (keyboard mode)")
        table.add_row("🌐 Browser", Config.DEFAULT_BROWSER.title())
        table.add_row("📧 Gmail", "✅ Configured" if os.path.exists(Config.GMAIL_CREDENTIALS_PATH) else "⚠️  Not configured")
        table.add_row("🧠 AI Key", "✅ Set" if Config.GEMINI_API_KEY else "❌ Not set")

        console.print(Panel(table, title="[bold cyan]System Status[/]", border_style="cyan"))
    else:
        print_styled("  ─── System Status ───", Colors.CYAN)
        Config.print_status()
        print_styled(f"  🎤 Mic:      {'✅ Ready' if mic_available else '❌ Keyboard mode'}", Colors.WHITE)
    print()


def print_help():
    """Print available commands."""
    if HAS_RICH:
        help_text = """
[bold cyan]Voice/Text Commands:[/]
  • Ask anything naturally — Jarvis understands context
  • "Open VS Code" / "Open Chrome" / "Open Brave"
  • "What time is it?" / "What's the date?"
  • "Read my emails" / "Any new emails?"
  • "Search Google for Python tutorials"
  • "Find me Python developer jobs on LinkedIn"
  • "What's on my calendar today?"
  • "Set volume to 50"
  • "What's the weather?"

[bold cyan]System Commands:[/]
  • Type [bold]'voice'[/] to toggle voice/keyboard mode
  • Type [bold]'reset'[/] to clear conversation
  • Type [bold]'quit'[/] or [bold]'exit'[/] to shut down
  • Type [bold]'help'[/] to see this message
"""
        console.print(Panel(help_text, title="[bold cyan]Help[/]", border_style="dim"))
    else:
        print_styled("\n  Commands: voice (toggle mode), reset (clear chat), quit (exit), help", Colors.DIM)


def main():
    """Launch the J.A.R.V.I.S. Graphical Interface."""
    import argparse
    parser = argparse.ArgumentParser(description="J.A.R.V.I.S. AI Assistant")
    parser.add_argument("--minimized", "--daemon", action="store_true", help="Run silently in the macOS menu bar without showing the main window")
    args, _ = parser.parse_known_args()
    
    # ── Try to import GUI components ──────────────────────────
    try:
        from gui.app import run_gui
        
        # Print a simple boot message to terminal
        if not args.minimized:
            if sys.stdout.isatty():
                os.system("clear")
            print(JARVIS_LOGO)
            print_styled("  Launching J.A.R.V.I.S. GUI...", Colors.GREEN)
            print_styled("  (Leave this terminal running. The app will open in a new window.)\n", Colors.DIM)
        else:
            print_styled("  Launching J.A.R.V.I.S. in Menu Bar Daemon mode...", Colors.CYAN)
        
        # Start GUI (blocks until window is closed)
        run_gui(minimized=args.minimized)
        
    except ImportError as e:
        print_styled(f"\n  ⚠️  Failed to launch GUI: {e}", Colors.RED)
        print_styled("  Starting J.A.R.V.I.S. in Headless / Mobile Server mode...", Colors.CYAN)
        try:
            from brain import Brain
            from server.api import start_api_server
            brain = Brain()
            start_api_server(brain)
            print_styled("  Headless mobile server active. Press Ctrl+C to terminate.\n", Colors.GREEN)
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print_styled("\n  Shutting down J.A.R.V.I.S...", Colors.DIM)
            sys.exit(0)
        except Exception as err:
            print_styled(f"  Fatal error: {err}", Colors.RED)
            sys.exit(1)

if __name__ == "__main__":
    main()
