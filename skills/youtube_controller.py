# Jarvis AI — YouTube Controller
# Controls YouTube playback in the user's browser tab via Playwright CDP.
# Search, play, pause, forward, rewind, skip ads, fullscreen, volume.

import asyncio
import threading
import time

from skills.playwright_browser import (
    _ensure_browser_connected, _run_async, _get_active_page
)


def _find_youtube_page():
    """Find the YouTube tab in the browser."""
    async def _find():
        page = await _ensure_browser_connected()
        from skills.playwright_browser import _context
        if _context:
            for p in _context.pages:
                if not p.is_closed() and "youtube.com" in p.url:
                    return p
        # If no YouTube tab found, check if current page is YouTube
        if "youtube.com" in page.url:
            return page
        return None

    return _run_async(_find())


def youtube_search_in_tab(query: str) -> str:
    """Search for a video on YouTube within the active YouTube tab."""
    async def _search():
        page = await _ensure_browser_connected()
        from skills.playwright_browser import _context, _page
        
        # Find or navigate to YouTube
        yt_page = None
        if _context:
            for p in _context.pages:
                if not p.is_closed() and "youtube.com" in p.url:
                    yt_page = p
                    break
        
        if not yt_page:
            # Navigate current page to YouTube
            yt_page = page
            await yt_page.goto("https://www.youtube.com", wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(2)
        
        await yt_page.bring_to_front()
        
        # Click the search box and type
        try:
            search_input = await yt_page.query_selector("input#search, input[name='search_query']")
            if search_input:
                await search_input.click()
                await search_input.fill("")
                await search_input.fill(query)
                await asyncio.sleep(0.3)
                await yt_page.keyboard.press("Enter")
                await asyncio.sleep(2)
                return f"Searching YouTube for '{query}'."
            else:
                # Fallback: use URL
                import urllib.parse
                encoded = urllib.parse.quote_plus(query)
                await yt_page.goto(f"https://www.youtube.com/results?search_query={encoded}", 
                                   wait_until="domcontentloaded", timeout=15000)
                return f"Searching YouTube for '{query}'."
        except Exception as e:
            return f"Search failed: {e}"

    try:
        return _run_async(_search())
    except Exception as e:
        return f"YouTube search failed: {e}"


def youtube_play_first_result() -> str:
    """Click the first video result on a YouTube search results page."""
    async def _play():
        page = await _ensure_browser_connected()
        from skills.playwright_browser import _context
        
        yt_page = None
        if _context:
            for p in _context.pages:
                if not p.is_closed() and "youtube.com" in p.url:
                    yt_page = p
                    break
        
        if not yt_page:
            return "No YouTube tab found. Search for something first."
        
        await yt_page.bring_to_front()
        
        # Click the first video thumbnail/title
        try:
            # Try clicking a video renderer
            video = await yt_page.query_selector("ytd-video-renderer a#video-title, ytd-rich-item-renderer a#video-title-link")
            if video:
                await video.click()
                await asyncio.sleep(2)
                return "Playing the first video result."
            
            # Try another selector pattern
            video = await yt_page.query_selector("a.ytd-thumbnail[href*='watch']")
            if video:
                await video.click()
                await asyncio.sleep(2)
                return "Playing the first video result."
            
            return "Could not find a video to play on the current page."
        except Exception as e:
            return f"Failed to play video: {e}"

    try:
        return _run_async(_play())
    except Exception as e:
        return f"Play first result failed: {e}"


def youtube_play_pause() -> str:
    """Toggle play/pause on the current YouTube video."""
    async def _toggle():
        yt_page = _find_youtube_page_sync()
        if not yt_page:
            return "No YouTube video tab found."
        
        # Press 'k' which is YouTube's play/pause shortcut
        await yt_page.keyboard.press("k")
        
        # Check if video is paused or playing
        is_paused = await yt_page.evaluate("""
            () => {
                const video = document.querySelector('video');
                return video ? video.paused : null;
            }
        """)
        
        if is_paused is True:
            return "Video paused."
        elif is_paused is False:
            return "Video playing."
        else:
            return "Toggled play/pause."

    def _find_youtube_page_sync():
        return _find_youtube_page()

    try:
        return _run_async(_toggle())
    except Exception as e:
        return f"Play/pause failed: {e}"


def youtube_forward(seconds: int = 10) -> str:
    """Forward the YouTube video by a number of seconds."""
    async def _forward():
        yt_page = _find_youtube_page()
        if not yt_page:
            return "No YouTube video tab found."
        
        # Use JavaScript to seek forward
        result = await yt_page.evaluate(f"""
            () => {{
                const video = document.querySelector('video');
                if (video) {{
                    video.currentTime += {seconds};
                    return Math.floor(video.currentTime);
                }}
                return null;
            }}
        """)
        
        if result is not None:
            return f"Forwarded {seconds} seconds. Now at {result}s."
        
        # Fallback: press right arrow (5 second increments)
        presses = max(1, seconds // 5)
        for _ in range(presses):
            await yt_page.keyboard.press("ArrowRight")
            await asyncio.sleep(0.1)
        return f"Forwarded approximately {presses * 5} seconds."

    try:
        return _run_async(_forward())
    except Exception as e:
        return f"Forward failed: {e}"


def youtube_rewind(seconds: int = 10) -> str:
    """Rewind the YouTube video by a number of seconds."""
    async def _rewind():
        yt_page = _find_youtube_page()
        if not yt_page:
            return "No YouTube video tab found."
        
        result = await yt_page.evaluate(f"""
            () => {{
                const video = document.querySelector('video');
                if (video) {{
                    video.currentTime = Math.max(0, video.currentTime - {seconds});
                    return Math.floor(video.currentTime);
                }}
                return null;
            }}
        """)
        
        if result is not None:
            return f"Rewound {seconds} seconds. Now at {result}s."
        
        presses = max(1, seconds // 5)
        for _ in range(presses):
            await yt_page.keyboard.press("ArrowLeft")
            await asyncio.sleep(0.1)
        return f"Rewound approximately {presses * 5} seconds."

    try:
        return _run_async(_rewind())
    except Exception as e:
        return f"Rewind failed: {e}"


def youtube_skip_ad() -> str:
    """Skip the ad on the current YouTube video if a skip button is available."""
    async def _skip():
        yt_page = _find_youtube_page()
        if not yt_page:
            return "No YouTube video tab found."
        
        # Try multiple skip ad button selectors
        skip_selectors = [
            ".ytp-skip-ad-button",
            ".ytp-ad-skip-button",
            ".ytp-ad-skip-button-text",
            "button.ytp-ad-skip-button-modern",
            ".ytp-ad-skip-button-container button",
            "[class*='skip-ad']",
            "button[id*='skip']",
        ]
        
        for selector in skip_selectors:
            try:
                btn = await yt_page.query_selector(selector)
                if btn and await btn.is_visible():
                    await btn.click()
                    return "Ad skipped!"
            except Exception:
                continue
        
        # Check if there's an ad playing but no skip button yet
        ad_playing = await yt_page.evaluate("""
            () => {
                const adOverlay = document.querySelector('.ytp-ad-player-overlay, .ad-showing, .ytp-ad-module');
                return !!adOverlay;
            }
        """)
        
        if ad_playing:
            return "Ad is playing but no skip button is available yet. Please wait."
        
        return "No ad detected on the current video."

    try:
        return _run_async(_skip())
    except Exception as e:
        return f"Ad skip failed: {e}"


def youtube_fullscreen() -> str:
    """Toggle fullscreen on the YouTube video."""
    async def _fs():
        yt_page = _find_youtube_page()
        if not yt_page:
            return "No YouTube video tab found."
        await yt_page.keyboard.press("f")
        return "Toggled fullscreen."

    try:
        return _run_async(_fs())
    except Exception as e:
        return f"Fullscreen toggle failed: {e}"


def youtube_set_volume(level: int) -> str:
    """Set the YouTube video volume (0-100)."""
    async def _vol():
        yt_page = _find_youtube_page()
        if not yt_page:
            return "No YouTube video tab found."
        
        level_clamped = max(0, min(100, level))
        await yt_page.evaluate(f"""
            () => {{
                const video = document.querySelector('video');
                if (video) video.volume = {level_clamped / 100};
            }}
        """)
        return f"YouTube volume set to {level_clamped}%."

    try:
        return _run_async(_vol())
    except Exception as e:
        return f"Volume set failed: {e}"


def youtube_next_video() -> str:
    """Skip to the next video in the YouTube queue."""
    async def _next():
        yt_page = _find_youtube_page()
        if not yt_page:
            return "No YouTube video tab found."
        await yt_page.keyboard.press("Shift+N")
        await asyncio.sleep(1)
        return "Skipped to next video."

    try:
        return _run_async(_next())
    except Exception as e:
        return f"Next video failed: {e}"


# ── Background Ad Skipper Daemon ──────────────────────────────
_ad_skipper_running = False
_ad_skipper_thread = None


def start_auto_ad_skipper() -> str:
    """Start a background daemon that automatically skips YouTube ads."""
    global _ad_skipper_running, _ad_skipper_thread
    
    if _ad_skipper_running:
        return "Auto ad-skipper is already running."
    
    _ad_skipper_running = True
    
    def _skipper_loop():
        global _ad_skipper_running
        while _ad_skipper_running:
            try:
                youtube_skip_ad()
            except Exception:
                pass
            time.sleep(3)
    
    _ad_skipper_thread = threading.Thread(target=_skipper_loop, daemon=True)
    _ad_skipper_thread.start()
    return "Auto ad-skipper started. I'll skip ads automatically."


def stop_auto_ad_skipper() -> str:
    """Stop the background ad skipper daemon."""
    global _ad_skipper_running
    _ad_skipper_running = False
    return "Auto ad-skipper stopped."


# ── Tool Definitions ──────────────────────────────────────────
YOUTUBE_TOOLS = [
    {
        "name": "youtube_search_in_tab",
        "description": "Search for a video on YouTube within the currently open YouTube tab. If no YouTube tab is open, it opens one. Use this instead of youtube_search when the user wants to search within the same tab.",
        "function": youtube_search_in_tab,
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "What to search for on YouTube",
                }
            },
            "required": ["query"],
        },
    },
    {
        "name": "youtube_play_first_result",
        "description": "Click and play the first video from YouTube search results. Use after youtube_search_in_tab.",
        "function": youtube_play_first_result,
        "parameters": {},
    },
    {
        "name": "youtube_play_pause",
        "description": "Toggle play/pause on the currently playing YouTube video.",
        "function": youtube_play_pause,
        "parameters": {},
    },
    {
        "name": "youtube_forward",
        "description": "Fast-forward the YouTube video by a number of seconds.",
        "function": youtube_forward,
        "parameters": {
            "type": "object",
            "properties": {
                "seconds": {
                    "type": "integer",
                    "description": "Number of seconds to skip forward (default: 10)",
                }
            },
            "required": ["seconds"],
        },
    },
    {
        "name": "youtube_rewind",
        "description": "Rewind the YouTube video by a number of seconds.",
        "function": youtube_rewind,
        "parameters": {
            "type": "object",
            "properties": {
                "seconds": {
                    "type": "integer",
                    "description": "Number of seconds to rewind (default: 10)",
                }
            },
            "required": ["seconds"],
        },
    },
    {
        "name": "youtube_skip_ad",
        "description": "Skip the ad currently playing on a YouTube video. Click the 'Skip Ad' button if available.",
        "function": youtube_skip_ad,
        "parameters": {},
    },
    {
        "name": "youtube_fullscreen",
        "description": "Toggle fullscreen mode on the YouTube video player.",
        "function": youtube_fullscreen,
        "parameters": {},
    },
    {
        "name": "youtube_set_volume",
        "description": "Set the volume of the YouTube video player (0 to 100).",
        "function": youtube_set_volume,
        "parameters": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "integer",
                    "description": "Volume level from 0 (mute) to 100 (max)",
                }
            },
            "required": ["level"],
        },
    },
    {
        "name": "youtube_next_video",
        "description": "Skip to the next video in the YouTube queue or playlist.",
        "function": youtube_next_video,
        "parameters": {},
    },
    {
        "name": "start_auto_ad_skipper",
        "description": "Start a background daemon that automatically detects and skips YouTube ads every few seconds. Use when the user says 'skip all ads automatically' or 'auto skip ads'.",
        "function": start_auto_ad_skipper,
        "parameters": {},
    },
    {
        "name": "stop_auto_ad_skipper",
        "description": "Stop the background auto ad-skipper daemon.",
        "function": stop_auto_ad_skipper,
        "parameters": {},
    },
]
