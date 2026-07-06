"""
微博 Collector — Layer 3 内容传播信号。

策略: httpx + Cookie 调用 weibo.com/ajax/side/hotSearch JSON API。
"""
import re
import logging
from typing import Optional

import httpx

from ..models.signal import TrendSignal, make_signal, SignalType
from ..utils.signal_classifier import classify_signal_type, classify_domain, extract_keywords
from ..utils.cookies import auto_load, check_valid

logger = logging.getLogger("weibo")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


class WeiboCollector:
    def __init__(self, cookies: list[dict] | None = None, timeout: int = 20, delay: float = 2.0):
        if cookies is None:
            cookies = auto_load("weibo")
        self.cookies = cookies
        self.timeout = timeout
        self.delay = delay

    @classmethod
    def check_ready(cls) -> bool:
        info = check_valid("weibo")
        return info["exists"] and len(info["key_cookies"]) >= 1

    def _client(self) -> httpx.Client:
        h = {"User-Agent": UA, "Referer": "https://weibo.com", "Accept": "application/json, text/plain, */*"}
        if self.cookies:
            h["Cookie"] = "; ".join(f"{c['name']}={c['value']}" for c in self.cookies)
        return httpx.Client(headers=h, timeout=self.timeout, follow_redirects=True)

    def collect_hot_search(self) -> list[TrendSignal]:
        """Layer 3: 微博热搜榜 — 需 Cookie"""
        if not self.cookies: return []
        signals = []
        try:
            with self._client() as c:
                r = c.get("https://weibo.com/ajax/side/hotSearch")
            if r.status_code != 200: return signals
            data = r.json()
            realtime = data.get("data", {}).get("realtime", [])
            for item in realtime:
                word = item.get("word", "").strip()
                if not word: continue
                rank = item.get("rank", 0)
                raw_hot = item.get("raw_hot", "")
                note = item.get("note", "")
                category = item.get("category", "")

                stype = classify_signal_type(word, note, "weibo", "")
                try:
                    heat_score = float(raw_hot) if raw_hot else None
                except (ValueError, TypeError):
                    heat_score = None

                signals.append(make_signal(
                    source="weibo",
                    signal_type=stype,
                    title=word,
                    content=note,
                    url=f"https://s.weibo.com/weibo?q={word}",
                    domain=classify_domain(word, note),
                    keywords=extract_keywords(word, note),
                    rank=rank,
                    heat_score=heat_score or 0,
                    raw_stats={"raw_hot": raw_hot, "category": category},
                ))
        except Exception as e:
            logger.warning(f"hot_search error: {e}")
        return signals

    def collect_all(self) -> list[TrendSignal]:
        return self.collect_hot_search()
