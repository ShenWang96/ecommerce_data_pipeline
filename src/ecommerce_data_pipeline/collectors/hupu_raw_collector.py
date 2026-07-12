"""
虎扑 RawCollector — 步行街热帖原始数据落地。

采集: bbs.hupu.com/all-gambia 步行街主版面热帖
方式: httpx 直接获取 SSR HTML (无需登录、无需 Playwright)
登录: 不需要 — 步行街热帖为公开内容
"""
import logging
import re
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from ..models.raw_record import RawRecord, make_raw
from ..utils.cookies import auto_load, check_valid

logger = logging.getLogger("hupu")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


def _parse_count(text: str) -> int:
    """解析 '1.2万' / '834' / '12,345' 等数字文本"""
    if not text:
        return 0
    text = text.replace(",", "").replace(" ", "").strip()
    if "万" in text:
        try:
            return int(float(text.replace("万", "")) * 10000)
        except ValueError:
            pass
    try:
        return int(text)
    except ValueError:
        return 0


class HupuRawCollector:
    def __init__(
        self,
        cookies: list[dict] | None = None,
        timeout: int = 20,
        **kwargs,  # 兼容旧参数 (headless, user_data_dir 等)
    ):
        if cookies is None:
            cookies = auto_load("hupu")
        self.cookies = cookies
        self.timeout = timeout

    @classmethod
    def check_ready(cls) -> bool:
        """虎扑步行街不需要登录，始终可用"""
        return True

    def _client(self) -> httpx.Client:
        h = {"User-Agent": UA, "Referer": "https://bbs.hupu.com/"}
        if self.cookies:
            h["Cookie"] = "; ".join(f"{c['name']}={c['value']}" for c in self.cookies)
        return httpx.Client(headers=h, timeout=self.timeout, follow_redirects=True)

    def collect_hot_posts(self, limit: int = 60) -> list[RawRecord]:
        """步行街热帖 — 直接解析 SSR HTML"""
        records = []
        try:
            with self._client() as c:
                r = c.get("https://bbs.hupu.com/all-gambia")
            if r.status_code != 200:
                logger.warning(f"hupu status: {r.status_code}")
                return records

            soup = BeautifulSoup(r.text, "lxml")

            # 帖子链接格式: /数字.html
            seen = set()
            for a in soup.find_all("a", href=re.compile(r"/\d{4,}\.html")):
                if len(records) >= limit:
                    break

                title = a.get_text(strip=True)
                href = a.get("href", "")
                if not title or len(title) < 6:
                    continue

                full_url = f"https://bbs.hupu.com{href}" if href.startswith("/") else href
                if full_url in seen:
                    continue
                seen.add(full_url)

                # 提取 thread_id
                tid_match = re.search(r"/(\d+)\.html", href)
                tid = tid_match.group(1) if tid_match else href

                # 向上找帖子容器，提取作者/回复数/浏览数
                post_div = a.find_parent("div", class_=re.compile("t-info|thread|post|list"))
                if not post_div:
                    post_div = a.parent

                # 作者
                author = ""
                author_el = post_div.find("a", class_=re.compile("user|author")) if post_div else None
                if not author_el:
                    author_el = post_div.find("span", attrs={"class": "author"}) if post_div else None
                if author_el:
                    author = author_el.get_text(strip=True)

                # 回复数 / 浏览数 — 在兄弟元素中查找
                replies = 0
                views = 0
                if post_div:
                    # 向上再找一层到帖子行容器
                    row = post_div.parent if post_div.parent else post_div
                    row_text = row.get_text()

                    # 回复数: 通常在 "回复" 旁边或独立的数字 span
                    reply_el = row.find(class_=re.compile("reply|comment|ans"))
                    if reply_el:
                        replies = _parse_count(reply_el.get_text(strip=True))

                    view_el = row.find(class_=re.compile("view|browse|click"))
                    if view_el:
                        views = _parse_count(view_el.get_text(strip=True))

                # 板块/分区
                board = ""
                board_el = post_div.find("a", class_=re.compile("board|node")) if post_div else None
                if board_el:
                    board = board_el.get_text(strip=True)

                records.append(make_raw(
                    source="hupu",
                    record_type="post",
                    item_id=tid,
                    url=full_url,
                    title=title,
                    author_name=author,
                    views=views,
                    comments_count=replies,
                    extra={
                        "source_tab": "all-gambia",
                        "board": board,
                        "rank": len(records) + 1,
                    },
                ))
        except Exception as e:
            logger.warning(f"hot_posts error: {e}")
        return records

    def collect_all(self) -> list[RawRecord]:
        return self.collect_hot_posts(limit=60)
