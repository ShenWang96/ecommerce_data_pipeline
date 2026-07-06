"""
百度指数实验 — 登录后提取搜索趋势数据。

Layer 4 (大众关注): 搜索量变化
"""
import sys, json, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.sync_api import sync_playwright
from session import get_or_prompt_cookies, make_playwright_context

logging.getLogger("playwright").setLevel(logging.WARNING)

SITE = "baidu_index"
RESULT = {"source": "百度指数", "findings": []}

def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)


def main():
    cookies = get_or_prompt_cookies(SITE)
    if not cookies:
        return

    print("=" * 60)
    print("百度指数 — 登录后测试")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = make_playwright_context(browser, SITE, cookies)
        page = ctx.new_page()

        # 百度指数首页
        print("\n--- Test 1: 百度指数首页 ---")
        try:
            page.goto("https://index.baidu.com/v2/index.html", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(5000)
            txt_len = len(page.evaluate('() => document.body.innerText'))
            title = page.title()
            log(f"标题: {title[:80]}")
            log(f"文本长度: {txt_len}")

            body_text = page.evaluate('() => document.body.innerText')
            log(f"\n内容:\n{body_text[:600]}")

            # Check for data panels
            if "指数" in body_text and txt_len > 200:
                log("\n[+] 页面内容包含指数数据")
            elif "登录" in body_text[:300]:
                log("[-] Cookie 无效，仍要求登录")
            elif txt_len < 100:
                log("[-] 页面内容极少，可能是 SPA 未加载完成")
        except Exception as e:
            log(f"Error: {e}")
        page.close()

        # 尝试直达趋势搜索页
        print("\n--- Test 2: 直接搜索「蓝牙音箱」---")
        page = ctx.new_page()
        try:
            page.goto(
                "https://index.baidu.com/v2/main/index.html#/trend/%E8%93%9D%E7%89%99%E9%9F%B3%E7%AE%B1",
                wait_until="domcontentloaded", timeout=30000
            )
            page.wait_for_timeout(5000)
            txt_len = len(page.evaluate('() => document.body.innerText'))
            body_text = page.evaluate('() => document.body.innerText')
            log(f"文本长度: {txt_len}")
            log(f"内容:\n{body_text[:600]}")
        except Exception as e:
            log(f"Error: {e}")
        page.close()

        browser.close()

    out = Path(__file__).parent / "baidu_index_result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\n结果: {out}")


if __name__ == "__main__":
    main()
