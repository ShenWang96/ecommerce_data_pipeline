"""
今日头条 RawCollector — 原始热榜数据落地。

采集: toutiao.com/hot-event/hot-board/ JSON API — 无需登录，公开接口
"""
import logging
from typing import Optional

import httpx

from ..models.raw_record import RawRecord, make_raw

logger = logging.getLogger("toutiao")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

HOT_API = "https://www.toutiao.com/hot-event/hot-board/?origin=toutiao_pc"


class ToutiaoRawCollector:
    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    @staticmethod
    def check_ready() -> bool:
        return True

    def _client(self) -> httpx.Client:
        h = {"User-Agent": UA, "Referer": "https://www.toutiao.com", "Accept": "application/json, text/plain, */*"}
        return httpx.Client(headers=h, timeout=self.timeout, follow_redirects=True)

    def collect_hot_board(self) -> list[RawRecord]:
        """头条热榜 — 完整 JSON 响应"""
        records = []
        try:
            with self._client() as c:
                r = c.get(HOT_API)
            if r.status_code != 200:
                logger.warning(f"hot_board HTTP {r.status_code}")
                return records
            data = r.json()
            items = data.get("data", [])
            for item in items:
                cluster_id = str(item.get("ClusterId", ""))
                title = item.get("Title", "").strip()
                if not title or not cluster_id:
                    continue
                hot_value = item.get("HotValue", "0")
                label = item.get("Label", "")
                categories = item.get("InterestCategory", [])
                image = item.get("Image", {})
                image_url = image.get("url", "") if image else ""

                url = item.get("Url", "")
                if not url:
                    url = f"https://www.toutiao.com/trending/{cluster_id}/"

                records.append(make_raw(
                    source="toutiao",
                    record_type="topic",
                    item_id=cluster_id,
                    url=url,
                    title=title,
                    body=title,
                    cover_url=image_url,
                    extra={
                        "hot_value": hot_value,
                        "label": label,
                        "categories": categories,
                        "rank": records.__len__(),
                    },
                    api_response=item,
                ))
        except Exception as e:
            logger.warning(f"hot_board error: {e}")
        return records

    def collect_all(self) -> list[RawRecord]:
        return self.collect_hot_board()
