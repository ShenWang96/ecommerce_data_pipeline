"""
experiment.py — Rakuten Japan 数据源可行性验证

Rakuten Ichiba is Japan's largest e-commerce marketplace.
Playwright renders JS-heavy product cards. Results include title, price (JPY),
rating, review count, shipping info, and merchant name.
"""
import sys, json, logging, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

logging.getLogger("playwright").setLevel(logging.WARNING)

RESULT = {"source": "Rakuten JP", "status": "unknown", "findings": [], "products": []}

def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)

def extract_products(soup, max_items=5):
    items = soup.select(".searchresultitem")
    log(f"Found {len(items)} search result items")

    for item in items[:max_items]:
        title_el = item.select_one('[class*=title]')
        title = title_el.text.strip()[:120] if title_el else "N/A"

        price_text = "N/A"
        for div in item.find_all("div", recursive=False):
            txt = div.get_text(strip=True)
            if "円" in txt and any(c.isdigit() for c in txt):
                price_text = txt
                break

        link_el = item.select_one("a[href*='item.rakuten']")
        link = link_el.get("href", "")[:120] if link_el else "N/A"

        review_el = item.select_one('[class*=review]')
        review_text = review_el.text.strip() if review_el else "N/A"

        info = f"{title} | {price_text} | Rating={review_text}"
        log(info)
        RESULT["products"].append({
            "title": title,
            "price_jpy": price_text,
            "url": link,
            "rating_reviews": review_text,
        })

def main():
    print("=" * 60)
    print("Rakuten JP — Feasibility Test")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = ctx.new_page()

        url = "https://search.rakuten.co.jp/search/mall/bluetooth+speaker/"
        log(f"Navigating to: {url}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            log(f"Navigation error: {e}")
            browser.close()
            return

        page.wait_for_timeout(5000)
        log(f"Page title: {page.title()[:120]}")

        soup = BeautifulSoup(page.content(), "lxml")
        extract_products(soup)

        total_text = soup.select_one('[class*=count]') or soup.find(string=re.compile(r'[\d,]+件'))
        if total_text:
            log(f"Total results: {total_text.text.strip()[:100]}")

        screenshot = Path(__file__).parent / "rakuten_jp_search.png"
        page.screenshot(path=str(screenshot))
        log(f"Screenshot: {screenshot.name}")
        browser.close()

    RESULT["status"] = "ok"
    out = Path(__file__).parent / "result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\nResults: {out}")

if __name__ == "__main__":
    main()
