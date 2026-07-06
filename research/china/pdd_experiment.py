"""
拼多多实验 — 登录后提取搜索商品数据。

Layer 5 (商业验证): 大众消费验证
"""
import sys, json, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.sync_api import sync_playwright
from session import get_or_prompt_cookies, make_playwright_context

logging.getLogger("playwright").setLevel(logging.WARNING)

SITE = "pdd"
RESULT = {"source": "拼多多", "findings": []}

def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)

def main():
    cookies = get_or_prompt_cookies(SITE)
    if not cookies:
        return

    print("=" * 60)
    print("拼多多 — 登录后搜索测试")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = make_playwright_context(browser, SITE, cookies)
        page = ctx.new_page()

        # 使用移动版页面（反爬更松）
        url = "https://mobile.yangkeduo.com/search_result.html?search_key=%E6%94%B6%E7%BA%B3%E7%9B%92"
        log(f"\n搜索: {url}")
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            txt_len = len(page.evaluate('() => document.body.innerText'))
            title = page.title()
            log(f"标题: {title[:100]}")
            log(f"文本长度: {txt_len}")

            if "登录" in title:
                log("Cookie 无效，需登录")
            elif txt_len > 200:
                body = page.evaluate('() => document.body.innerText')
                lines = [l.strip() for l in body.split('\n') if l.strip() and len(l.strip()) > 3]
                log(f"\n有效行数: {len(lines)}")
                for l in lines[:20]:
                    log(f"  {l[:120]}")
        except Exception as e:
            log(f"Error: {e}")
        page.close()

        browser.close()

    out = Path(__file__).parent / "pdd_result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\n结果: {out}")

if __name__ == "__main__":
    main()
