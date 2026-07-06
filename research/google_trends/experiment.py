"""
experiment.py — Google Trends 数据源可行性验证

目标：用最小代码确认 pytrends 能不能拉数据、能拉到什么粒度、有什么限制。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
import json
import time
from datetime import datetime, timedelta

from pytrends.request import TrendReq
import pandas as pd

RESULT = {"source": "Google Trends", "status": "unknown", "findings": []}


def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)


def test_basic_connection():
    """Test 1: 能否连接到 Google Trends"""
    log("Connecting to Google Trends...")
    try:
        pytrend = TrendReq(hl="en-US", tz=360, timeout=10)
        log("Connection OK (en-US, tz=360)")
        return pytrend
    except Exception as e:
        log(f"Connection FAILED: {e}")
        return None


def test_interest_over_time(pytrend):
    """Test 2: 按时间获取搜索热度"""
    log("Testing interest_over_time for keyword 'air fryer'...")
    try:
        pytrend.build_payload(kw_list=["air fryer"], timeframe="today 3-m", geo="US")
        df = pytrend.interest_over_time()
        if df is not None and not df.empty:
            log(f"OK — got {len(df)} rows, columns: {list(df.columns)}")
            log(f"  Sample:\n{df.head(3).to_string()}")
            return df
        else:
            log("Empty result — possible rate limit or no data")
            return None
    except Exception as e:
        log(f"interest_over_time FAILED: {e}")
        return None


def test_related_queries(pytrend):
    """Test 3: 获取相关搜索词"""
    log("Testing related_queries for 'air fryer'...")
    try:
        df = pytrend.related_queries()
        if df:
            top = df["air fryer"]["top"]
            rising = df["air fryer"]["rising"]
            log(f"OK — top queries: {len(top) if top is not None else 0} rows")
            if top is not None and not top.empty:
                log(f"  Top 5:\n{top.head(5).to_string()}")
            log(
                f"  Rising queries: {len(rising) if rising is not None else 0} rows"
            )
            if rising is not None and not rising.empty:
                log(f"  Rising 5:\n{rising.head(5).to_string()}")
        else:
            log("related_queries returned empty")
    except Exception as e:
        log(f"related_queries FAILED: {e}")


def test_related_topics(pytrend):
    """Test 4: 获取相关话题"""
    log("Testing related_topics for 'air fryer'...")
    try:
        df = pytrend.related_topics()
        if df:
            for k in df:
                for t in ("top", "rising"):
                    sub = df[k][t]
                    if sub is not None and not sub.empty:
                        log(
                            f"  {k} {t}: {len(sub)} entries, cols: {list(sub.columns)}"
                        )
                        log(f"  Top 3:\n{sub.head(3).to_string()}")
        else:
            log("related_topics returned empty")
    except Exception as e:
        log(f"related_topics FAILED: {e}")


def test_multiple_keywords(pytrend):
    """Test 5: 多关键词对比搜索"""
    log("Testing multi-keyword: 'bluetooth speaker', 'wireless earbuds', 'smart watch'...")
    try:
        pytrend.build_payload(
            kw_list=["bluetooth speaker", "wireless earbuds", "smart watch"],
            timeframe="today 3-m",
            geo="US",
        )
        df = pytrend.interest_over_time()
        if df is not None and not df.empty:
            log(f"OK — got {len(df)} rows for 3 keywords")
            log(f"  Last 5 rows:\n{df.tail(5).to_string()}")
        else:
            log("Empty result")
    except Exception as e:
        log(f"Multi-keyword FAILED: {e}")


def test_regional_interest(pytrend):
    """Test 6: 按区域获取热度"""
    log("Testing interest_by_region for 'air fryer'...")
    try:
        pytrend.build_payload(kw_list=["air fryer"], timeframe="today 3-m", geo="US")
        df = pytrend.interest_by_region(resolution="REGION", inc_low_vol=True)
        if df is not None and not df.empty:
            log(f"OK — got {len(df)} regions with data")
            log(f"  Top 5 regions:\n{df.head(5).to_string()}")
        else:
            log("Empty result")
    except Exception as e:
        log(f"interest_by_region FAILED: {e}")


def test_daily_resolution(pytrend):
    """Test 7: 尝试获取日粒度数据（需更短时间窗）"""
    log("Testing daily-resolution data for 'air fryer' (last 7 days)...")
    try:
        end = datetime.now()
        start = end - timedelta(days=7)
        timeframe = f"{start.strftime('%Y-%m-%d')} {end.strftime('%Y-%m-%d')}"
        log(f"  Timeframe: {timeframe}")
        pytrend.build_payload(kw_list=["air fryer"], timeframe=timeframe, geo="US")
        df = pytrend.interest_over_time()
        if df is not None and not df.empty:
            log(f"OK — got {len(df)} daily data points")
            log(f"  All rows:\n{df.to_string()}")
        else:
            log("Empty result")
    except Exception as e:
        log(f"Daily resolution FAILED: {e}")


def test_rate_limiting(pytrend):
    """Test 8: 测试限频 — 连续多次请求"""
    log("Testing rate limiting: 5 rapid requests...")
    success = 0
    fail = 0
    for i in range(5):
        try:
            pytrend.build_payload(kw_list=[f"test keyword {i}"], timeframe="today 3-m")
            pytrend.interest_over_time()
            success += 1
            log(f"  Request {i+1}: OK")
        except Exception as e:
            fail += 1
            log(f"  Request {i+1}: FAILED — {str(e)[:80]}")
        time.sleep(2)
    log(f"Rate limiting test: {success} OK, {fail} FAILED out of 5")


def main():
    print("=" * 60)
    print("Google Trends Data Source — Feasibility Test")
    print("=" * 60)

    pytrend = test_basic_connection()
    if pytrend is None:
        RESULT["status"] = "failed"
        _save()
        return

    test_interest_over_time(pytrend)
    time.sleep(3)

    test_related_queries(pytrend)
    time.sleep(3)

    test_related_topics(pytrend)
    time.sleep(3)

    test_multiple_keywords(pytrend)
    time.sleep(3)

    test_regional_interest(pytrend)
    time.sleep(3)

    test_daily_resolution(pytrend)
    time.sleep(3)

    test_rate_limiting(pytrend)

    RESULT["status"] = "success"
    _save()


def _save():
    out = Path(__file__).parent / "result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\nResults saved to {out}")


if __name__ == "__main__":
    main()
