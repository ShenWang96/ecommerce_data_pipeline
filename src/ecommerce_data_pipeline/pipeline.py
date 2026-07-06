"""
PipelineRunner — 中国大陆趋势信号一键采集管道。

按 SOP 六层信号链，并行采集 4 个数据源，合并去重，输出结构化 JSONL。

使用方式:
    python -m ecommerce_data_pipeline.pipeline [--keywords 收纳,宠物,办公] [--output data/signals.jsonl]
"""
import json
import time
from datetime import datetime
from collections import defaultdict
from pathlib import Path
from typing import Optional

from .collectors.bilibili_collector import BilibiliCollector
from .collectors.zhihu_collector import ZhihuCollector
from .collectors.weibo_collector import WeiboCollector
from .collectors.xiaohongshu_collector import XiaohongshuCollector
from .models.signal import TrendSignal, SignalType


class PipelineRunner:
    """
    趋势信号 Pipeline 运行器。
    
    输出结构:
      - 按 Layer (1-6) 分层
      - 每层按 engagement 降序排列
      - 同标题自动去重 (保留 engagement 最高的源)
    """

    def __init__(self, keywords: list[str] | None = None, output_dir: Path | str = "data"):
        self.keywords = keywords or ["收纳", "宠物", "家居", "办公", "健身"]
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def collect_all(self) -> list[TrendSignal]:
        """并行采集所有数据源，合并去重"""
        all_signals = []

        # B站 (无需登录)
        print("[1/4] B站 采集...")
        try:
            with BilibiliCollector() as b:
                b_signals = b.collect_all()
                all_signals.extend(b_signals)
                self._summary(b_signals, "B站")
        except Exception as e:
            print(f"  ✗ B站 error: {e}")

        # 知乎 (部分无登录)
        print("[2/4] 知乎 采集...")
        try:
            z = ZhihuCollector()
            z_signals = z.collect_all()
            all_signals.extend(z_signals)
            self._summary(z_signals, "知乎")
        except Exception as e:
            print(f"  ✗ 知乎 error: {e}")

        # 微博 (需 Cookie)
        print("[3/4] 微博 采集...")
        if WeiboCollector.check_ready():
            try:
                w = WeiboCollector()
                w_signals = w.collect_all()
                all_signals.extend(w_signals)
                self._summary(w_signals, "微博")
            except Exception as e:
                print(f"  ✗ 微博 error: {e}")
        else:
            print("  ⚠ 微博跳过 — 未配置 Cookie")

        # 小红书 (需 Cookie)
        print("[4/4] 小红书 采集...")
        if XiaohongshuCollector.check_ready():
            try:
                x = XiaohongshuCollector()
                x_signals = x.collect_all(self.keywords)
                all_signals.extend(x_signals)
                self._summary(x_signals, "小红书")
            except Exception as e:
                print(f"  ✗ 小红书 error: {e}")
        else:
            print("  ⚠ 小红书跳过 — 未配置 Cookie")

        return all_signals

    def deduplicate(self, signals: list[TrendSignal]) -> list[TrendSignal]:
        """去重: 相同标题保留 engagement 最高的"""
        seen = {}
        for s in signals:
            key = (s.source, s.title[:80])
            if key not in seen or s.engagement > seen[key].engagement:
                seen[key] = s
        return list(seen.values())

    def run(self) -> dict:
        """执行完整 Pipeline"""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        print(f"\n{'='*60}")
        print(f"  China Trend Signal Pipeline — {timestamp}")
        print(f"{'='*60}\n")

        raw = self.collect_all()
        deduped = self.deduplicate(raw)

        # 按 Layer 分组
        by_layer = defaultdict(list)
        by_domain = defaultdict(list)
        by_type = defaultdict(list)

        for s in deduped:
            by_layer[s.layer].append(s)
            if s.domain:
                by_domain[s.domain].append(s)
            by_type[s.signal_type].append(s)

        # 每层按 engagement 排序
        for layer in by_layer:
            by_layer[layer].sort(key=lambda x: x.engagement, reverse=True)

        # 生成报告
        report = {
            "pipeline": "china_trend_signal",
            "timestamp": timestamp,
            "summary": {
                "total_raw": len(raw),
                "total_deduped": len(deduped),
                "sources": get_source_stats(deduped),
                "by_layer": {f"L{lv}": len(ss) for lv, ss in sorted(by_layer.items())},
                "by_signal_type": {st: len(ss) for st, ss in sorted(by_type.items())},
                "top_domains": sorted(
                    [(d, len(ss)) for d, ss in by_domain.items() if d != "其他"],
                    key=lambda x: x[1], reverse=True
                )[:10],
            },
            "signals": [s.to_dict() for s in deduped],
        }

        # 写入文件
        jsonl_path = self.output_dir / f"signals_{timestamp}.jsonl"
        with open(jsonl_path, "w") as f:
            for s in deduped:
                f.write(json.dumps(s.to_dict(), ensure_ascii=False) + "\n")

        report_path = self.output_dir / f"report_{timestamp}.json"
        with open(report_path, "w") as f:
            # report without signals list for summary
            summary = {k: v for k, v in report.items() if k != "signals"}
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*60}")
        print(f"  Pipeline 完成!")
        print(f"  原始: {len(raw)} → 去重: {len(deduped)}")
        print(f"  JSONL: {jsonl_path}")
        print(f"  报告:  {report_path}")
        print(f"{'='*60}")

        # Auto-generate HTML report
        try:
            from scripts.generate_report import build_report as gen_html
            html_path = jsonl_path.with_suffix('.html')
            html_path.write_text(gen_html(deduped))
            print(f"  HTML:   {html_path}")
        except Exception:
            pass

        return report

    def _summary(self, signals: list[TrendSignal], name: str):
        """打印单源采集摘要"""
        layer_counts = defaultdict(int)
        type_counts = defaultdict(int)
        for s in signals:
            layer_counts[s.layer] += 1
            type_counts[s.signal_type] += 1
        layers = ", ".join(f"L{lv}:{c}" for lv, c in sorted(layer_counts.items()))
        types = ", ".join(f"{st}:{c}" for st, c in sorted(type_counts.items()))
        print(f"  ✓ {name}: {len(signals)} 条 [{layers}]")


def get_source_stats(signals: list[TrendSignal]) -> dict:
    stats = defaultdict(int)
    for s in signals:
        stats[s.source] += 1
    return dict(stats)
