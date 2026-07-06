"""
B站 RawCollector — 从公开 API 采集原始数据，零信息损失。

采集内容:
  - 热门推荐 (Layer 3): 视频标题/描述/标签/UP主/全量统计
  - 全站排行榜 (Layer 3): 排名/分数/分区
  - 视频评论 (Layer 1): 评论全文+回复+点赞数

不做: 信号分类、关键词提取、领域分类 (留给 Signal Extraction Pipeline)
"""
import time
from typing import Optional, Iterator

import httpx

from ..models.raw_record import RawRecord, make_raw

BASE = "https://api.bilibili.com"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


class BilibiliRawCollector:
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

    def collect_popular(self, count: int = 50) -> list[RawRecord]:
        """热门推荐 — 完整视频元数据"""
        records, seen = [], set()
        for pn in range(1, (count // 20) + 2):
            data = self._get("/x/web-interface/popular", {"pn": pn, "ps": 20})
            if not data: break
            for v in data.get("list", []):
                bvid = v.get("bvid", "")
                if bvid in seen: continue
                seen.add(bvid)
                stat = v.get("stat", {})
                owner = v.get("owner", {})
                records.append(make_raw(
                    source="bilibili",
                    record_type="video",
                    item_id=bvid,
                    url=f"https://www.bilibili.com/video/{bvid}",
                    title=v.get("title", ""),
                    body=v.get("desc", ""),
                    author_name=owner.get("name", ""),
                    author_id=str(owner.get("mid", "")),
                    cover_url=v.get("pic", ""),
                    views=stat.get("view", 0),
                    likes=stat.get("like", 0),
                    comments_count=stat.get("reply", 0),
                    shares=stat.get("share", 0),
                    favorites=stat.get("favorite", 0),
                    extra={
                        "bvid": bvid,
                        "aid": v.get("aid", 0),
                        "tname": v.get("tname", ""),
                        "duration": v.get("duration", 0),
                        "danmaku": stat.get("danmaku", 0),
                        "coin": stat.get("coin", 0),
                        "owner": owner,
                    },
                    api_response=v,
                ))
            if len(seen) >= count: break
            self._sleep()
        return records

    def collect_ranking(self) -> list[RawRecord]:
        """全站排行榜"""
        data = self._get("/x/web-interface/ranking/v2", {"rid": 0, "type": "all"})
        if not data: return []
        records = []
        for v in data.get("list", []):
            bvid = v.get("bvid", "")
            stat = v.get("stat", {})
            owner = v.get("owner", {})
            records.append(make_raw(
                source="bilibili",
                record_type="video",
                item_id=bvid,
                url=f"https://www.bilibili.com/video/{bvid}",
                title=v.get("title", ""),
                body=v.get("desc", ""),
                author_name=owner.get("name", ""),
                author_id=str(owner.get("mid", "")),
                cover_url=v.get("pic", ""),
                views=stat.get("view", 0),
                likes=stat.get("like", 0),
                comments_count=stat.get("reply", 0),
                shares=stat.get("share", 0),
                favorites=stat.get("favorite", 0),
                extra={
                    "rank": v.get("rank", 0),
                    "score": v.get("score", 0),
                    "tname": v.get("tname", ""),
                    "danmaku": stat.get("danmaku", 0),
                    "coin": stat.get("coin", 0),
                },
                api_response=v,
            ))
        return records

    def collect_comments(self, bvid: str, count: int = 50) -> list[RawRecord]:
        """视频评论 — 完整评论文本+元数据，作为子记录"""
        detail = self._get("/x/web-interface/view", {"bvid": bvid})
        if not detail: return []
        aid = detail.get("aid")
        if not aid: return []

        comments, seen = [], set()
        for pn in range(1, (count // 20) + 2):
            data = self._get("/x/v2/reply", {"type": 1, "oid": aid, "pn": pn, "ps": 20, "sort": 2})
            if not data: break
            for r in data.get("replies", []):
                rpid = r.get("rpid", 0)
                if rpid in seen: continue
                seen.add(rpid)
                msg = r.get("content", {}).get("message", "")
                member = r.get("member", {})
                comments.append(make_raw(
                    source="bilibili",
                    record_type="comment",
                    item_id=str(rpid),
                    url=f"https://www.bilibili.com/video/{bvid}#reply{rpid}",
                    body=msg,
                    author_name=member.get("uname", ""),
                    author_id=str(member.get("mid", "")),
                    likes=r.get("like", 0),
                    extra={
                        "parent_bvid": bvid,
                        "parent_aid": aid,
                        "rcount": r.get("rcount", 0),
                        "ctime": r.get("ctime", 0),
                        "member": member,
                    },
                    api_response=r,
                ))
            if len(seen) >= count: break
            self._sleep()
        return comments

    def collect_all(self) -> list[RawRecord]:
        """一键采集"""
        records = self.collect_popular(count=50)
        records.extend(self.collect_ranking())

        # 取前 3 个热门视频的评论
        popular = self.collect_popular(count=3)
        for i, vid in enumerate(popular):
            bvid = vid.item_id
            comments = self.collect_comments(bvid, count=15)
            for c in comments:
                c.extra["parent_title"] = vid.title[:100]
            records.extend(comments)
            if i < len(popular) - 1:
                self._sleep()

        return records
