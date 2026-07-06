"""
RawPipeline — 原始数据落地管道。

两阶段架构:
  Stage 1 (当前): RawCollector → data/raw/{source}_{timestamp}.jsonl
    - 完整 HTML / API 响应
    - 所有图片 URL / 视频 URL
    - 原始链接 (可回放)
    - 零分类/零解读

  Stage 2 (未来): SignalExtractor → data/signals/{timestamp}.jsonl
    - 读取 data/raw/*.jsonl
    - 信号分类 + 关键词提取 + 领域识别
    - 去重合并
    - 产出 TrendSignal

使用:
    python -m ecommerce_data_pipeline.raw_pipeline [--keywords 收纳,宠物]
"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from .collectors.bilibili_raw_collector import BilibiliRawCollector
from .collectors.zhihu_raw_collector import ZhihuRawCollector
from .collectors.weibo_raw_collector import WeiboRawCollector
from .collectors.xiaohongshu_raw_collector import XiaohongshuRawCollector
from .models.raw_record import RawRecord


class RawPipeline:
    """原始数据落地管道 — 只采集，不解读"""

    def __init__(self, keywords: list[str] | None = None, output_dir: Path | str = "data/raw"):
        self.keywords = keywords or []
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def collect_all(self) -> list[RawRecord]:
        all_records = []
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

        # B站 (无需登录，httpx API)
        print("[1/4] B站 原始数据采集...")
        try:
            with BilibiliRawCollector() as b:
                records = b.collect_all()
                all_records.extend(records)
                self._save(records, f"bilibili_{timestamp}.jsonl")
                self._summary(records, "B站")
        except Exception as e:
            print(f"  ✗ B站 error: {e}")

        # 知乎 (部分无登录 + Cookie 热榜)
        print("[2/4] 知乎 原始数据采集...")
        try:
            z = ZhihuRawCollector()
            records = z.collect_all()
            all_records.extend(records)
            self._save(records, f"zhihu_{timestamp}.jsonl")
            self._summary(records, "知乎")
        except Exception as e:
            print(f"  ✗ 知乎 error: {e}")

        # 微博 (需 Cookie)
        print("[3/4] 微博 原始数据采集...")
        if WeiboRawCollector.check_ready():
            try:
                w = WeiboRawCollector()
                records = w.collect_all()
                all_records.extend(records)
                self._save(records, f"weibo_{timestamp}.jsonl")
                self._summary(records, "微博")
            except Exception as e:
                print(f"  ✗ 微博 error: {e}")
        else:
            print("  ⚠ 微博跳过 — 未配置 Cookie")

        # 小红书 (需 Cookie + Playwright) — 发现页热榜 + 热搜关键词
        print("[4/4] 小红书 原始数据采集...")
        if XiaohongshuRawCollector.check_ready():
            try:
                x = XiaohongshuRawCollector()
                records = x.collect_all()
                all_records.extend(records)
                self._save(records, f"xiaohongshu_{timestamp}.jsonl")
                self._summary(records, "小红书")
            except Exception as e:
                print(f"  ✗ 小红书 error: {e}")
        else:
            print("  ⚠ 小红书跳过 — 未配置 Cookie")

        return all_records

    def _save(self, records: list[RawRecord], filename: str):
        path = self.output_dir / filename
        with open(path, "w") as f:
            for r in records:
                f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
        print(f"  → {path}")

    def _summary(self, records: list[RawRecord], name: str):
        from collections import Counter
        types = Counter(r.record_type for r in records)
        type_str = ", ".join(f"{t}:{c}" for t, c in types.most_common())
        print(f"  ✓ {name}: {len(records)} 条 [{type_str}]")

    def run(self) -> dict:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        print(f"\n{'='*60}")
        print(f"  Raw Data Pipeline — {timestamp}")
        print(f"  阶段 1: 原始数据落地")
        print(f"{'='*60}\n")

        all_records = self.collect_all()

        # 写入合并文件
        merged_path = self.output_dir / f"all_{timestamp}.jsonl"
        with open(merged_path, "w") as f:
            for r in all_records:
                f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")

        total_images = sum(len(r.images) for r in all_records)
        total_html = sum(1 for r in all_records if r.html_snapshot)

        print(f"\n{'='*60}")
        print(f"  Stage 1 完成!")
        print(f"  总记录: {len(all_records)}")
        print(f"  图片URL: {total_images}")
        print(f"  HTML快照: {total_html}")
        print(f"  合并文件: {merged_path}")
        print(f"{'='*60}")
        print(f"\n  下一步: 运行 Stage 2 Signal Extraction Pipeline")
        print(f"  输入: data/raw/*.jsonl")
        print(f"  输出: data/signals/*.jsonl + HTML 报告")
        print(f"{'='*60}")

        return {
            "pipeline": "raw_data_collection",
            "timestamp": timestamp,
            "total_records": len(all_records),
            "total_image_urls": total_images,
            "total_html_snapshots": total_html,
            "output_dir": str(self.output_dir),
        }
