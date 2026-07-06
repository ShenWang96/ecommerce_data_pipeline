"""
experiment.py — Amazon India 数据源可行性验证
"""
import sys, json, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

logging.getLogger("playwright").setLevel(logging.WARNING)

RESULT = {"source": "Amazon IN", "status": "unknown", "findings": [], "products": []}

def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)

def main():
    print("=" * 60)
    print("Amazon IN — Feasibility Test")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
        )
        page = ctx.new_page()

        url = "https://www.amazon.in/s?k=bluetooth+speaker"
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
        items = soup.select('div[data-component-type="s-search-result"]')
        log(f"Found {len(items)} products")

        for item in items[:5]:
            asin = item.get("data-asin", "N/A")
            h2 = item.select_one("h2 span")
            title = h2.text.strip()[:100] if h2 else "N/A"
            pw = item.select_one(".a-price-whole")
            pf = item.select_one(".a-price-fraction")
            price_text = pw.text if pw else ""
            price_text += pf.text if pf else ""
            price = f"₹{price_text}" if price_text else "N/A"
            rating_el = item.select_one(".a-icon-alt")
            rating = rating_el.text.strip() if rating_el else "N/A"
            info = f"[{asin}] {title} | {price} | {rating}"
            log(info)
            RESULT["products"].append({"asin": asin, "title": title, "price_inr": price, "rating": rating})

        screenshot = Path(__file__).parent / "amazon_in_search.png"
        page.screenshot(path=str(screenshot))
        log(f"Screenshot: {screenshot.name}")
        browser.close()

    RESULT["status"] = "ok"
    out = Path(__file__).parent / "result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\nResults: {out}")

if __name__ == "__main__":
    main()
