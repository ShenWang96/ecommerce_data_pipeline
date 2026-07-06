"""
小红书 Collector — Layer 1-3 需求萌芽到内容传播信号。

使用 Playwright stealth 模式 + Cookie 登录。
"""
import re
import logging
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from ..models.signal import TrendSignal, make_signal, SignalType
from ..utils.signal_classifier import classify_signal_type, classify_domain, extract_keywords
from ..utils.cookies import auto_load, check_valid

logger = logging.getLogger("xiaohongshu")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox", "--disable-setuid-sandbox",
    "--disable-dev-shm-usage", "--window-size=1280,800",
    "--disable-default-apps", "--disable-extensions",
    "--disable-popup-blocking", "--password-store=basic",
]

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => false });
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
"""


class XiaohongshuCollector:
    def __init__(
        self,
        cookies: list[dict] | None = None,
        headless: bool = True,
        timeout: int = 30000,
        wait_seconds: int = 5,
        user_data_dir: Optional[Path] = None,
    ):
        if cookies is None:
            cookies = auto_load("xiaohongshu")
        self.cookies = cookies
        self.headless = headless
        self.timeout = timeout
        self.wait_seconds = wait_seconds
        self.user_data_dir = str(user_data_dir or (Path.home() / ".local" / "xhs-stealth-profile"))

    @classmethod
    def check_ready(cls) -> bool:
        info = check_valid("xiaohongshu")
        return info["exists"] and len(info["key_cookies"]) >= 3

    def _new_browser_and_context(self):
        p = sync_playwright().start()
        ctx = p.chromium.launch_persistent_context(
            self.user_data_dir,
            headless=self.headless,
            args=STEALTH_ARGS,
            user_agent=UA,
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            geolocation={"latitude": 31.2304, "longitude": 121.4737},
            permissions=["geolocation"],
        )
        ctx.add_init_script(STEALTH_SCRIPT)
        if self.cookies:
            ctx.add_cookies(self.cookies)
        return p, ctx

    def collect_search(self, keyword: str, limit: int = 30) -> list[TrendSignal]:
        """Layer 1: 搜索笔记"""
        signals = []
        p, ctx = self._new_browser_and_context()
        page = ctx.new_page()
        try:
            url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes"
            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(self.wait_seconds * 1000)
            soup = BeautifulSoup(page.content(), "lxml")
            for item in soup.select("section.note-item")[:limit]:
                title_el = item.select_one(".title span") or item.select_one('[class*=title] span')
                title = title_el.get_text(strip=True)[:120] if title_el else ""
                author_el = item.select_one('[class*=author] .name') or item.select_one('.name')
                author = author_el.get_text(strip=True)[:30] if author_el else ""
                link_el = item.select_one("a[href*='/explore/']") or item.select_one("a[href*='/search_result/']")
                href = link_el.get("href", "") if link_el else ""
                url = f"https://www.xiaohongshu.com{href}" if href.startswith("/") else href
                if not title: continue

                stype = classify_signal_type(title, "", "xiaohongshu", "")
                signals.append(make_signal(
                    source="xiaohongshu",
                    signal_type=stype,
                    title=title,
                    content="",
                    url=url,
                    author=author,
                    domain=classify_domain(title, ""),
                    keywords=extract_keywords(title, keyword),
                    raw_stats={"keyword": keyword},
                ))
        except Exception as e:
            logger.warning(f"search error: {e}")
        finally:
            page.close(); ctx.close(); p.stop()
        return signals

    def collect_explore(self, limit: int = 30) -> list[TrendSignal]:
        """Layer 2-3: 首页推荐流"""
        signals = []
        p, ctx = self._new_browser_and_context()
        page = ctx.new_page()
        try:
            page.goto("https://www.xiaohongshu.com/explore",
                      wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(self.wait_seconds * 1000)
            soup = BeautifulSoup(page.content(), "lxml")
            for item in soup.select("section.note-item")[:limit]:
                title_el = item.select_one(".title span")
                title = title_el.get_text(strip=True)[:120] if title_el else ""
                author_el = item.select_one('.name')
                author = author_el.get_text(strip=True)[:30] if author_el else ""
                link_el = item.select_one("a[href*='/explore/']")
                href = link_el.get("href", "") if link_el else ""
                url = f"https://www.xiaohongshu.com{href}" if href.startswith("/") else href
                if not title: continue

                stype = classify_signal_type(title, "", "xiaohongshu", "")
                signals.append(make_signal(
                    source="xiaohongshu",
                    signal_type=stype,
                    title=title,
                    content="",
                    url=url,
                    author=author,
                    domain=classify_domain(title, ""),
                    keywords=extract_keywords(title, ""),
                    raw_stats={},
                ))
        except Exception as e:
            logger.warning(f"explore error: {e}")
        finally:
            page.close(); ctx.close(); p.stop()
        return signals

    def collect_all(self, keywords: list[str] | None = None) -> list[TrendSignal]:
        signals = self.collect_explore()
        if keywords:
            for kw in keywords:
                signals.extend(self.collect_search(kw))
        return signals
