"""
虎扑 RawCollector — 步行街热帖原始数据落地。

采集: bbs.hupu.com/all-gambia 步行街主版面热帖
方式: Playwright stealth 模式 (同小红书) — 页面完全 JS 渲染
登录: 扫码登录 (需先运行 python3 scripts/qr_login.py hupu)
"""
import logging
import re
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from ..models.raw_record import RawRecord, make_raw
from ..utils.cookies import auto_load, check_valid

logger = logging.getLogger("hupu")

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


class HupuRawCollector:
    def __init__(
        self,
        cookies: list[dict] | None = None,
        headless: bool = True,
        timeout: int = 60000,
        wait_seconds: int = 5,
        save_html: bool = False,
        user_data_dir: Optional[Path] = None,
    ):
        if cookies is None:
            cookies = auto_load("hupu")
        self.cookies = cookies
        self.headless = headless
        self.timeout = timeout
        self.wait_seconds = wait_seconds
        self.save_html = save_html
        self.user_data_dir = str(user_data_dir or (Path.home() / ".local" / "hupu-stealth-profile"))

    @classmethod
    def check_ready(cls) -> bool:
        info = check_valid("hupu")
        return info["exists"] and len(info["key_cookies"]) >= 2

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
        )
        ctx.add_init_script(STEALTH_SCRIPT)
        if self.cookies:
            ctx.add_cookies(self.cookies)
        return p, ctx

    def collect_hot_posts(self, limit: int = 50, scroll_times: int = 3) -> list[RawRecord]:
        """步行街热帖 — 爬取 all-gambia 主版面
        
        页面完全由 JS 渲染，需 Playwright 等待 DOM 就绪后解析。
        滚动多次加载更多帖子。
        """
        records = []
        seen = set()
        p, ctx = self._new_browser_and_context()
        page = ctx.new_page()
        try:
            page.goto("https://bbs.hupu.com/all-gambia",
                      wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(self.wait_seconds * 1000)

            # 滚动加载更多
            for _ in range(scroll_times):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)

            html_content = page.content() if self.save_html else ""
            soup = BeautifulSoup(page.content(), "lxml")

            # 选择器 — 多级回退以应对 Hupu DOM 变动
            post_items = (
                soup.select("li[class*=thread]") or
                soup.select("div[class*=thread-item]") or
                soup.select("div[class*=post-item]") or
                soup.select("li[class*=list-item]")
            )

            if not post_items:
                # 最终回退：查找所有含标题链接的列表项
                post_items = soup.select("li:has(a[href*='/'])")

            for item in post_items:
                if len(records) >= limit:
                    break

                # 标题
                title_el = (
                    item.select_one("a[class*=title]") or
                    item.select_one(".truetit") or
                    item.select_one("a[class*=thread-title]") or
                    item.select_one("a[href*='post']") or
                    item.select_one("a[href*='thread']")
                )
                title = title_el.get_text(strip=True)[:200] if title_el else ""
                href = title_el.get("href", "") if title_el else ""

                if not title or not href:
                    continue

                full_url = f"https://bbs.hupu.com{href}" if href.startswith("/") else href

                # 去重 (基于 URL)
                if full_url in seen:
                    continue
                seen.add(full_url)

                # 提取 thread_id
                tid_match = re.search(r"/(\d+)\.html", href)
                tid = tid_match.group(1) if tid_match else href

                # 作者
                author_el = (
                    item.select_one(".author a") or
                    item.select_one(".user-name") or
                    item.select_one("[class*=author]") or
                    item.select_one("a[class*=user]")
                )
                author = author_el.get_text(strip=True)[:50] if author_el else ""

                # 回复数
                reply_el = (
                    item.select_one(".reply-count") or
                    item.select_one("[class*=reply] span") or
                    item.select_one(".num")
                )
                replies = _parse_count(reply_el)

                # 浏览数
                view_el = (
                    item.select_one(".view-count") or
                    item.select_one("[class*=view] span")
                )
                views = _parse_count(view_el)

                records.append(make_raw(
                    source="hupu",
                    record_type="post",
                    item_id=tid,
                    url=full_url,
                    title=title,
                    author_name=author,
                    views=views,
                    comments_count=replies,
                    html_snapshot=html_content if self.save_html else "",
                    extra={
                        "source_tab": "all-gambia",
                        "rank": len(records),
                    },
                ))
        except Exception as e:
            logger.warning(f"hot_posts error: {e}")
        finally:
            page.close(); ctx.close(); p.stop()
        return records

    def collect_all(self) -> list[RawRecord]:
        return self.collect_hot_posts(limit=50)


def _parse_count(el) -> int:
    if not el:
        return 0
    txt = el.get_text(strip=True)
    if not txt:
        return 0
    txt = txt.replace(",", "").replace(" ", "")
    if "万" in txt:
        try:
            return int(float(txt.replace("万", "")) * 10000)
        except ValueError:
            pass
    try:
        return int(txt)
    except ValueError:
        return 0
