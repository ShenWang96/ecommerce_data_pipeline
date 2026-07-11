"""
结构化媒体 RawCollector — 原始深度内容数据落地。

采集:
  - 36kr RSS 订阅源
  - 华尔街见闻 实时快讯 API
"""
import logging
import re
from typing import Optional
from xml.etree import ElementTree as ET

import httpx

from ..models.raw_record import RawRecord, make_raw

logger = logging.getLogger("structured_media")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

RSS_FEEDS = {
    "36kr": "https://36kr.com/feed",
}

WALLSTREET_API = "https://api-one.wallstcn.com/apiv1/content/lives?channel=global-channel&limit=20"


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


class WechatRawCollector:

    def __init__(self, timeout: int = 20):
        self.timeout = timeout

    @staticmethod
    def check_ready() -> bool:
        return True

    def _client(self) -> httpx.Client:
        h = {"User-Agent": UA, "Accept": "application/xml, text/xml, */*"}
        return httpx.Client(headers=h, timeout=self.timeout, follow_redirects=True)

    def _api_client(self) -> httpx.Client:
        h = {"User-Agent": UA, "Accept": "application/json, text/plain, */*",
             "Referer": "https://wallstreetcn.com/"}
        return httpx.Client(headers=h, timeout=self.timeout, follow_redirects=True)

    def collect_36kr(self) -> list[RawRecord]:
        """36氪 RSS — 结构化提取"""
        records = []
        try:
            with self._client() as c:
                r = c.get(RSS_FEEDS["36kr"])
            if r.status_code != 200:
                logger.warning(f"36kr_rss HTTP {r.status_code}")
                return records
            root = ET.fromstring(r.text)
            for item in root.findall(".//item"):
                title_el = item.find("title")
                link_el = item.find("link")
                desc_el = item.find("description")
                title = title_el.text.strip() if title_el is not None and title_el.text else ""
                link = link_el.text.strip() if link_el is not None and link_el.text else ""
                desc_html = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
                desc_text = _strip_html(desc_html)

                if not title:
                    continue

                item_id = link.split("/p/")[-1].split("?")[0] if "/p/" in link else link

                records.append(make_raw(
                    source="36kr",
                    record_type="article",
                    item_id=item_id,
                    url=link,
                    title=title,
                    body=desc_text[:2000],
                    extra={
                        "feed": "36kr_rss",
                        "desc_html": desc_html[:5000],
                    },
                ))
        except Exception as e:
            logger.warning(f"36kr_rss error: {e}")
        return records

    def collect_wallstreetcn(self) -> list[RawRecord]:
        """华尔街见闻 实时快讯 — 宏观政策/行业拐点等结构性信号"""
        records = []
        try:
            with self._api_client() as c:
                r = c.get(WALLSTREET_API)
            if r.status_code != 200:
                logger.warning(f"wallstreetcn HTTP {r.status_code}")
                return records
            data = r.json()
            items = data.get("data", {}).get("items", [])
            for item in items:
                cid = str(item.get("id", ""))
                title = (item.get("title") or "").strip()
                content = (item.get("content_text") or title).strip()
                if not content:
                    continue
                uri = item.get("uri", "")
                url = f"https://wallstreetcn.com{uri}" if uri else ""

                records.append(make_raw(
                    source="wallstreetcn",
                    record_type="flash",
                    item_id=cid,
                    url=url,
                    title=title,
                    body=content,
                    extra={
                        "channel": item.get("channel", ""),
                        "display_time": item.get("display_time", ""),
                    },
                    api_response=item,
                ))
        except Exception as e:
            logger.warning(f"wallstreetcn error: {e}")
        return records

    def collect_all(self) -> list[RawRecord]:
        records = self.collect_36kr()
        records.extend(self.collect_wallstreetcn())
        return records
