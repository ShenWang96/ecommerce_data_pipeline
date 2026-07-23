#!/usr/bin/env python3
"""
Pipeline 定时采集脚本 — 供 cron 调用。

执行 8 源全量采集，输出摘要 JSON + JSONL 数据。

用法:
    python3 scripts/scheduled_collect.py [--output-dir data/raw]

输出:
    1. data/raw/{source}_{timestamp}.jsonl — 各源原始数据
    2. data/raw/all_{timestamp}.jsonl — 合并文件
    3. stdout — 摘要 (JSON 格式，供 cron agent 解析)
"""
import sys
import os
import json
from pathlib import Path

# 环境变量
os.environ.setdefault("LD_LIBRARY_PATH", os.path.expanduser("~/.local/playwright-libs"))
os.environ.setdefault("PYTHONPATH", str(Path(__file__).parent.parent / "src"))

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ecommerce_data_pipeline.raw_pipeline import RawPipeline


def main():
    pipeline = RawPipeline()
    result = pipeline.run()

    # 输出摘要到 stdout（cron agent 可解析）
    summary = {
        "timestamp": result["timestamp"],
        "total_records": result["total_records"],
        "total_image_urls": result["total_image_urls"],
        "output_dir": result["output_dir"],
        "status": "ok" if result["total_records"] > 100 else "warning",
        "message": f"采集完成: {result['total_records']} 条",
    }
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
