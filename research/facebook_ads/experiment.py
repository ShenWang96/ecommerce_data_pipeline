"""
experiment.py — Facebook Ads Library 数据源可行性验证

Meta Ad Library API: https://www.facebook.com/ads/library/api/
免费使用，但需要 Facebook App + Access Token
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx

RESULT = {"source": "Facebook Ads Library", "status": "unknown", "findings": []}


def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)


def test_ad_library_unauthenticated():
    """Test 1: 无认证访问 Ad Library 网页版"""
    log("Testing Facebook Ad Library web page...")
    h = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    }
    try:
        with httpx.Client(headers=h, timeout=20, follow_redirects=True) as c:
            r = c.get("https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=US&q=bluetooth%20speaker&search_type=keyword_unordered&media_type=all")
        code = r.status_code
        log(f"Ad Library page: {code}, {len(r.text)} bytes")

        if code == 200:
            if len(r.text) < 5000:
                log("Small response — likely requires JS/login")
            elif "login" in r.text[:3000].lower():
                log("Login wall detected")
            else:
                log("Got substantial content")
    except Exception as e:
        log(f"Request FAILED: {e}")


def test_ad_library_api_info():
    """Test 2: 了解 API 申请流程"""
    log("\n=== Meta Ad Library API Info ===")
    info = """
Meta Ad Library API:
- URL: https://www.facebook.com/ads/library/api/
- 需要: Facebook App + Access Token
- 免费: 是的（有 rate limit）
- 能力: 
  - 按关键词搜索广告
  - 按广告主搜索（Page ID）
  - 获取广告创意、文案、投放时间
  - 获取广告花费估算（政治类广告）
- 限制:
  - 请求频率限制
  - 部分数据仅对政治类广告开放
  - 需要实名认证的 Facebook 开发者账号
- 申请流程:
  1. 创建 Facebook App（developers.facebook.com）
  2. 添加 "Ads Library API" 权限
  3. 提交 App Review（需身份验证）
  4. 获取 Access Token
"""
    for line in info.strip().split("\n"):
        log(line)

    log("\n  Verdict: 有官方 API，需要准备 Facebook App 和开发者账号")


def test_alternative_approaches():
    """Test 3: 其他广告数据源"""
    log("\n=== Alternative Ad Intelligence Sources ===")

    sources = [
        ("TikTok Ads Library", "https://library.tiktok.com/ads/", "TikTok 官方广告库，免费", "中"),
        ("Google Ads Transparency", "https://adstransparency.google.com/", "Google 广告透明度中心", "低"),
        ("AdSpy / PowerAdSpy", "付费 SaaS", "第三方竞品广告分析工具", "高($149/mo)"),
        ("BigSpy", "https://bigspy.com/", "免费增值模式，社媒广告数据库", "低（有免费层）"),
    ]

    for name, url, desc, cost in sources:
        log(f"  {name}: {desc} [{cost}]")


def main():
    print("=" * 60)
    print("Facebook Ads Library — Feasibility Test")
    print("=" * 60)

    test_ad_library_unauthenticated()
    test_ad_library_api_info()
    test_alternative_approaches()

    RESULT["status"] = "needs_dev_account"
    out = Path(__file__).parent / "result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\nResults saved to {out}")


if __name__ == "__main__":
    main()
