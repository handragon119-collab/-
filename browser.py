# JARVIS — Built from CLAUDE.md by Taoufik · https://www.youtube.com/@TaoufikAI
"""
browser.py — Playwright-powered web browsing for JARVIS.

Async helpers to search the web, visit a page, extract readable text, and
grab a screenshot. A single headless Chromium instance is launched lazily and
reused across calls.
"""

from __future__ import annotations

import asyncio
import urllib.parse
from typing import Any

try:
    from playwright.async_api import async_playwright, Browser, Playwright
    _HAVE_PLAYWRIGHT = True
except Exception:  # pragma: no cover - optional dep / not installed
    _HAVE_PLAYWRIGHT = False


class WebBrowser:
    def __init__(self) -> None:
        self._pw: "Playwright | None" = None
        self._browser: "Browser | None" = None
        self._lock = asyncio.Lock()

    async def _ensure(self) -> "Browser":
        if not _HAVE_PLAYWRIGHT:
            raise RuntimeError("Playwright is not installed")
        async with self._lock:
            if self._browser is None:
                self._pw = await async_playwright().start()
                self._browser = await self._pw.chromium.launch(headless=True)
        return self._browser

    async def search(self, query: str, limit: int = 5) -> list[dict[str, str]]:
        """DuckDuckGo HTML search → list of {title, url, snippet}."""
        browser = await self._ensure()
        page = await browser.new_page()
        try:
            q = urllib.parse.quote(query)
            await page.goto(f"https://duckduckgo.com/html/?q={q}", timeout=20000)
            results = []
            anchors = await page.query_selector_all("a.result__a")
            snippets = await page.query_selector_all(".result__snippet")
            for i, a in enumerate(anchors[:limit]):
                title = (await a.inner_text()).strip()
                url = await a.get_attribute("href")
                snip = ""
                if i < len(snippets):
                    snip = (await snippets[i].inner_text()).strip()
                results.append({"title": title, "url": url or "", "snippet": snip})
            return results
        finally:
            await page.close()

    async def visit(self, url: str, max_chars: int = 4000) -> dict[str, Any]:
        """Visit a URL and return {title, text} with the body text extracted."""
        browser = await self._ensure()
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=25000, wait_until="domcontentloaded")
            title = await page.title()
            text = await page.evaluate(
                "() => document.body ? document.body.innerText : ''"
            )
            text = " ".join(text.split())
            return {"title": title, "url": url, "text": text[:max_chars]}
        finally:
            await page.close()

    async def screenshot(self, url: str, path: str) -> str:
        browser = await self._ensure()
        page = await browser.new_page()
        try:
            await page.goto(url, timeout=25000, wait_until="networkidle")
            await page.screenshot(path=path, full_page=True)
            return path
        finally:
            await page.close()

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._pw is not None:
            await self._pw.stop()
            self._pw = None


_default: WebBrowser | None = None


def get_browser() -> WebBrowser:
    global _default
    if _default is None:
        _default = WebBrowser()
    return _default
