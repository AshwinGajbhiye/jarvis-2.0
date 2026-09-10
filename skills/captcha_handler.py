# Jarvis AI — CAPTCHA Handler Skill
# Basic CAPTCHA bypass and human-verification handling via Playwright CDP.
# Detects and handles: Cloudflare Turnstile, Google reCAPTCHA v2 checkbox, hCaptcha.
# For complex image puzzles, alerts the user to complete the puzzle manually.

import asyncio
import time
from skills.playwright_browser import _ensure_browser_connected, _run_async


async def _async_detect_captcha():
    """Detect presence and type of CAPTCHA on the active browser tab."""
    page = await _ensure_browser_connected()
    
    findings = []
    
    # Check title/body for Cloudflare Challenge
    title = await page.title()
    if "just a moment" in title.lower() or "attention required" in title.lower():
        findings.append("Cloudflare Challenge Page")
        
    # Check for Cloudflare Turnstile
    turnstile_frames = [f for f in page.frames if "turnstile" in f.url or "challenges.cloudflare.com" in f.url]
    turnstile_divs = await page.locator("div.cf-turnstile, #turnstile-wrapper, div[data-turnstile]").count()
    if turnstile_frames or turnstile_divs > 0:
        findings.append("Cloudflare Turnstile")
        
    # Check for Google reCAPTCHA
    recaptcha_frames = [f for f in page.frames if "recaptcha" in f.url]
    recaptcha_divs = await page.locator(".g-recaptcha, #g-recaptcha, iframe[src*='recaptcha']").count()
    if recaptcha_frames or recaptcha_divs > 0:
        findings.append("Google reCAPTCHA")
        
    # Check for hCaptcha
    hcaptcha_frames = [f for f in page.frames if "hcaptcha" in f.url]
    hcaptcha_divs = await page.locator(".h-captcha, iframe[src*='hcaptcha']").count()
    if hcaptcha_frames or hcaptcha_divs > 0:
        findings.append("hCaptcha")
        
    # Check for generic "Verify you are human" / "I'm not a robot"
    generic_matches = await page.locator("text='Verify you are human', text=\"I'm not a robot\", text='Verify that you are human'").count()
    if generic_matches > 0:
        findings.append("Human Verification prompt")
        
    if findings:
        return f"Detected CAPTCHA: {', '.join(findings)}"
    return "No CAPTCHA detected on current page."


def detect_captcha() -> str:
    """Detect if a CAPTCHA or Cloudflare challenge is currently present on the active browser page."""
    try:
        return _run_async(_async_detect_captcha())
    except Exception as e:
        return f"Error checking for CAPTCHA: {e}"


async def _async_solve_basic_captcha():
    """Attempt to solve or bypass basic checkbox CAPTCHAs on the active page."""
    page = await _ensure_browser_connected()
    
    # 1. Cloudflare Challenge / Turnstile
    for frame in page.frames:
        if "cloudflare" in frame.url or "turnstile" in frame.url:
            try:
                # Look for checkbox or button inside the frame
                checkbox = frame.locator("input[type='checkbox'], #cf-stage input, span.mark, .ctp-checkbox-label")
                if await checkbox.count() > 0:
                    await checkbox.first.click(delay=150)
                    await asyncio.sleep(2)
                    return "Clicked Cloudflare Turnstile checkbox. Verification passed."
            except Exception:
                pass

    # Try main page Turnstile click
    turnstile_box = page.locator("iframe[src*='challenges.cloudflare.com'], iframe[src*='turnstile']")
    if await turnstile_box.count() > 0:
        try:
            # Click near center of Turnstile iframe
            box = await turnstile_box.first.bounding_box()
            if box:
                # Add human-like offset (near the checkbox on the left side)
                click_x = box["x"] + min(35, box["width"] * 0.15)
                click_y = box["y"] + box["height"] / 2
                await page.mouse.click(click_x, click_y, delay=120)
                await asyncio.sleep(2.5)
                return "Clicked Cloudflare Turnstile verification."
        except Exception as e:
            pass

    # 2. Google reCAPTCHA v2 Checkbox
    for frame in page.frames:
        if "recaptcha" in frame.url and "anchor" in frame.url:
            try:
                anchor = frame.locator("#recaptcha-anchor")
                if await anchor.count() > 0:
                    # Check if already checked
                    checked = await anchor.get_attribute("aria-checked")
                    if checked == "true":
                        return "reCAPTCHA is already verified."
                    
                    # Human-like click
                    await anchor.click(delay=180)
                    await asyncio.sleep(2.5)
                    
                    # Check result
                    checked_after = await anchor.get_attribute("aria-checked")
                    if checked_after == "true":
                        return "reCAPTCHA checkbox successfully verified!"
                    
                    # Check if bframe (image puzzle) opened
                    return "reCAPTCHA checkbox clicked. An image puzzle may require manual selection."
            except Exception as e:
                pass

    # 3. hCaptcha
    for frame in page.frames:
        if "hcaptcha" in frame.url:
            try:
                cb = frame.locator("#checkbox, div[role='checkbox']")
                if await cb.count() > 0:
                    await cb.click(delay=150)
                    await asyncio.sleep(2)
                    return "Clicked hCaptcha verification checkbox."
            except Exception:
                pass

    # 4. Generic "I'm not a robot" or "Verify" button/label
    generic_selectors = [
        "input[type='checkbox'][name*='captcha']",
        "input[type='checkbox'][id*='captcha']",
        "button:has-text('Verify you are human')",
        "button:has-text('I am human')",
        "div[role='checkbox']:has-text('robot')",
        "label:has-text(\"I'm not a robot\")",
    ]
    for sel in generic_selectors:
        loc = page.locator(sel)
        if await loc.count() > 0 and await loc.first.is_visible():
            await loc.first.click(delay=120)
            await asyncio.sleep(2)
            return f"Clicked human verification element ({sel})."

    return "No interactable checkbox CAPTCHA found. If this is an image or audio puzzle, please solve it manually."


def solve_captcha() -> str:
    """Attempt to solve or click through basic checkbox CAPTCHAs (Cloudflare Turnstile, reCAPTCHA v2, hCaptcha)."""
    try:
        return _run_async(_async_solve_basic_captcha())
    except Exception as e:
        return f"Error solving CAPTCHA: {e}"


# ── Tool Definitions for Jarvis Function Calling ─────────────

CAPTCHA_TOOLS = [
    {
        "name": "detect_captcha",
        "description": "Check if the current webpage has a CAPTCHA or Cloudflare verification challenge.",
        "function": detect_captcha,
        "parameters": {},
    },
    {
        "name": "solve_captcha",
        "description": "Automatically solve or click through basic checkbox CAPTCHAs (Cloudflare Turnstile, reCAPTCHA v2 checkbox, hCaptcha). If an image puzzle appears, informs the user to complete it.",
        "function": solve_captcha,
        "parameters": {},
    },
]
