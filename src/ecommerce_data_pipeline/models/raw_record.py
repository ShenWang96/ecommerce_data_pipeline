"""
RawRecord — 原始数据落地模型。

设计原则:
  1. 零信息损失 — 保存平台返回的原始 HTML / JSON / 媒体 URL
  2. 不做分类/解读 — 那是 Signal Extraction Pipeline 的事
  3. 可回放 — 用原始链接可以随时重新抓取验证

存储: data/raw/{source}_{timestamp}.jsonl
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class RawRecord:
    """
    一条原始采集记录。字段保持最小抽象，尽可能贴近原始数据形态。
    
    语义字段 (所有源都有):
      source:         平台标识 (bilibili/zhihu/weibo/xiaohongshu)
      record_type:    记录类型 (video/question/topic/note/comment)
      item_id:        平台内唯一标识 (bvid/qid/note_id...)
      url:            原始链接 (可回放访问)
      scraped_at:     采集时间
    
    内容字段 (按平台不同):
      title:          标题
      body:           正文/描述/问题详情
      author_name:    作者/UP主/博主名
      author_id:      作者唯一ID
    
    媒体 (零信息损失 — 保存全部):
      images:         图片URL列表 (封面图、插图、笔记配图)
      videos:         视频URL列表
      cover_url:      封面图URL
    
    互动数据 (原始数值):
      metrics:        {views, likes, comments, shares, favorites}
    
    原始数据 (完整回放):
      html_snapshot:  页面HTML快照 (Playwright源保存)
      api_response:   原始API JSON响应 (API源保存)
      extra:          平台特有的其他字段
    
    嵌套数据:
      comments:       子记录列表 (评论/回复，同格式)
    """
    source: str
    record_type: str
    item_id: str
    url: str

    title: str = ""
    body: str = ""
    author_name: str = ""
    author_id: str = ""

    images: list[str] = field(default_factory=list)
    videos: list[str] = field(default_factory=list)
    cover_url: str = ""

    metrics: dict = field(default_factory=lambda: {
        "views": 0, "likes": 0, "comments": 0, "shares": 0, "favorites": 0,
    })

    html_snapshot: str = ""
    api_response: dict | None = None
    extra: dict = field(default_factory=dict)

    comments: list["RawRecord"] = field(default_factory=list)

    scraped_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["scraped_at"] = d["scraped_at"].isoformat()
        d["comments"] = [c.to_dict() for c in (self.comments or [])]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "RawRecord":
        d = dict(d)
        if "scraped_at" in d and isinstance(d["scraped_at"], str):
            d["scraped_at"] = datetime.fromisoformat(d["scraped_at"])
        if "comments" in d and isinstance(d["comments"], list):
            d["comments"] = [cls.from_dict(c) for c in d["comments"]]
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


def make_raw(
    source: str,
    record_type: str,
    item_id: str,
    url: str,
    *,
    title: str = "",
    body: str = "",
    author_name: str = "",
    author_id: str = "",
    images: list[str] | None = None,
    videos: list[str] | None = None,
    cover_url: str = "",
    views: int = 0,
    likes: int = 0,
    comments_count: int = 0,
    shares: int = 0,
    favorites: int = 0,
    html_snapshot: str = "",
    api_response: dict | None = None,
    extra: dict | None = None,
    comments: list["RawRecord"] | None = None,
) -> RawRecord:
    return RawRecord(
        source=source,
        record_type=record_type,
        item_id=item_id,
        url=url,
        title=title,
        body=body,
        author_name=author_name,
        author_id=author_id,
        images=images or [],
        videos=videos or [],
        cover_url=cover_url,
        metrics={
            "views": views,
            "likes": likes,
            "comments": comments_count,
            "shares": shares,
            "favorites": favorites,
        },
        html_snapshot=html_snapshot,
        api_response=api_response,
        extra=extra or {},
        comments=comments or [],
    )
