"""
TrendSignal — 中国大陆电商趋势信号模型，对齐 SOP 六层信号链。

信号链:
  Layer 1: 需求萌芽 (Pain & Needs)
    pain_point     — 问题描述 (久坐腰疼、夏天养猫味道大)
    seeking_help   — 求推荐/求替代/求避坑 (有没有更好的XX)
    complaint      — 吐槽/后悔 (踩雷、后悔买)
  
  Layer 2: 理念形成 (Lifestyle & Concept)
    lifestyle      — 新生活方式 (露营、极简、CityWalk)
    concept        — 新兴概念/理念 (AI办公、宠物拟人化)
  
  Layer 3: 内容传播 (Content Amplification)
    trending       — 上热榜/热搜 (微博热搜、B站热门)
    viral          — 爆款内容 (高播放/高互动)
  
  Layer 4: 大众关注 (Attention) — 百度指数/微信指数 (待实现)
    search_rising  — 搜索量上升
  
  Layer 5: 商业验证 (Commercial Validation) — 淘宝/京东 (待实现)
    product_emerging — 新品出现
    sales_growing    — 销量增长
  
  Layer 6: 供应扩张 (Supply Expansion) — 1688 (待实现)
    supply_growing   — 供应商增加/同款增多
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


# ─── 信号类型常量 (对齐 SOP) ───

class SignalType:
    L1_PAIN_POINT = "pain_point"
    L1_SEEKING_HELP = "seeking_help"
    L1_COMPLAINT = "complaint"
    L2_LIFESTYLE = "lifestyle"
    L2_CONCEPT = "concept"
    L3_TRENDING = "trending"
    L3_VIRAL = "viral"
    L4_SEARCH_RISING = "search_rising"
    L5_PRODUCT_EMERGING = "product_emerging"
    L5_SALES_GROWING = "sales_growing"
    L6_SUPPLY_GROWING = "supply_growing"

    @classmethod
    def layer_of(cls, signal_type: str) -> int:
        return {
            cls.L1_PAIN_POINT: 1, cls.L1_SEEKING_HELP: 1, cls.L1_COMPLAINT: 1,
            cls.L2_LIFESTYLE: 2, cls.L2_CONCEPT: 2,
            cls.L3_TRENDING: 3, cls.L3_VIRAL: 3,
            cls.L4_SEARCH_RISING: 4,
            cls.L5_PRODUCT_EMERGING: 5, cls.L5_SALES_GROWING: 5,
            cls.L6_SUPPLY_GROWING: 6,
        }.get(signal_type, 0)


# ─── 消费领域分类 ───

CONSUMER_DOMAINS = [
    "家居收纳", "宠物用品", "数码3C", "办公效率",
    "美妆护肤", "健康养生", "食品饮料", "出行旅游",
    "母婴育儿", "健身运动", "服饰穿搭", "汽车用品",
    "厨房用品", "清洁用品", "个护仪器", "户外露营",
    "智能家居", "教育学习", "娱乐玩具", "其他",
]


@dataclass
class TrendSignal:
    """
    SOP 对齐的趋势信号。

    Fields:
        source:         数据来源 (bilibili/zhihu/weibo/xiaohongshu)
        signal_type:    信号类型 (SignalType 常量)
        layer:          信号层级 (1-6)
        domain:         消费领域 (家居收纳/宠物用品/数码3C...)
        keywords:       提取的关键词/概念
        title:          原始标题/问题
        content:        正文/描述内容
        url:            原始链接
        author:         作者名
        engagement:     互动量 (点赞+评论+收藏+转发 总和)
        metrics:        标准化指标 {views, likes, comments, shares, favorites}
        rank:           排行榜位置 (Layer 3, 可选)
        heat_score:     热度评分 (Layer 3, 可选)
        scraped_at:     采集时间
        raw_stats:      原始平台的完整统计 (调试用)
    """
    source: str
    signal_type: str
    layer: int
    domain: str
    keywords: list[str]
    title: str
    content: str
    url: str
    author: str
    engagement: int
    metrics: dict
    rank: Optional[int] = None
    heat_score: Optional[float] = None
    scraped_at: datetime = field(default_factory=datetime.utcnow)
    raw_stats: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["scraped_at"] = d["scraped_at"].isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "TrendSignal":
        if "scraped_at" in d and isinstance(d["scraped_at"], str):
            d["scraped_at"] = datetime.fromisoformat(d["scraped_at"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ─── 信号工厂 ───

def make_signal(
    source: str,
    signal_type: str,
    title: str,
    *,
    content: str = "",
    url: str = "",
    author: str = "",
    keywords: list[str] | None = None,
    domain: str = "其他",
    metrics: dict | None = None,
    rank: int | None = None,
    heat_score: float | None = None,
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    favorites: int = 0,
    views: int = 0,
    raw_stats: dict | None = None,
) -> TrendSignal:
    m = metrics or {}
    engagement = (
        m.get("likes", likes)
        + m.get("comments", comments)
        + m.get("shares", shares)
        + m.get("favorites", favorites)
    )
    if engagement == 0:
        engagement = likes + comments + shares + favorites

    return TrendSignal(
        source=source,
        signal_type=signal_type,
        layer=SignalType.layer_of(signal_type),
        domain=domain,
        keywords=keywords or [],
        title=title[:200],
        content=content[:1000],
        url=url,
        author=author,
        engagement=engagement,
        metrics={
            "views": m.get("views", views),
            "likes": m.get("likes", likes),
            "comments": m.get("comments", comments),
            "shares": m.get("shares", shares),
            "favorites": m.get("favorites", favorites),
        },
        rank=rank,
        heat_score=heat_score,
        raw_stats=raw_stats or {},
    )
