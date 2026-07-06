"""
小红书 RawCollector — 原始笔记数据落地。

采集:
  - 热门笔记 (Explore/发现页): 平台算法推荐的热门内容 (≈ 微博热搜/知乎热榜)
  - 热搜关键词: 搜索框下拉 trending searches
  - 搜索页: 特定关键词笔记 (保留，默认不使用)

特点:
  - 使用 Playwright stealth 模式绕过反爬
  - 可保存完整 HTML 快照 (默认关闭以节省空间)
  - 自动加载 Cookie
"""
import logging
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from ..models.raw_record import RawRecord, make_raw
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


class XiaohongshuRawCollector:
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
            cookies = auto_load("xiaohongshu")
        self.cookies = cookies
        self.headless = headless
        self.timeout = timeout
        self.wait_seconds = wait_seconds
        self.save_html = save_html
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

    def collect_search(self, keyword: str, limit: int = 30) -> list[RawRecord]:
        """搜索笔记 — 完整标题+作者+URL+图片URL"""
        records = []
        p, ctx = self._new_browser_and_context()
        page = ctx.new_page()
        try:
            url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes"
            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(self.wait_seconds * 1000)

            html_content = page.content() if self.save_html else ""
            soup = BeautifulSoup(page.content(), "lxml")

            for item in soup.select("section.note-item")[:limit]:
                # 标题
                title_el = item.select_one(".title span") or item.select_one('[class*=title] span')
                title = title_el.get_text(strip=True)[:200] if title_el else ""

                # 作者
                author_el = item.select_one('[class*=author] .name') or item.select_one('.name')
                author = author_el.get_text(strip=True)[:50] if author_el else ""

                # 链接
                link_el = item.select_one("a[href*='/explore/']") or item.select_one("a[href*='/search_result/']")
                href = link_el.get("href", "") if link_el else ""
                note_url = f"https://www.xiaohongshu.com{href}" if href.startswith("/") else href
                note_id = href.split("/")[-1] if href else ""

                # 图片URL
                img_urls = []
                for img in item.select("img[src]"):
                    src = img.get("src", "") or img.get("data-src", "")
                    if src and "http" in src:
                        img_urls.append(src)

                # 封面
                cover_el = item.select_one(".cover img") or item.select_one("img[class*=cover]")
                cover = (cover_el.get("src") or cover_el.get("data-src", "")) if cover_el else ""
                if not cover and img_urls:
                    cover = img_urls[0]

                # 互动数据
                likes = _parse_count(item.select_one('[class*=like] span') or item.select_one('[class*=count]'))
                comments = _parse_count(item.select_one('[class*=comment] span'))

                if not title:
                    continue

                records.append(make_raw(
                    source="xiaohongshu",
                    record_type="note",
                    item_id=note_id,
                    url=note_url,
                    title=title,
                    author_name=author,
                    cover_url=cover,
                    images=img_urls,
                    likes=likes,
                    comments_count=comments,
                    html_snapshot=html_content if self.save_html else "",
                    extra={
                        "keyword": keyword,
                        "rank": 0,
                    },
                ))
        except Exception as e:
            logger.warning(f"search error: {e}")
        finally:
            page.close(); ctx.close(); p.stop()
        return records

    def collect_explore(self, limit: int = 50, scroll_times: int = 3) -> list[RawRecord]:
        """热门笔记 — 发现页 (平台热榜，≈ 微博热搜/知乎热榜).
        
        通过滚动加载更多热门笔记。
        """
        records = []
        seen = set()
        p, ctx = self._new_browser_and_context()
        page = ctx.new_page()
        try:
            page.goto("https://www.xiaohongshu.com/explore",
                      wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(self.wait_seconds * 1000)

            for _ in range(scroll_times):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)

            html_content = page.content() if self.save_html else ""
            soup = BeautifulSoup(page.content(), "lxml")

            for item in soup.select("section.note-item"):
                if len(records) >= limit:
                    break

                title_el = item.select_one(".title span")
                title = title_el.get_text(strip=True)[:200] if title_el else ""
                author_el = item.select_one('.name')
                author = author_el.get_text(strip=True)[:50] if author_el else ""
                link_el = item.select_one("a[href*='/explore/']")
                href = link_el.get("href", "") if link_el else ""
                note_url = f"https://www.xiaohongshu.com{href}" if href.startswith("/") else href
                note_id = href.split("/")[-1] if href else ""

                if not title or note_id in seen:
                    continue
                seen.add(note_id)

                img_urls = []
                for img in item.select("img[src]"):
                    src = img.get("src", "") or img.get("data-src", "")
                    if src and "http" in src:
                        img_urls.append(src)
                cover = img_urls[0] if img_urls else ""

                records.append(make_raw(
                    source="xiaohongshu",
                    record_type="note",
                    item_id=note_id,
                    url=note_url,
                    title=title,
                    author_name=author,
                    cover_url=cover,
                    images=img_urls,
                    html_snapshot=html_content if self.save_html else "",
                    extra={"source_tab": "explore"},
                ))
        except Exception as e:
            logger.warning(f"explore error: {e}")
        finally:
            page.close(); ctx.close(); p.stop()
        return records

    def collect_trending_searches(self, limit: int = 30) -> list[RawRecord]:
        """热搜关键词 — "猜你想搜" / trending searches.
        
        在 explore 页点击搜索区域触发 suggestion 面板，抓取热搜词。
        """
        records = []
        p, ctx = self._new_browser_and_context()
        page = ctx.new_page()
        try:
            page.goto("https://www.xiaohongshu.com/explore",
                      wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(3000)

            # 点击搜索区域触发 suggestion 面板
            clicked = False
            for selector in ['.search-area', '[class*=search-area]',
                             '.wendian-wrapper', '[class*=wendian]',
                             'textarea']:
                el = page.query_selector(selector)
                if el:
                    try:
                        el.click(force=True, timeout=5000)
                        clicked = True
                        break
                    except Exception:
                        continue
            if not clicked:
                logger.info("could not trigger search area, no trending searches")
                return records

            page.wait_for_timeout(3000)

            html_content = page.content() if self.save_html else ""
            soup = BeautifulSoup(page.content(), "lxml")

            # suggestion-section 面板中的 suggestion-item
            items = soup.select('.suggestion-item, [class*=suggestion] [class*=item]')
            if not items:
                # 退而求其次: 查找任何 suggestion 相关的可见文字元素
                section = soup.select_one('[class*=suggestion-section], [class*=suggest]')
                if section:
                    items = section.find_all(['div', 'span'])

            seen_terms = set()
            for el in items[:limit]:
                # 取 suggestion-content 优先于整个元素的 text
                content_el = el.select_one('[class*=content]') or el.select_one('[class*=desc]')
                term = content_el.get_text(strip=True) if content_el else el.get_text(strip=True)

                if not term or len(term) < 2 or len(term) > 30:
                    continue
                if term in seen_terms or term == "猜你想搜":
                    continue
                # 跳过纯数字/符号
                if term.isdigit() or all(c in '0123456789., #' for c in term):
                    continue
                seen_terms.add(term)

                item_id = f"trending_search_{hash(term) & 0x7FFFFFFF}"
                records.append(make_raw(
                    source="xiaohongshu",
                    record_type="topic",
                    item_id=item_id,
                    url=f"https://www.xiaohongshu.com/search_result?keyword={term}",
                    title=term,
                    html_snapshot=html_content if self.save_html else "",
                    extra={
                        "source_tab": "trending_search",
                        "rank": len(records),
                    },
                ))
        except Exception as e:
            logger.warning(f"trending search error: {e}")
        finally:
            page.close(); ctx.close(); p.stop()
        return records

    def collect_all(self, keywords: list[str] | None = None) -> list[RawRecord]:
        records = self.collect_explore(limit=50)
        trending = self.collect_trending_searches(limit=30)
        records.extend(trending)
        return records


def _parse_count(el) -> int:
    if not el: return 0
    txt = el.get_text(strip=True)
    if not txt: return 0
    # 处理 "1.2万" 格式
    txt = txt.replace(",", "").replace(" ", "")
    if "万" in txt:
        try: return int(float(txt.replace("万", "")) * 10000)
        except: pass
    try: return int(txt)
    except: return 0
