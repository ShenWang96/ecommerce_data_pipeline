"""
1688实验 — 登录后提取搜索商品、供应商数据。

Layer 6 (供应扩张): 新增供应商、MOQ、价格
"""
import sys, json, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from session import get_or_prompt_cookies, make_playwright_context

logging.getLogger("playwright").setLevel(logging.WARNING)

SITE = "1688"
RESULT = {"source": "1688", "findings": [], "products": []}

def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)

def main():
    cookies = get_or_prompt_cookies(SITE)
    if not cookies:
        return

    print("=" * 60)
    print("1688 — 登录后搜索测试")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = make_playwright_context(browser, SITE, cookies)
        page = ctx.new_page()

        url = "https://s.1688.com/selloffer/offer_search.htm?keywords=%CA%D5%C4%C9%BA%D0"
        log(f"\n搜索: {url}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            txt_len = len(page.evaluate('() => document.body.innerText'))
            title = page.title()
            log(f"标题: {title[:100]}")
            log(f"文本长度: {txt_len}")

            if "登录" in page.content()[:1000]:
                log("Cookie 无效，需要重新登录")
            elif txt_len > 200:
                body = page.evaluate('() => document.body.innerText')
                lines = [l.strip() for l in body.split('\n') if l.strip() and len(l.strip()) > 3]
                log(f"\n有效行数: {len(lines)}")
                # Focus on product-related lines
                for l in lines[:30]:
                    if any(c in l for c in ['¥', '￥', '件', '台', '个', '起批', '成交', '供应商']):
                        log(f"  {l[:120]}")
                    elif len(l) > 10:
                        log(f"  {l[:120]}")
        except Exception as e:
            log(f"Error: {e}")
        page.close()

        browser.close()

    out = Path(__file__).parent / "1688_result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\n结果: {out}")

if __name__ == "__main__":
    main()
