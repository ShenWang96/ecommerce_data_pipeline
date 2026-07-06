"""
知乎 Collector — Layer 1 需求萌芽信号。

无登录: /explore 发现页 (热点问题标题+回答数)
有 Cookie: /api/v3/feed/topstory/hot-lists/total 热榜 JSON API
"""
import re
import time
import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from ..models.signal import TrendSignal, make_signal, SignalType
from ..utils.signal_classifier import classify_signal_type, classify_domain, extract_keywords
from ..utils.cookies import auto_load, check_valid

logger = logging.getLogger("zhihu")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


class ZhihuCollector:
    def __init__(self, cookies: list[dict] | None = None, timeout: int = 20, delay: float = 2.0):
        if cookies is None:
            cookies = auto_load("zhihu")
        self.cookies = cookies
        self.timeout = timeout
        self.delay = delay

    @classmethod
    def check_ready(cls) -> bool:
        info = check_valid("zhihu")
        return info["exists"] and len(info["key_cookies"]) >= 1

    def _client(self) -> httpx.Client:
        h = {"User-Agent": UA, "Referer": "https://www.zhihu.com"}
        if self.cookies:
            h["Cookie"] = "; ".join(f"{c['name']}={c['value']}" for c in self.cookies)
        return httpx.Client(headers=h, timeout=self.timeout, follow_redirects=True)

    def collect_explore(self) -> list[TrendSignal]:
        """Layer 1: 发现页热点问题 — 无需登录"""
        signals = []
        try:
            with self._client() as c:
                r = c.get("https://www.zhihu.com/explore")
            if r.status_code != 200: return signals
            soup = BeautifulSoup(r.text, "lxml")
            seen = set()
            for a in soup.select('a[href*="/question/"]'):
                title = a.get_text(strip=True)
                href = a.get("href", "")
                if not title or len(title) < 8 or title.startswith("http") or title in seen:
                    continue
                seen.add(title)
                url = f"https://www.zhihu.com{href}" if href.startswith("/") else href
                answer_count = 0
                parent = a.parent
                for _ in range(3):
                    if parent:
                        m = re.search(r"(\d[\d,]*)\s*(?:个回答|回答)", parent.get_text())
                        if m: answer_count = int(m.group(1).replace(",", "")); break
                        parent = parent.parent

                stype = classify_signal_type(title, "", "zhihu", "")
                signals.append(make_signal(
                    source="zhihu",
                    signal_type=stype,
                    title=title,
                    content=title,
                    url=url,
                    domain=classify_domain(title, ""),
                    keywords=extract_keywords(title, ""),
                    comments=answer_count,
                    raw_stats={"answer_count": answer_count},
                ))
        except Exception as e:
            logger.warning(f"explore error: {e}")
        return signals

    def collect_hot_api(self) -> list[TrendSignal]:
        """Layer 1: 热榜 JSON API — 需 Cookie"""
        if not self.cookies: return []
        signals = []
        try:
            with self._client() as c:
                r = c.get("https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50&desktop=true")
            if r.status_code != 200: return signals
            data = r.json()
            for item in data.get("data", []):
                target = item.get("target", {})
                title = target.get("title", "").strip()
                if not title: continue
                metrics_text = target.get("metrics_area", {}).get("text", "")
                stype = classify_signal_type(title, metrics_text, "zhihu", "")
                signals.append(make_signal(
                    source="zhihu",
                    signal_type=stype,
                    title=title,
                    content=metrics_text,
                    url=f"https://www.zhihu.com/question/{target.get('id','')}",
                    domain=classify_domain(title, metrics_text),
                    keywords=extract_keywords(title, metrics_text),
                    raw_stats={"metrics": metrics_text, "target": target},
                ))
        except Exception as e:
            logger.warning(f"hot_api error: {e}")
        return signals

    def collect_all(self) -> list[TrendSignal]:
        signals = self.collect_explore()
        if self.cookies:
            time.sleep(self.delay)
            signals.extend(self.collect_hot_api())
        return signals
