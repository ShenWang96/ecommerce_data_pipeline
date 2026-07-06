"""
experiment.py — TikTok 数据源可行性验证

测试:
1. 非官方 TikTokApi 库是否能连上
2. 直接 HTTP 请求 TikTok 搜索/趋势页
3. 评估可行性
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from bs4 import BeautifulSoup

RESULT = {"source": "TikTok", "status": "unknown", "findings": []}


def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)


def test_tiktok_api():
    """Test 1: TikTokApi 非官方库"""
    log("Testing TikTokApi library...")
    try:
        from TikTokApi import TikTokApi

        log("TikTokApi imported OK")
        log(f"Version: {TikTokApi.__version__ if hasattr(TikTokApi, '__version__') else 'unknown'}")

        # Try to create instance
        # Note: many TikTokApi methods require ms_token from browser
        api = TikTokApi()
        log("TikTokApi instance created")
        return api
    except ImportError:
        log("TikTokApi not installed — would need: pip install TikTokApi")
        return None
    except Exception as e:
        log(f"TikTokApi init FAILED: {e}")
        return None


def test_tiktok_trending():
    """Test 2: 尝试无认证获取 trending"""
    log("Testing TikTok trending page...")
    h = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }
    try:
        with httpx.Client(headers=h, timeout=20, follow_redirects=True) as c:
            r = c.get("https://www.tiktok.com/trending")
        code = r.status_code
        log(f"Trending page: {code}, {len(r.text)} bytes")
        if code == 200:
            if "captcha" in r.text.lower():
                log("Captcha on trending page")
            elif len(r.text) > 10000:
                log("Got substantial content — may contain data")
            else:
                log(f"Small response — likely JS-rendered SPA")
        else:
            log(f"Status {code}")
    except Exception as e:
        log(f"Request FAILED: {e}")


def test_tiktok_search():
    """Test 3: TikTok 搜索页"""
    log("Testing TikTok search page...")
    h = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }
    try:
        with httpx.Client(headers=h, timeout=20, follow_redirects=True) as c:
            r = c.get("https://www.tiktok.com/search?q=bluetooth%20speaker")
        code = r.status_code
        log(f"Search page: {code}, {len(r.text)} bytes")
        if code == 200:
            if len(r.text) > 10000:
                log("Got substantial content")
                soup = BeautifulSoup(r.text, "lxml")
                title = soup.title.string if soup.title else "no title"
                log(f"Title: {title[:120]}")
            else:
                log(f"Small response — JS-rendered SPA (expected)")
    except Exception as e:
        log(f"Request FAILED: {e}")


def test_tiktok_hashtag():
    """Test 4: TikTok hashtag page (常用来做趋势发现)"""
    log("Testing TikTok hashtag page...")
    h = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }
    try:
        with httpx.Client(headers=h, timeout=20, follow_redirects=True) as c:
            r = c.get("https://www.tiktok.com/tag/bluetoothspeaker")
        code = r.status_code
        log(f"Hashtag page: {code}, {len(r.text)} bytes")
    except Exception as e:
        log(f"Request FAILED: {e}")


def test_tiktok_api_v2():
    """Test 5: 试 TikTok 非官方 API 接口 (RapidAPI 风格)"""
    # Many third-party APIs exist on RapidAPI
    log("Testing alternative: tiktok-scraper approach...")
    log("  Note: Most unofficial TikTok APIs either:")
    log("    a) Require ms_token from TikTok mobile app (hard to get)")
    log("    b) Are paid services (RapidAPI ~$30-100/mo)")
    log("    c) Use TikTok's internal API but get blocked quickly")
    log("  Recommendation: TikTokApi + Playwright = most viable free approach")


def main():
    print("=" * 60)
    print("TikTok Data Source — Feasibility Test")
    print("=" * 60)

    api = test_tiktok_api()
    test_tiktok_trending()
    test_tiktok_search()
    test_tiktok_hashtag()
    test_tiktok_api_v2()

    RESULT["status"] = "needs_browser"
    out = Path(__file__).parent / "result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\nResults saved to {out}")


if __name__ == "__main__":
    main()
