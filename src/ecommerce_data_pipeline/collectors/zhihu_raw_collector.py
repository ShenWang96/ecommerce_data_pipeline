"""
知乎 RawCollector — 原始数据落地。

无登录: /explore 发现页 — 保存问题标题+回答数+链接
有 Cookie: /api/v3/feed/topstory/hot-lists/total 热榜 JSON — 完整 API 响应
"""
import re
import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from ..models.raw_record import RawRecord, make_raw
from ..utils.cookies import auto_load, check_valid

logger = logging.getLogger("zhihu")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


class ZhihuRawCollector:
    def __init__(self, cookies: list[dict] | None = None, timeout: int = 20):
        if cookies is None:
            cookies = auto_load("zhihu")
        self.cookies = cookies
        self.timeout = timeout

    @classmethod
    def check_ready(cls) -> bool:
        info = check_valid("zhihu")
        return info["exists"] and len(info["key_cookies"]) >= 1

    def _client(self) -> httpx.Client:
        h = {"User-Agent": UA, "Referer": "https://www.zhihu.com"}
        if self.cookies:
            h["Cookie"] = "; ".join(f"{c['name']}={c['value']}" for c in self.cookies)
        return httpx.Client(headers=h, timeout=self.timeout, follow_redirects=True)

    def collect_explore(self) -> list[RawRecord]:
        """发现页 — HTML 中提取问题链接+回答数"""
        records = []
        try:
            with self._client() as c:
                r = c.get("https://www.zhihu.com/explore")
            if r.status_code != 200: return records
            soup = BeautifulSoup(r.text, "lxml")

            for a in soup.select('a[href*="/question/"]'):
                title = a.get_text(strip=True)
                href = a.get("href", "")
                if not title or len(title) < 8 or title.startswith("http"):
                    continue
                url = f"https://www.zhihu.com{href}" if href.startswith("/") else href
                qid = url.split("/")[-1] if "/question/" in url else ""

                # 尝试提取回答数
                answer_count = 0
                parent = a.parent
                for _ in range(3):
                    if parent:
                        m = re.search(r"(\d[\d,]*)\s*(?:个回答|回答)", parent.get_text())
                        if m: answer_count = int(m.group(1).replace(",", "")); break
                        parent = parent.parent

                records.append(make_raw(
                    source="zhihu",
                    record_type="question",
                    item_id=qid,
                    url=url,
                    title=title,
                    body=title,
                    comments_count=answer_count,
                    html_snapshot="",  # 可选: 保存完整 HTML (太大)
                    extra={"answer_count": answer_count},
                ))
        except Exception as e:
            logger.warning(f"explore error: {e}")
        return records

    def collect_hot_api(self) -> list[RawRecord]:
        """热榜 JSON API — 需 Cookie"""
        if not self.cookies: return []
        records = []
        try:
            with self._client() as c:
                r = c.get("https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50&desktop=true")
            if r.status_code != 200: return records
            data = r.json()
            for item in data.get("data", []):
                target = item.get("target", {})
                title = target.get("title", "").strip()
                if not title: continue
                qid = str(target.get("id", ""))
                metrics_text = target.get("metrics_area", {}).get("text", "")
                records.append(make_raw(
                    source="zhihu",
                    record_type="question",
                    item_id=qid,
                    url=f"https://www.zhihu.com/question/{qid}" if qid else "",
                    title=title,
                    body=metrics_text,
                    extra={"metrics_text": metrics_text},
                    api_response=target,
                ))
        except Exception as e:
            logger.warning(f"hot_api error: {e}")
        return records

    def collect_all(self) -> list[RawRecord]:
        records = self.collect_explore()
        if self.cookies:
            records.extend(self.collect_hot_api())
        return records
