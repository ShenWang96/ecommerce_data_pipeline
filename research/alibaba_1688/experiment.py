"""
experiment.py — 1688 / Alibaba 数据源可行性验证

测试:
1. 1688.com 搜索页 — 淘宝系，登录墙/验证码
2. Alibaba.com 国际站 — 反爬程度
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from bs4 import BeautifulSoup

RESULT = {"source": "1688 / Alibaba", "status": "unknown", "findings": []}


def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def test_1688_search():
    """Test 1: 1688.com 搜索页"""
    url = "https://s.1688.com/selloffer/offer_search.htm?keywords=%C0%B6%D1%C0%D2%F4%CF%E4"
    log(f"1688 search URL: {url}")

    h = HEADERS.copy()
    h["Referer"] = "https://www.1688.com/"

    try:
        with httpx.Client(headers=h, timeout=20, follow_redirects=True) as c:
            r = c.get(url)
        code = r.status_code
        log(f"Status: {code}, Content-Length: {len(r.text)}")

        if code == 200:
            soup = BeautifulSoup(r.text, "lxml")
            title = soup.title.string.strip() if soup.title else "no title"
            log(f"Page title: {title[:120]}")

            # Check login wall
            if "login" in r.text[:3000].lower() or "请登录" in r.text[:3000]:
                log("WARNING: Login wall detected!")

            # Check captcha
            text_lower = r.text[:5000].lower()
            if "captcha" in text_lower or "验证码" in r.text[:5000]:
                log("WARNING: Captcha detected!")
            if "人机验证" in r.text[:5000] or "滑块" in r.text[:5000]:
                log("WARNING: Slider verification detected!")

            # Check if we got product data
            if "offer" in text_lower and "price" in text_lower:
                log("Page contains offer/price keywords — looks like product data")

            # Try different selectors for 1688 product cards
            _find_1688_products(soup)

        elif code in (302, 301):
            log(f"Redirect to: {r.headers.get('Location', 'unknown')}")
        elif code == 403:
            log("403 Forbidden — blocked")
    except Exception as e:
        log(f"Request FAILED: {e}")


def _find_1688_products(soup):
    selectors = [
        ".offer-list-item-wrap",
        ".space-offer-card",
        '[class*="offer"][class*="item"]',
        ".sm-offer-item",
        ".offer_item",
        ".list-item",
    ]
    found = False
    for sel in selectors:
        items = soup.select(sel)
        if items:
            log(f"Found {len(items)} items with '{sel}'")
            found = True
            for i, item in enumerate(items[:3]):
                title_el = item.select_one("[title]") or item.select_one(
                    "a[title]"
                )
                price_el = item.select_one(
                    '[class*="price"]'
                ) or item.select_one("em")
                title = (
                    title_el.get("title", title_el.text.strip())[:60]
                    if title_el
                    else "N/A"
                )
                price = price_el.text.strip() if price_el else "N/A"
                log(f"  [{i+1}] {title} | Price: {price}")
            break

    if not found:
        log("No product cards found with known selectors — checking raw content...")
        text = soup.get_text()
        # Show first 300 meaningful chars
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        log(f"  First lines: {' | '.join(lines[:5])[:200]}")


def test_alibaba_search():
    """Test 2: Alibaba.com 国际站"""
    url = "https://www.alibaba.com/trade/search?SearchText=bluetooth+speaker"
    log(f"\nAlibaba.com URL: {url}")

    h = HEADERS.copy()
    h["Accept-Language"] = "en-US,en;q=0.9"

    try:
        with httpx.Client(headers=h, timeout=20, follow_redirects=True) as c:
            r = c.get(url)
        code = r.status_code
        log(f"Status: {code}, Content-Length: {len(r.text)}")

        if code == 200:
            soup = BeautifulSoup(r.text, "lxml")
            title = soup.title.string.strip() if soup.title else "no title"
            log(f"Page title: {title[:120]}")

            if "captcha" in r.text.lower():
                log("WARNING: Captcha detected!")

            # Try product selectors
            _find_alibaba_products(soup)
    except Exception as e:
        log(f"Request FAILED: {e}")


def _find_alibaba_products(soup):
    selectors = [
        ".search-card-e-container",
        '[class*="search-card"]',
        ".fy23-search-card",
        ".traffic-card",
        '[class*="product"][class*="card"]',
    ]
    found = False
    for sel in selectors:
        items = soup.select(sel)
        if items:
            log(f"Found {len(items)} items with '{sel}'")
            found = True
            for i, item in enumerate(items[:3]):
                title_el = item.select_one("h2") or item.select_one(
                    '[class*="title"]'
                )
                price_el = item.select_one('[class*="price"]')
                moq_el = item.select_one('[class*="moq"]')
                supplier_el = item.select_one('[class*="supplier"]')

                title = title_el.text.strip()[:60] if title_el else "N/A"
                price = price_el.text.strip() if price_el else "N/A"
                moq = moq_el.text.strip() if moq_el else "N/A"
                supplier = supplier_el.text.strip() if supplier_el else "N/A"
                log(f"  [{i+1}] {title} | {price} | MOQ: {moq} | {supplier}")
            break

    if not found:
        log("No products found — checking raw content snippet...")
        text = soup.get_text()
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        log(f"  First lines: {' | '.join(lines[:5])[:200]}")


def test_1688_api_endpoint():
    """Test 3: 试 1688 的 API 端点"""
    url = "https://h5api.m.1688.com/h5/mtop.1688.offer.search/1.0/?jsv=2.4.0"
    log(f"\n1688 API endpoint: {url[:80]}...")

    h = HEADERS.copy()
    h["Referer"] = "https://m.1688.com/"

    try:
        with httpx.Client(headers=h, timeout=20) as c:
            r = c.get(url)
        log(f"Status: {code if (code := r.status_code) else code}")
        log(f"Response: {r.text[:300]}")
    except Exception as e:
        log(f"API test FAILED: {e}")


def main():
    print("=" * 60)
    print("1688 / Alibaba Data Source — Feasibility Test")
    print("=" * 60)

    test_1688_search()
    test_alibaba_search()
    test_1688_api_endpoint()

    RESULT["status"] = "see_findings"
    out = Path(__file__).parent / "result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\nResults saved to {out}")


if __name__ == "__main__":
    main()
