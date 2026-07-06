"""
京东实验 — 登录后提取搜索商品数据。

Layer 5 (商业验证): 新品数量、销量、评论
"""
import sys, json, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from session import get_or_prompt_cookies, make_playwright_context

logging.getLogger("playwright").setLevel(logging.WARNING)

SITE = "jd"
RESULT = {"source": "京东", "findings": [], "products": []}

def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)

def main():
    cookies = get_or_prompt_cookies(SITE)
    if not cookies:
        return

    print("=" * 60)
    print("京东 — 登录后搜索测试")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = make_playwright_context(browser, SITE, cookies)
        page = ctx.new_page()

        url = "https://search.jd.com/Search?keyword=%E6%94%B6%E7%BA%B3%E7%9B%92&enc=utf-8"
        log(f"\n搜索: {url}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            txt_len = len(page.evaluate('() => document.body.innerText'))
            title = page.title()
            log(f"标题: {title[:100]}")
            log(f"文本长度: {txt_len}")

            if "登录" in title or "passport" in page.url.lower():
                log("Cookie 无效，跳转登录页")
            elif txt_len > 200:
                body = page.evaluate('() => document.body.innerText')
                lines = [l.strip() for l in body.split('\n') if l.strip() and len(l.strip()) > 3]
                log(f"\n有效行数: {len(lines)}")

                soup = BeautifulSoup(page.content(), "lxml")
                # Try JD product selectors
                sel_list = ['.gl-item', '.goods-list li', '.item', '[class*=goods]']
                for sel in sel_list:
                    items = soup.select(sel)
                    if items:
                        log(f"\nSelector '{sel}': {len(items)} 个商品")
                        for item in items[:3]:
                            txt = item.get_text(strip=True)[:150]
                            log(f"  {txt}")
                        break

                if not any(soup.select(s) for s in sel_list):
                    for l in lines[:20]:
                        log(f"  {l[:120]}")
        except Exception as e:
            log(f"Error: {e}")
        page.close()

        browser.close()

    out = Path(__file__).parent / "jd_result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\n结果: {out}")

if __name__ == "__main__":
    main()
