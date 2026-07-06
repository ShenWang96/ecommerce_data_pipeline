"""
知乎实验 — 登录后提取热点问题和回答内容。

Layer 1 (需求萌芽): 知乎问题是发现用户痛点的最佳来源
"""
import sys, json, time, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from session import get_or_prompt_cookies, make_playwright_context

logging.getLogger("playwright").setLevel(logging.WARNING)

SITE = "zhihu"
RESULT = {"source": "知乎", "findings": [], "questions": []}

def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)

def main():
    cookies = get_or_prompt_cookies(SITE)
    if not cookies:
        return

    print("=" * 60)
    print("知乎 — 登录后数据提取测试")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = make_playwright_context(browser, SITE, cookies)
        page = ctx.new_page()

        # Test 1: 热榜
        print("\n--- Test 1: 知乎热榜 ---")
        try:
            page.goto("https://www.zhihu.com/hot", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            txt_len = len(page.evaluate('() => document.body.innerText'))
            log(f"热榜页 文本长度: {txt_len}")

            if "登录" in page.content()[:1000]:
                log("Cookie 已过期或无效，需要重新登录")
            else:
                # Extract hot questions
                soup = BeautifulSoup(page.content(), "lxml")
                items = soup.select(".HotList-item") or soup.select('[class*=HotItem]')
                log(f"找到 {len(items)} 个热榜条目")

                # Try to get titles from the page
                titles = soup.select("h2") or soup.select('[class*=title]')
                for t in titles[:10]:
                    text = t.get_text(strip=True)
                    if len(text) > 5:
                        log(f"  {text[:80]}")

                body = page.evaluate('() => document.body.innerText')
                lines = [l.strip() for l in body.split('\n') if l.strip() and len(l.strip()) > 8]
                log(f"有效文本行数: {len(lines)}")
                for l in lines[:15]:
                    log(f"  {l[:100]}")
        except Exception as e:
            log(f"Error: {e}")
        page.close()

        # Test 2: 搜索问题
        print("\n--- Test 2: 搜索「收纳」---")
        page = ctx.new_page()
        try:
            page.goto("https://www.zhihu.com/search?type=content&q=收纳", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            body = page.evaluate('() => document.body.innerText')
            lines = [l.strip() for l in body.split('\n') if l.strip() and len(l.strip()) > 8]
            log(f"搜索结果文本行数: {len(lines)}")
            for l in lines[:20]:
                log(f"  {l[:100]}")
        except Exception as e:
            log(f"Error: {e}")
        page.close()

        browser.close()

    out = Path(__file__).parent / "zhihu_result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\n结果: {out}")


if __name__ == "__main__":
    main()
