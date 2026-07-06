"""B站 Collector 快速验证"""
import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from ecommerce_data_pipeline.collectors.bilibili_collector import BilibiliCollector

with BilibiliCollector() as b:
    print("=== 热门 ===")
    popular = b.collect_popular(count=5)
    print(f"  获得 {len(popular)} 条")
    for p in popular:
        print(f"  [{p.tags[0] if p.tags else '?'}] {p.title[:60]} 播放:{p.stats.get('view',0)}")
        print(f"    UP: {p.author} 点赞:{p.stats.get('like',0)}")

    print("\n=== 排行榜 ===")
    ranking = b.collect_ranking()
    print(f"  获得 {len(ranking)} 条")
    for r in ranking[:5]:
        print(f"  #{r.stats.get('rank','?')} [{', '.join(r.tags) if r.tags else '?'}] {r.title[:60]}")

    print("\n=== 评论 (Layer 1 需求信号) ===")
    comments = b.collect_comments_for_popular(video_count=3, comments_per_video=5)
    print(f"  获得 {len(comments)} 条评论")
    for c in comments[:10]:
        tag = c.tags[0][:30] if c.tags else "?"
        print(f"  [{c.author}] {c.description[:80]}  👍{c.stats.get('like',0)}  ({tag})")

    # Demo: convert to jsonl
    project = Path(__file__).parent.parent.parent.parent
    out_dir = project / "data"
    out_dir.mkdir(exist_ok=True)
    all_signals = popular + ranking + comments
    with open(out_dir / "bilibili_signals.jsonl", "w") as f:
        for s in all_signals:
            f.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")
    print(f"\n共 {len(all_signals)} 条信号写入 data/bilibili_signals.jsonl")
