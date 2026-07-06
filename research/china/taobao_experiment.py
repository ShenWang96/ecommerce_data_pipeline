"""
淘宝实验 — 登录后提取搜索页商品数据。

Layer 5 (商业验证): 新品数量、销量、评论增长
"""
import sys, json, time, logging, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from session import get_or_prompt_cookies, make_playwright_context

logging.getLogger("playwright").setLevel(logging.WARNING)

SITE = "taobao"
RESULT = {"source": "淘宝", "findings": [], "products": []}

def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)

def main():
    cookies = get_or_prompt_cookies(SITE)
    if not cookies:
        return

    print("=" * 60)
    print("淘宝 — 登录后搜索测试")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = make_playwright_context(browser, SITE, cookies)
        page = ctx.new_page()

        # 搜索「收纳盒」
        url = "https://s.taobao.com/search?q=%E6%94%B6%E7%BA%B3%E7%9B%92"
        log(f"\n搜索: {url}")

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            txt_len = len(page.evaluate('() => document.body.innerText'))
            title = page.title()
            log(f"标题: {title[:100]}")
            log(f"文本长度: {txt_len}")

            soup = BeautifulSoup(page.content(), "lxml")

            # Check if logged in
            if "登录" in title or "login" in title.lower():
                log("Cookie 无效，需要重新登录")
                browser.close()
                return

            # Try multiple selectors for products
            body_text = page.evaluate('() => document.body.innerText')
            lines = [l.strip() for l in body_text.split('\n') if l.strip() and len(l.strip()) > 5]
            log(f"\n有效文本行: {len(lines)}")
            # Show non-noisy lines
            shown = 0
            for l in lines:
                if any(c in l for c in ['¥', '￥', '付款', '收货', '销量', '人付款', '价格']):
                    log(f"  {l[:120]}")
                    shown += 1
                if shown >= 20:
                    break

            # Also try to find product cards
            product_sels = [
                '.item', '.J_MouseEneterLeave', '[class*=item]',
                '.grid-item', '.card', '.product',
            ]
            for sel in product_sels:
                items = soup.select(sel)
                if items:
                    log(f"\nSelector '{sel}': {len(items)} 个元素")
                    for item in items[:3]:
                        txt = item.get_text(strip=True)[:120]
                        log(f"  {txt}")

        except Exception as e:
            log(f"Error: {e}")
        finally:
            page.close()

        browser.close()

    out = Path(__file__).parent / "taobao_result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\n结果: {out}")


if __name__ == "__main__":
    main()
