"""
B站 Collector — 从 Bilibili 公开 API 采集趋势信号。

端点映射 SOP:
  Layer 1 (评论): 视频评论 — 提取痛点/诉求
  Layer 2 (视频详情): 标题/描述/UP主 — 理念形成
  Layer 3 (热门/排行): 首页热门 + 全站排行榜 — 内容传播
"""
import time
from typing import Optional

import httpx

from ..models.signal import TrendSignal, make_signal, SignalType
from ..utils.signal_classifier import classify_signal_type, classify_domain, extract_keywords

BASE = "https://api.bilibili.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


class BilibiliCollector:
    def __init__(self, timeout: int = 20, delay: float = 1.0):
        self.timeout = timeout
        self.delay = delay
        self._client = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                headers={"User-Agent": UA, "Referer": "https://www.bilibili.com"},
                timeout=self.timeout, follow_redirects=True,
            )
        return self._client

    def close(self): self._client and self._client.close(); self._client = None
    def __enter__(self): return self
    def __exit__(self, *a): self.close()

    def _get(self, path: str, params: dict = None) -> dict | None:
        try:
            r = self.client.get(f"{BASE}{path}", params=params)
            if r.status_code != 200: return None
            data = r.json()
            return data.get("data") if data.get("code") == 0 else None
        except Exception:
            return None

    def _sleep(self): time.sleep(self.delay)

    def collect_popular(self, count: int = 50) -> list[TrendSignal]:
        """Layer 3: 热门推荐"""
        signals, seen = [], set()
        for pn in range(1, (count // 20) + 2):
            data = self._get("/x/web-interface/popular", {"pn": pn, "ps": 20})
            if not data: break
            for v in data.get("list", []):
                bvid = v.get("bvid", "")
                if bvid in seen: continue
                seen.add(bvid)
                stat = v.get("stat", {})
                title = v.get("title", "")
                desc = v.get("desc", "")
                category = v.get("tname", "")
                signals.append(make_signal(
                    source="bilibili",
                    signal_type=SignalType.L3_TRENDING,
                    title=title,
                    content=desc,
                    url=f"https://www.bilibili.com/video/{bvid}",
                    author=v.get("owner", {}).get("name", ""),
                    domain=classify_domain(title, desc),
                    keywords=extract_keywords(title, category),
                    views=stat.get("view", 0),
                    likes=stat.get("like", 0),
                    comments=stat.get("reply", 0),
                    favorites=stat.get("favorite", 0),
                    shares=stat.get("share", 0),
                    raw_stats=stat,
                ))
            if len(seen) >= count: break
            self._sleep()
        return signals

    def collect_ranking(self) -> list[TrendSignal]:
        """Layer 3: 全站排行榜"""
        data = self._get("/x/web-interface/ranking/v2", {"rid": 0, "type": "all"})
        if not data: return []
        signals = []
        for v in data.get("list", []):
            bvid = v.get("bvid", "")
            stat = v.get("stat", {})
            title = v.get("title", "")
            desc = v.get("desc", "")
            rank = v.get("rank", 0)
            signals.append(make_signal(
                source="bilibili",
                signal_type=SignalType.L3_TRENDING,
                title=title,
                content=desc,
                url=f"https://www.bilibili.com/video/{bvid}",
                author=v.get("owner", {}).get("name", ""),
                domain=classify_domain(title, desc),
                keywords=extract_keywords(title, v.get("tname", "")),
                views=stat.get("view", 0),
                likes=stat.get("like", 0),
                comments=stat.get("reply", 0),
                favorites=stat.get("favorite", 0),
                shares=stat.get("share", 0),
                rank=rank,
                heat_score=v.get("score", 0),
                raw_stats={"rank": rank, "score": v.get("score"), **stat},
            ))
        return signals

    def collect_comments(self, bvid: str, video_title: str = "", count: int = 50) -> list[TrendSignal]:
        """Layer 1: 视频评论 — 需求萌芽信号"""
        detail = self._get("/x/web-interface/view", {"bvid": bvid})
        if not detail: return []
        aid = detail.get("aid")
        if not aid: return []

        signals, seen = [], set()
        for pn in range(1, (count // 20) + 2):
            data = self._get("/x/v2/reply", {"type": 1, "oid": aid, "pn": pn, "ps": 20, "sort": 2})
            if not data: break
            for r in data.get("replies", []):
                rpid = r.get("rpid", 0)
                if rpid in seen: continue
                seen.add(rpid)
                msg = r.get("content", {}).get("message", "")
                member = r.get("member", {})
                stype = classify_signal_type(msg, "", "bilibili", "comment")
                signals.append(make_signal(
                    source="bilibili",
                    signal_type=stype,
                    title=video_title[:50] if video_title else msg[:50],
                    content=msg,
                    url=f"https://www.bilibili.com/video/{bvid}#reply{rpid}",
                    author=member.get("uname", ""),
                    domain=classify_domain(video_title, msg),
                    keywords=extract_keywords(msg, video_title),
                    likes=r.get("like", 0),
                    raw_stats={"rpid": rpid, "rcount": r.get("rcount", 0)},
                ))
            if len(seen) >= count: break
            self._sleep()
        return signals

    def collect_comments_for_popular(self, video_count: int = 10, comments_per_video: int = 20) -> list[TrendSignal]:
        """便捷: 获取热门视频的评论"""
        popular = self.collect_popular(count=video_count)
        all_comments = []
        for i, s in enumerate(popular):
            bvid = s.url.split("/")[-1]
            comments = self.collect_comments(bvid, video_title=s.title, count=comments_per_video)
            all_comments.extend(comments)
            if i < len(popular) - 1: self._sleep()
        return all_comments

    def collect_all(self) -> list[TrendSignal]:
        return (
            self.collect_popular()
            + self.collect_ranking()
            + self.collect_comments_for_popular(video_count=3, comments_per_video=10)
        )
