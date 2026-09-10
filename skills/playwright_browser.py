# Jarvis AI — Playwright Browser Engine
# Deep browser interaction via Chrome DevTools Protocol (CDP).
# Connects to the user's REAL Chrome/Brave browser to interact with web pages.

import asyncio
import subprocess
import time
import json

from config import Config

# ── Global browser state ──────────────────────────────────────
_browser = None
_page = None
_context = None
_playwright = None
CDP_PORT = 9222


def _ensure_event_loop():
    """Ensure there's an event loop available for asyncio operations."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


def _run_async(coro):
    """Run an async coroutine from synchronous code."""
    loop = _ensure_event_loop()
    if loop.is_running():
        # We're already in an async context, create a new thread
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(asyncio.run, coro)
            return future.result(timeout=30)
    else:
        return loop.run_until_complete(coro)


async def _ensure_browser_connected(allow_launch: bool = False):
    """Connect to the user's running Chrome/Brave via CDP if not already connected."""
    global _browser, _page, _context, _playwright

    if _page and not _page.is_closed():
        return _page

    try:
        from playwright.async_api import async_playwright

        if not _playwright:
            _playwright = await async_playwright().start()

        # Try connecting to existing browser via CDP
        try:
            _browser = await _playwright.chromium.connect_over_cdp(
                f"http://localhost:{CDP_PORT}",
                timeout=2000
            )
        except Exception:
            if not allow_launch:
                return None
            # Only launch a clean Chromium instance if explicitly allowed
            try:
                _browser = await _playwright.chromium.launch(headless=False)
            except Exception:
                return None

        if not _browser:
            return None

        # Get the first context and page
        contexts = _browser.contexts
        if contexts:
            _context = contexts[0]
            pages = _context.pages
            if pages:
                _page = pages[0]
            else:
                _page = await _context.new_page()
        else:
            _context = await _browser.new_context()
            _page = await _context.new_page()

        return _page

    except Exception as e:
        if not allow_launch:
            return None
        raise Exception(f"Could not connect to browser: {e}")


