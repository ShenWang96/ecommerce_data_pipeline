"""
百度 RawCollector — 原始热搜数据落地。

采集: top.baidu.com/api/board 热搜 JSON API — 无需登录，公开接口
"""
import logging
from typing import Optional

import httpx

from ..models.raw_record import RawRecord, make_raw

logger = logging.getLogger("baidu")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

HOT_API = "https://top.baidu.com/api/board?platform=wise&tab=realtime"


class BaiduRawCollector:
    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    @staticmethod
    def check_ready() -> bool:
        return True

    def _client(self) -> httpx.Client:
        h = {"User-Agent": UA, "Referer": "https://top.baidu.com", "Accept": "application/json, text/plain, */*"}
        return httpx.Client(headers=h, timeout=self.timeout, follow_redirects=True)

    def collect_hot_search(self) -> list[RawRecord]:
        """百度热搜 — 完整 JSON 响应"""
        records = []
        try:
            with self._client() as c:
                r = c.get(HOT_API)
            if r.status_code != 200:
                logger.warning(f"hot_search HTTP {r.status_code}")
                return records
            data = r.json()
            cards = data.get("data", {}).get("cards", [])
            for card in cards:
                if card.get("component") != "tabTextList":
                    continue
                for group in card.get("content", []):
                    for item in group.get("content", []):
                        word = item.get("word", "").strip()
                        if not word:
                            continue
                        index = item.get("index", records.__len__())
                        is_top = item.get("isTop", False)
                        hot_tag = item.get("hotTag", "")
                        new_hot_name = ""
                        if item.get("newHotTag"):
                            new_hot_name = item.get("newHotTag", {}).get("newHotName", "")
                        url = item.get("url", f"https://m.baidu.com/s?word={word}")

                        records.append(make_raw(
                            source="baidu",
                            record_type="topic",
                            item_id=word,
                            url=url,
                            title=word,
                            body=word,
                            extra={
                                "rank": index,
                                "is_top": is_top,
                                "hot_tag": hot_tag,
                                "hot_label": new_hot_name,
                            },
                            api_response=item,
                        ))
        except Exception as e:
            logger.warning(f"hot_search error: {e}")
        return records

    def collect_all(self) -> list[RawRecord]:
        return self.collect_hot_search()
