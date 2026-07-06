"""
experiment.py — Reviews 数据源调研

测试各平台评论数据的可获取性：
1. Amazon 评论页 (via httpx)
2. Alibaba 评论 (已知需要登录)
3. Google 购物/评论
4. 专用 Review 平台 (Trustpilot, G2 等)
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from bs4 import BeautifulSoup

RESULT = {"source": "Reviews Aggregation", "status": "unknown", "findings": []}


def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def test_amazon_reviews():
    """Amazon 产品评论页"""
    asin = "B08FC5ZVR7"
    url = f"https://www.amazon.com/product-reviews/{asin}"
    log(f"Testing Amazon reviews: {url}")
    try:
        with httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True) as c:
            r = c.get(url)
        log(f"Status: {r.status_code}, {len(r.text)} bytes")
        if r.status_code == 200:
            if len(r.text) < 5000:
                log("Blocked — JS verification page")
            elif "review" in r.text.lower():
                log("Page contains review content")
                soup = BeautifulSoup(r.text, "lxml")
                review_blocks = soup.select('[data-hook="review"]')
                if review_blocks:
                    log(f"Found {len(review_blocks)} review blocks!")
                else:
                    log("No review blocks found (may need JS)")
    except Exception as e:
        log(f"Request FAILED: {e}")


def test_trustpilot():
    """Trustpilot — 第三方评论平台"""
    url = "https://www.trustpilot.com/review/www.amazon.com"
    log(f"\nTesting Trustpilot: {url}")
    try:
        with httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True) as c:
            r = c.get(url)
        log(f"Status: {r.status_code}, {len(r.text)} bytes")
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "lxml")
            title = soup.title.string.strip() if soup.title else "no title"
            log(f"Title: {title[:120]}")
            reviews = soup.select('[class*="review"]')
            log(f"Elements with 'review' class: {len(reviews)}")
            if reviews:
                for rev in reviews[:2]:
                    text = rev.get_text(strip=True)[:100]
                    log(f"  Sample: {text}...")
    except Exception as e:
        log(f"Request FAILED: {e}")


def test_google_shopping():
    """Google Shopping 商品评价"""
    url = "https://www.google.com/shopping/product/1"
    log(f"\nTesting Google Shopping...")
    log("  Google Shopping requires complex XHR calls and is heavily JS-dependent")
    log("  Not feasible via plain HTTP — requires browser automation")
    log("  Alternative: Google Shopping API is deprecated")


def test_review_apis():
    """Review API 服务调研"""
    log("\n=== Review API Services ===")
    services = [
        ("Amazon Product Advertising API", "官方API，含评论摘要但非全文", "免费（需Affiliate）", "有限"),
        ("Rainforest API (Amazon)", "第三方，完整评论数据", "$49/mo起", "高"),
        ("Trustpilot API", "官方API，获取商家评论", "免费层可用", "中"),
        ("ReviewMeta", "评论分析工具，有API", "免费", "中（非原始数据）"),
        ("Google Places API", "Google商家评价", "免费层（$200/月额度）", "低（仅本地商家）"),
    ]
    for name, desc, cost, value in services:
        log(f"  {name}: {desc} [{cost}, value: {value}]")


def main():
    print("=" * 60)
    print("Reviews Data Source — Feasibility Test")
    print("=" * 60)

    test_amazon_reviews()
    test_trustpilot()
    test_google_shopping()
    test_review_apis()

    RESULT["status"] = "mixed"
    out = Path(__file__).parent / "result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\nResults saved to {out}")


if __name__ == "__main__":
    main()