def _launch_browser_with_cdp():
    """Relaunch the user's browser with CDP enabled."""
    browser_name = Config.DEFAULT_BROWSER.lower()

    if browser_name == "brave":
        app_path = "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"
    elif browser_name == "chrome":
        app_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    else:
        app_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    try:
        subprocess.Popen(
            [app_path, f"--remote-debugging-port={CDP_PORT}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except FileNotFoundError:
        # Fallback: try using 'open' command
        if browser_name == "brave":
            subprocess.Popen(["open", "-a", "Brave Browser", "--args", f"--remote-debugging-port={CDP_PORT}"])
        else:
            subprocess.Popen(["open", "-a", "Google Chrome", "--args", f"--remote-debugging-port={CDP_PORT}"])


def _get_active_page():
    """Get the currently active (visible) browser tab."""
    global _page, _context

    async def _get():
        global _page, _context
        page = await _ensure_browser_connected()

        # Try to find the currently visible/focused page
        if _context:
            for p in _context.pages:
                if not p.is_closed():
                    # Use the most recently active page
                    _page = p
                    return p
        return page

    return _run_async(_get())


# ── Public API Functions ──────────────────────────────────────

def browser_navigate(url: str) -> str:
    """Navigate the active browser tab to a URL."""
    async def _nav():
        page = await _ensure_browser_connected()
        await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        return f"Navigated to {url}."

    try:
        return _run_async(_nav())
    except Exception as e:
        return f"Failed to navigate: {e}"


def browser_click(selector: str) -> str:
    """Click an element on the page by CSS selector or text content."""
    async def _click():
        page = await _ensure_browser_connected()

        # Try CSS selector first
        try:
            await page.click(selector, timeout=5000)
            return f"Clicked element: {selector}"
        except Exception:
            pass

        # Try clicking by text content
        try:
            await page.click(f"text={selector}", timeout=5000)
            return f"Clicked element with text: {selector}"
        except Exception:
            pass

        # Try clicking by aria-label
        try:
            await page.click(f"[aria-label='{selector}']", timeout=5000)
            return f"Clicked element with label: {selector}"
        except Exception as e:
            return f"Could not find element to click: {selector}. Error: {e}"

    try:
        return _run_async(_click())
    except Exception as e:
        return f"Click failed: {e}"


def browser_type(selector: str, text: str) -> str:
    """Type text into an input field on the page."""
    async def _type():
        page = await _ensure_browser_connected()

        # Try CSS selector
        try:
            await page.fill(selector, text, timeout=5000)
            return f"Typed '{text}' into {selector}."
        except Exception:
            pass

        # Try by placeholder
        try:
            await page.fill(f"[placeholder*='{selector}']", text, timeout=5000)
            return f"Typed '{text}' into field with placeholder '{selector}'."
        except Exception:
            pass

        # Try by name/id
        try:
            await page.fill(f"input[name='{selector}'], input[id='{selector}'], textarea[name='{selector}']", text, timeout=5000)
            return f"Typed '{text}' into {selector}."
        except Exception as e:
            return f"Could not find input field '{selector}': {e}"

    try:
        return _run_async(_type())
    except Exception as e:
        return f"Type failed: {e}"


def browser_press_key(key: str) -> str:
    """Press a keyboard key on the active page (e.g., 'Enter', 'Tab', 'Escape', 'ArrowRight')."""
    async def _press():
        page = await _ensure_browser_connected()
        await page.keyboard.press(key)
        return f"Pressed key: {key}"

    try:
        return _run_async(_press())
    except Exception as e:
        return f"Key press failed: {e}"


def browser_read_page() -> str:
    """Read the visible text content from the current page."""
    async def _read():
        page = await _ensure_browser_connected()
        title = await page.title()
        url = page.url

        # Get main text content (limited to avoid huge outputs)
        text = await page.evaluate("""
            () => {
                const body = document.body;
                if (!body) return '';
                // Get visible text, skip scripts/styles
                const walker = document.createTreeWalker(
                    body, NodeFilter.SHOW_TEXT, {
                        acceptNode: (node) => {
                            const parent = node.parentElement;
                            if (!parent) return NodeFilter.FILTER_REJECT;
                            const tag = parent.tagName.toLowerCase();
                            if (['script', 'style', 'noscript'].includes(tag)) return NodeFilter.FILTER_REJECT;
                            if (parent.offsetParent === null && tag !== 'body') return NodeFilter.FILTER_REJECT;
                            return NodeFilter.FILTER_ACCEPT;
                        }
                    }
                );
                let text = '';
                let node;
                while (node = walker.nextNode()) {
                    const t = node.textContent.trim();
                    if (t) text += t + '\\n';
                }
                return text.substring(0, 3000);
            }
        """)

        return f"**Page:** {title}\n**URL:** {url}\n\n{text}"

    try:
        return _run_async(_read())
    except Exception as e:
        return f"Failed to read page: {e}"


def browser_run_js(script: str) -> str:
    """Execute JavaScript on the active browser page and return the result."""
    async def _js():
        page = await _ensure_browser_connected()
        result = await page.evaluate(script)
        return f"JS Result: {json.dumps(result) if result is not None else 'undefined'}"

    try:
        return _run_async(_js())
    except Exception as e:
        return f"JS execution failed: {e}"


def browser_screenshot() -> str:
    """Take a screenshot of the active browser tab."""
    async def _screenshot():
        page = await _ensure_browser_connected()
        import os
        screenshot_path = os.path.join(Config.HISTORY_DIR, "browser_screenshot.png")
        os.makedirs(Config.HISTORY_DIR, exist_ok=True)
        await page.screenshot(path=screenshot_path, full_page=False)
        return f"Screenshot saved to {screenshot_path}"

    try:
        return _run_async(_screenshot())
    except Exception as e:
        return f"Screenshot failed: {e}"


def browser_get_current_url() -> str:
    """Get the URL of the active browser tab."""
    async def _url():
        page = await _ensure_browser_connected()
        return f"Current URL: {page.url}"

    try:
        return _run_async(_url())
    except Exception as e:
        return f"Failed to get URL: {e}"


def browser_switch_tab(index: int = 0) -> str:
    """Switch to a different browser tab by index (0-based)."""
    async def _switch():
        global _page
        await _ensure_browser_connected()
        if _context:
            pages = _context.pages
            if 0 <= index < len(pages):
                _page = pages[index]
                await _page.bring_to_front()
                title = await _page.title()
                return f"Switched to tab {index}: {title}"
            else:
                return f"Tab index {index} out of range. {len(pages)} tabs open."
        return "No browser context available."

    try:
        return _run_async(_switch())
    except Exception as e:
        return f"Tab switch failed: {e}"


# ── Tool Definitions ──────────────────────────────────────────
PLAYWRIGHT_TOOLS = [
    {
        "name": "browser_navigate",
        "description": "Navigate the active browser tab to a specific URL. Use this to go to a webpage.",
        "function": browser_navigate,
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to navigate to",
                }
            },
            "required": ["url"],
        },
    },
    {
        "name": "browser_click",
        "description": "Click an element on the current web page. Accepts CSS selectors, text content, or aria-labels. Use for clicking buttons, links, menu items, etc.",
        "function": browser_click,
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector, text content, or aria-label of the element to click (e.g., '#submit-btn', 'Sign In', 'Search')",
                }
            },
            "required": ["selector"],
        },
    },
    {
        "name": "browser_type",
        "description": "Type text into an input field on the current web page. Use for filling search boxes, forms, etc.",
        "function": browser_type,
        "parameters": {
            "type": "object",
            "properties": {
                "selector": {
                    "type": "string",
                    "description": "CSS selector, placeholder text, or name/id of the input field",
                },
                "text": {
                    "type": "string",
                    "description": "The text to type into the field",
                }
            },
            "required": ["selector", "text"],
        },
    },
    {
        "name": "browser_press_key",
        "description": "Press a keyboard key in the browser (e.g., 'Enter', 'Escape', 'ArrowRight', 'Space', 'Tab').",
        "function": browser_press_key,
        "parameters": {
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The key to press (e.g., 'Enter', 'Escape', 'ArrowRight', 'Space', 'k', 'f')",
                }
            },
            "required": ["key"],
        },
    },
    {
        "name": "browser_read_page",
        "description": "Read the visible text content from the current browser page. Use to understand what's on screen.",
        "function": browser_read_page,
        "parameters": {},
    },
    {
        "name": "browser_run_js",
        "description": "Execute JavaScript code on the active browser page. Use for advanced interactions not covered by other tools.",
        "function": browser_run_js,
        "parameters": {
            "type": "object",
            "properties": {
                "script": {
                    "type": "string",
                    "description": "The JavaScript code to execute",
                }
            },
            "required": ["script"],
        },
    },
    {
        "name": "browser_screenshot",
        "description": "Take a screenshot of the current browser tab.",
        "function": browser_screenshot,
        "parameters": {},
    },
    {
        "name": "browser_get_current_url",
        "description": "Get the URL of the currently active browser tab.",
        "function": browser_get_current_url,
        "parameters": {},
    },
    {
        "name": "browser_switch_tab",
        "description": "Switch to a different browser tab by index (0 = first tab, 1 = second tab, etc.).",
        "function": browser_switch_tab,
        "parameters": {
            "type": "object",
            "properties": {
                "index": {
                    "type": "integer",
                    "description": "The tab index to switch to (0-based)",
                }
            },
            "required": ["index"],
        },
    },
]
