"""
微博实验 — 多策略攻克热搜数据。

策略优先级:
  1. 移动端 API (m.weibo.cn) — 无需登录，有频率限制
  2. Web API (weibo.com/ajax/side/hotSearch) — 需 Cookie
  3. Playwright 渲染 — 兜底方案
"""
import sys, json, time, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from playwright.sync_api import sync_playwright
from session import get_or_prompt_cookies, make_playwright_context

logging.getLogger("playwright").setLevel(logging.WARNING)

SITE = "weibo"
RESULT = {"source": "微博", "findings": [], "topics": [], "strategies": {}}

def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
}

WEB_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://weibo.com",
}

# ─── Strategy 1: 移动端 API (无需 Cookie) ───
def test_mobile_api():
    print("\n--- Strategy 1: 移动端 API ---")
    url = "https://m.weibo.cn/api/container/getIndex"
    params = {
        "containerid": "106003type%3D25%26t%3D3%26disable_hot%3D1%26filter_type%3Drealtimehot",
        "title": "微博热搜",
        "luicode": "10000011",
        "lfid": "106003type%3D25%26t%3D3%26disable_hot%3D1%26filter_type%3Drealtimehot",
    }
    try:
        with httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True) as c:
            r = c.get(url, params=params)
        log(f"  HTTP {r.status_code} ({len(r.text)} bytes)")
        if r.status_code == 200:
            try:
                data = r.json()
                if data.get("ok") == 1:
                    cards = data.get("data", {}).get("cards", [])
                    log(f"  成功! cards: {len(cards)}")
                    for card in cards:
                        card_group = card.get("card_group", [])
                        hot_items = 0
                        for item in card_group:
                            if item.get("itemid"):
                                hot_items += 1
                                if hot_items <= 10:
                                    desc = item.get("desc", "")[:50]
                                    log(f"    {desc}")
                        log(f"  该 card 含 {hot_items} 条热搜")
                    RESULT["strategies"]["mobile_api"] = True
                    return cards
                else:
                    log(f"  API 返回 ok!=1: {data.get('msg','?')}")
            except json.JSONDecodeError:
                log(f"  非 JSON: {r.text[:300]}")
        elif r.status_code == 302:
            log(f"  302 重定向到: {r.headers.get('location','?')}")
    except Exception as e:
        log(f"  Error: {e}")
    RESULT["strategies"]["mobile_api"] = False
    return []


# ─── Strategy 2: Web API (需 Cookie) ───
def test_web_api_httpx(cookies: list[dict]):
    print("\n--- Strategy 2: Web API (httpx + Cookie) ---")
    url = "https://weibo.com/ajax/side/hotSearch"
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
    h = {**WEB_HEADERS, "Cookie": cookie_str}
    try:
        with httpx.Client(headers=h, timeout=20, follow_redirects=True) as c:
            r = c.get(url)
        log(f"  HTTP {r.status_code} ({len(r.text)} bytes)")
        if r.status_code == 200:
            try:
                data = r.json()
                realtime = data.get("data", {}).get("realtime", [])
                log(f"  成功! 热搜条数: {len(realtime)}")
                for item in realtime[:15]:
                    word = item.get("word", "")[:50]
                    rank = item.get("rank", "?")
                    raw_hot = item.get("raw_hot", "")
                    category = item.get("category", "")
                    log(f"    #{rank} {word} [热度:{raw_hot}] {category}")
                    RESULT["topics"].append({
                        "rank": rank, "word": word,
                        "heat": raw_hot, "category": category,
                    })
                RESULT["strategies"]["web_api_httpx"] = True
                return data
            except json.JSONDecodeError:
                log(f"  非 JSON: {r.text[:300]}")
        elif r.status_code == 403:
            log("  403 — Cookie 无效或过期")
    except Exception as e:
        log(f"  Error: {e}")
    RESULT["strategies"]["web_api_httpx"] = False
    return {}


# ─── Strategy 3: 网页热搜榜 (Playwright) ───
def test_web_hot_playwright(browser_obj, cookies):
    print("\n--- Strategy 3: 网页热搜榜 (Playwright) ---")
    try:
        ctx = make_playwright_context(browser_obj, SITE, cookies)
        page = ctx.new_page()
        page.goto("https://weibo.com/newlogin?tabtype=weibo&gid=102803&OpenLoginLayer=1", wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)
        body = page.evaluate('() => document.body.innerText')
        txt_len = len(body)
        log(f"  页面文本长度: {txt_len}")
        if txt_len > 500:
            lines = [l.strip() for l in body.split("\n") if l.strip()]
            # Try to find hot topics
            hot_seen = False
            for l in lines[:50]:
                if any(kw in l for kw in ["热搜", "实时", "热度", "排名"]):
                    if not hot_seen:
                        log(f"  找到热搜区域:")
                        hot_seen = True
                if hot_seen and len(l) > 3:
                    log(f"    {l[:100]}")
        else:
            log("  页面内容不足，可能需 Cookie")
        page.close()
        RESULT["strategies"]["web_hot_playwright"] = txt_len > 500
    except Exception as e:
        log(f"  Error: {e}")
        RESULT["strategies"]["web_hot_playwright"] = False


def main():
    print("=" * 60)
    print("微博 — 多策略热搜攻克")
    print("=" * 60)

    # Try Strategy 1 first (no cookie needed)
    mobile_data = test_mobile_api()
    if mobile_data:
        print("\n✅ 移动端 API 可用，无需 Cookie！")

    # Try Strategy 2 (needs cookie)
    cookies = get_or_prompt_cookies(SITE)
    if cookies:
        test_web_api_httpx(cookies)

    # Try Strategy 3 (Playwright fallback)
    if cookies:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            test_web_hot_playwright(browser, cookies)
            browser.close()

    # Summary
    print("\n" + "=" * 60)
    print("策略汇总:")
    for name, ok in RESULT["strategies"].items():
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")

    out = Path(__file__).parent.parent / "weibo_result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\n结果: {out}")


if __name__ == "__main__":
    main()
