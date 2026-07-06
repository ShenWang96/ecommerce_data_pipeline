"""
experiment.py — Amazon 数据源可行性验证 (Playwright 版)

用浏览器自动化绕过 JS 验证页面，测试能否抓取搜索列表和商品详情。
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

RESULT = {"source": "Amazon (Playwright)", "status": "unknown", "findings": []}


def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)


def test_search_page():
    """Test 1: 用 Playwright 打开搜索页"""
    log("Launching Chromium via Playwright...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = ctx.new_page()

        url = "https://www.amazon.com/s?k=bluetooth+speaker"
        log(f"Navigating to: {url}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            log(f"Navigation timeout/error: {e}")
            browser.close()
            return

        # Wait a bit for JS verification to complete
        page.wait_for_timeout(5000)

        # Check current URL (did we get redirected?)
        current_url = page.url
        log(f"Final URL: {current_url[:120]}")

        if "bm-verify" in current_url:
            log("Still on verification page — blocked")
            browser.close()
            return

        title = page.title()
        log(f"Page title: {title[:120]}")

        content = page.content()
        soup = BeautifulSoup(content, "lxml")

        # Check for captcha
        if "captcha" in content.lower():
            log("WARNING: Captcha detected!")
            browser.close()
            return

        if "Type the characters you see" in content:
            log("WARNING: CAPTCHA challenge page")
            browser.close()
            return

        # Try to find products
        _find_products(soup, page)

        # Take screenshot for reference
        page.screenshot(path=str(Path(__file__).parent / "amazon_search.png"))
        log("Screenshot saved to amazon_search.png")

        browser.close()


def _find_products(soup, page=None):
    selectors = [
        'div[data-component-type="s-search-result"]',
        '.s-result-item[data-asin]:not([data-asin=""])',
        '[data-asin]:not([data-asin=""])',
    ]
    found = False
    for sel in selectors:
        items = soup.select(sel)
        if items:
            log(f"Found {len(items)} products with '{sel}'")
            found = True
            for i, item in enumerate(items[:5]):
                asin = item.get("data-asin", "N/A")
                h2 = item.select_one("h2 span")
                title = h2.text.strip()[:80] if h2 else "N/A"
                price_whole = item.select_one(".a-price-whole")
                price_frac = item.select_one(".a-price-fraction")
                price = (
                    f"${price_whole.text}{price_frac.text}"
                    if price_whole
                    else "N/A"
                )
                rating = item.select_one(".a-icon-alt")
                rating_t = rating.text.strip() if rating else "N/A"
                reviews = item.select_one(
                    "span.a-size-base.s-underline-text"
                ) or item.select_one('[data-cy="reviews-block"] span')
                reviews_t = reviews.text.strip() if reviews else "N/A"

                log(f"  [{i+1}] ASIN={asin} | {title} | {price} | {rating_t} | Reviews={reviews_t}")
            break

    if not found:
        log("No products found — trying generic div scan...")
        # Just print what kind of content we got
        body = soup.find("body")
        if body:
            text = body.get_text()[:500]
            log(f"Page text start: {text[:300]}...")


def test_product_detail():
    """Test 2: 商品详情页"""
    log("\nTesting product detail page...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = ctx.new_page()

        asin = "B08FC5ZVR7"
        url = f"https://www.amazon.com/dp/{asin}"
        log(f"Navigating to: {url}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            log(f"Error: {e}")
            browser.close()
            return

        page.wait_for_timeout(5000)
        log(f"Final URL: {page.url[:120]}")

        content = page.content()
        soup = BeautifulSoup(content, "lxml")

        title_tag = soup.select_one("#productTitle")
        if title_tag:
            log(f"Product: {title_tag.text.strip()[:100]}")

        # Find price
        price_el = (
            soup.select_one(".a-price .a-offscreen")
            or soup.select_one("#priceblock_ourprice")
            or soup.select_one(".a-price-whole")
        )
        if price_el:
            log(f"Price: {price_el.text.strip()}")

        # Find BSR
        detail_bullets = soup.select(
            "#detailBullets_feature_div li span"
        ) + soup.select("#productDetails_detailBullets_sections1 tr")
        for el in detail_bullets:
            text = el.text.strip()
            if "Best Sellers" in text:
                log(f"BSR: {text[:150]}")

        # Review count
        review_el = soup.select_one("#acrCustomerReviewText")
        if review_el:
            log(f"Reviews: {review_el.text.strip()}")

        page.screenshot(path=str(Path(__file__).parent / "amazon_detail.png"))
        log("Screenshot saved to amazon_detail.png")
        browser.close()


def main():
    import logging
    logging.getLogger("playwright").setLevel(logging.WARNING)

    print("=" * 60)
    print("Amazon Data Source — Feasibility Test (Playwright)")
    print("=" * 60)

    test_search_page()
    test_product_detail()

    RESULT["status"] = "see_findings"
    out = Path(__file__).parent / "result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\nResults saved to {out}")


if __name__ == "__main__":
    main()
