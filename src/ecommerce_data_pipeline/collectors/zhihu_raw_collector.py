"""
知乎 RawCollector — 原始数据落地。

/hot 热榜页 — HTML 解析，提取问题标题+热度+回答数+链接 (需 Cookie)
/api/v3/feed/topstory/hot-lists/total 热榜 JSON — 完整 API 响应 (需 Cookie)
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

    def collect_hot_list(self) -> list[RawRecord]:
        """热榜页 https://www.zhihu.com/hot — HTML 解析"""
        records = []
        try:
            with self._client() as c:
                r = c.get("https://www.zhihu.com/hot")
            if r.status_code != 200: return records
            soup = BeautifulSoup(r.text, "lxml")

            # 匹配热榜条目: .HotList-item 或 [class*=HotItem]
            items = soup.select(".HotList-item, [class*=HotItem]")
            if not items:
                # 回退: 直接从页面提取所有问题链接
                items = soup.select('a[href*="/question/"]')

            seen = set()
            for item in items:
                # 提取链接和标题
                link = item.select_one('a[href*="/question/"]')
                if not link:
                    continue
                title = link.get_text(strip=True)
                href = link.get("href", "")
                if not title or len(title) < 6 or title.startswith("http"):
                    continue
                if title in seen:
                    continue
                seen.add(title)

                url = f"https://www.zhihu.com{href}" if href.startswith("/") else href
                qid = url.split("/")[-1] if "/question/" in url else ""

                # 尝试提取热度指标
                item_text = item.get_text()
                heat_metric = ""
                heat_m = re.search(r"(\d[\d,.]*\s*万?\s*热度)", item_text)
                if heat_m:
                    heat_metric = heat_m.group(1)

                # 尝试提取回答数
                answer_count = 0
                answer_m = re.search(r"(\d[\d,]*)\s*(?:个回答|回答)", item_text)
                if answer_m:
                    answer_count = int(answer_m.group(1).replace(",", ""))

                records.append(make_raw(
                    source="zhihu",
                    record_type="question",
                    item_id=qid,
                    url=url,
                    title=title,
                    body=heat_metric,
                    comments_count=answer_count,
                    html_snapshot="",
                    extra={
                        "answer_count": answer_count,
                        "heat_metric": heat_metric,
                    },
                ))
        except Exception as e:
            logger.warning(f"hot_list error: {e}")
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
                excerpt = target.get("excerpt", "").strip()
                # excerpt 是问题的详细描述，作为 body 的主要内容
                # metrics_text (如 "76 回答 · 5 关注") 放入 extra
                records.append(make_raw(
                    source="zhihu",
                    record_type="question",
                    item_id=qid,
                    url=f"https://www.zhihu.com/question/{qid}" if qid else "",
                    title=title,
                    body=excerpt or metrics_text,
                    extra={"metrics_text": metrics_text, "excerpt": excerpt},
                    api_response=target,
                ))
        except Exception as e:
            logger.warning(f"hot_api error: {e}")
        return records

    def collect_all(self) -> list[RawRecord]:
        # 有 Cookie 时优先走 API 路径（数据更全：含 excerpt 问题详情）
        if self.cookies:
            api_records = self.collect_hot_api()
            if api_records:
                return api_records
        # 无 Cookie 或 API 失败时回退到 HTML 解析
        return self.collect_hot_list()
