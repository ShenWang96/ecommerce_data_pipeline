"""
小红书实验 — 登录后提取笔记内容和搜索数据。

Layer 1-3: 需求萌芽、理念形成、内容传播
"""
import sys, json, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from session import get_or_prompt_cookies, make_playwright_context

logging.getLogger("playwright").setLevel(logging.WARNING)

SITE = "xiaohongshu"
RESULT = {"source": "小红书", "findings": [], "notes": []}

def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)

def main():
    cookies = get_or_prompt_cookies(SITE)
    if not cookies:
        return

    print("=" * 60)
    print("小红书 — 登录后数据测试")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = make_playwright_context(browser, SITE, cookies)
        page = ctx.new_page()

        # Test 1: 首页推荐流
        print("\n--- Test 1: 首页 Explore ---")
        try:
            page.goto("https://www.xiaohongshu.com/explore", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            txt_len = len(page.evaluate('() => document.body.innerText'))
            title = page.title()
            log(f"标题: {title[:80]}")
            log(f"文本长度: {txt_len}")

            if txt_len > 500:
                body = page.evaluate('() => document.body.innerText')
                lines = [l.strip() for l in body.split('\n') if l.strip() and len(l.strip()) > 3]
                log(f"有效行数: {len(lines)}")
                for l in lines[:20]:
                    log(f"  {l[:100]}")
            else:
                log("内容较少，可能 Cookie 无效或页面加载不完整")
        except Exception as e:
            log(f"Error: {e}")
        page.close()

        # Test 2: 搜索
        print("\n--- Test 2: 搜索「收纳」---")
        page = ctx.new_page()
        try:
            page.goto("https://www.xiaohongshu.com/search_result?keyword=收纳", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            txt_len = len(page.evaluate('() => document.body.innerText'))
            log(f"搜索结果 文本长度: {txt_len}")

            if txt_len > 500:
                body = page.evaluate('() => document.body.innerText')
                lines = [l.strip() for l in body.split('\n') if l.strip() and len(l.strip()) > 3]
                log(f"有效行数: {len(lines)}")
                for l in lines[:20]:
                    log(f"  {l[:100]}")
        except Exception as e:
            log(f"Error: {e}")
        page.close()

        browser.close()

    out = Path(__file__).parent / "xiaohongshu_result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\n结果: {out}")


if __name__ == "__main__":
    main()
