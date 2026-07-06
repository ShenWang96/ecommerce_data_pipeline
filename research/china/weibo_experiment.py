"""
微博实验 — 登录后稳定获取热搜数据。

Layer 3 (内容传播): 热搜话题
"""
import sys, json, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from playwright.sync_api import sync_playwright
from session import get_or_prompt_cookies, make_playwright_context

logging.getLogger("playwright").setLevel(logging.WARNING)

SITE = "weibo"
RESULT = {"source": "微博", "findings": [], "hot_topics": []}

def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)

def main():
    cookies = get_or_prompt_cookies(SITE)
    if not cookies:
        return

    print("=" * 60)
    print("微博 — 登录后热搜测试")
    print("=" * 60)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = make_playwright_context(browser, SITE, cookies)
        page = ctx.new_page()

        # Test: 微博热搜榜
        print("\n--- 微博热搜 ---")
        try:
            page.goto("https://weibo.com/ajax/side/hotSearch", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            body = page.evaluate('() => document.body.innerText')
            log(f"响应长度: {len(body)}")

            if body and len(body) > 100:
                import json as _json
                try:
                    data = _json.loads(body)
                    realtime = data.get('data', {}).get('realtime', [])
                    log(f"热搜条数: {len(realtime)}")
                    for item in realtime[:15]:
                        word = item.get('word', '')[:50]
                        rank = item.get('rank', '?')
                        raw_hot = item.get('raw_hot', '')
                        log(f"  #{rank} {word} [{raw_hot}]")
                        RESULT["hot_topics"].append({"rank": rank, "word": word, "heat": raw_hot})
                except _json.JSONDecodeError:
                    log(f"非JSON响应: {body[:300]}")
            else:
                log("Cookie 可能无效")
        except Exception as e:
            log(f"Error: {e}")
        page.close()

        browser.close()

    out = Path(__file__).parent / "weibo_result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\n结果: {out}")

if __name__ == "__main__":
    main()
