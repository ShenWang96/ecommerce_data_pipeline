"""
微博 RawCollector — 原始热搜数据落地。

采集: weibo.com/ajax/side/hotSearch JSON API — 完整响应+所有字段
"""
import logging
from typing import Optional

import httpx

from ..models.raw_record import RawRecord, make_raw
from ..utils.cookies import auto_load, check_valid

logger = logging.getLogger("weibo")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


class WeiboRawCollector:
    def __init__(self, cookies: list[dict] | None = None, timeout: int = 20):
        if cookies is None:
            cookies = auto_load("weibo")
        self.cookies = cookies
        self.timeout = timeout

    @classmethod
    def check_ready(cls) -> bool:
        info = check_valid("weibo")
        return info["exists"] and len(info["key_cookies"]) >= 1

    def _client(self) -> httpx.Client:
        h = {"User-Agent": UA, "Referer": "https://weibo.com", "Accept": "application/json, text/plain, */*"}
        if self.cookies:
            h["Cookie"] = "; ".join(f"{c['name']}={c['value']}" for c in self.cookies)
        return httpx.Client(headers=h, timeout=self.timeout, follow_redirects=True)

    def collect_hot_search(self) -> list[RawRecord]:
        """热搜榜 — 完整 JSON 响应"""
        if not self.cookies: return []
        records = []
        try:
            with self._client() as c:
                r = c.get("https://weibo.com/ajax/side/hotSearch")
            if r.status_code != 200: return records
            data = r.json()
            realtime = data.get("data", {}).get("realtime", [])
            for item in realtime:
                word = item.get("word", "").strip()
                if not word: continue
                records.append(make_raw(
                    source="weibo",
                    record_type="topic",
                    item_id=word,
                    url=f"https://s.weibo.com/weibo?q={word}",
                    title=word,
                    body=item.get("note", ""),
                    extra={
                        "rank": item.get("rank", 0),
                        "raw_hot": item.get("raw_hot", ""),
                        "category": item.get("category", ""),
                        "icon_desc": item.get("icon_desc", ""),
                        "num": item.get("num", 0),
                        "onboard_time": item.get("onboard_time", 0),
                    },
                    api_response=item,
                ))
        except Exception as e:
            logger.warning(f"hot_search error: {e}")
        return records

    def collect_all(self) -> list[RawRecord]:
        return self.collect_hot_search()
