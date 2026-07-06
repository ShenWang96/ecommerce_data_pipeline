"""
知乎实验 v2 — 多策略测试 Layer 1 需求萌芽信号。

策略:
  1. httpx 无登录 → /explore 发现页 (热点问题标题+浏览量)
  2. httpx + Cookie → /hot 热榜 JSON API
  3. Playwright + Cookie → 完整浏览器体验
"""
import sys, json, time, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
from bs4 import BeautifulSoup
from session import get_or_prompt_cookies

SITE = "zhihu"
RESULT = {"source": "知乎", "findings": [], "questions": [], "strategies": {}}

def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
}

CLIENT = httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True)


# ─── Strategy 1: 无登录 httpx → /explore (发现页) ───
def test_explore_no_login():
    print("\n--- Strategy 1: 无登录 /explore (httpx) ---")
    try:
        r = CLIENT.get("https://www.zhihu.com/explore")
        log(f"  HTTP {r.status_code} ({len(r.text)} bytes)")
        soup = BeautifulSoup(r.text, "lxml")
        title = soup.title.string.strip() if soup.title else "no title"
        log(f"  Title: {title[:80]}")
        
        # Check if logged in
        if "登录" in r.text[:2000] and "知乎" in r.text[:2000]:
            log("  页面含登录引导，可能需 Cookie")
        
        # Try to extract questions from explore page
        cards = (
            soup.select(".ExploreHomePage-specials") or
            soup.select('[class*=ExploreSpecialCard]') or
            soup.select('[class*=explore] [class*=card]') or
            soup.select('[class*=ContentItem]')
        )
        log(f"  卡片数: {len(cards)}")
        
        # Extract text-based question titles
        body = soup.get_text()
        lines = [l.strip() for l in body.split('\n') if l.strip() and len(l.strip()) > 10]
        # Filter to likely questions/topics
        question_lines = [l for l in lines if l.endswith('?') or l.endswith('？') or '如何' in l or '为什么' in l]
        log(f"  疑似问题行: {len(question_lines)}")
        for l in question_lines[:10]:
            log(f"    {l[:100]}")
        
        if len(question_lines) > 0:
            RESULT["strategies"]["explore_no_login"] = True
            return lines
    except Exception as e:
        log(f"  Error: {e}")
    RESULT["strategies"]["explore_no_login"] = False
    return []


# ─── Strategy 2: httpx + Cookie → /hot (热榜页面) ───
def test_hot_with_cookies(cookies: list[dict]):
    print("\n--- Strategy 2: Cookie + /hot (httpx) ---")
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
    h = {**HEADERS, "Cookie": cookie_str}
    try:
        with httpx.Client(headers=h, timeout=20, follow_redirects=True) as c:
            r = c.get("https://www.zhihu.com/hot")
        log(f"  HTTP {r.status_code} ({len(r.text)} bytes)")
        
        if "登录" in r.text[:2000]:
            log("  Cookie 过期 → 显示登录页")
            RESULT["strategies"]["hot_with_cookie"] = False
            return []
        
        soup = BeautifulSoup(r.text, "lxml")
        
        # Try to find hot items
        items = (
            soup.select(".HotList-item") or
            soup.select('[class*=HotItem]') or
            soup.select('.HotList-list .HotItem') or
            soup.select('[class*=card] h2')
        )
        log(f"  热榜条目: {len(items)}")
        
        # Also try text extraction
        body_lines = soup.get_text().split('\n')
        body_lines = [l.strip() for l in body_lines if l.strip() and len(l.strip()) > 8]
        
        # Look for numbered items (典型热榜格式)
        hot_candidates = []
        for l in body_lines:
            if l[0].isdigit() or l.startswith('排名') or '热度' in l or '回答' in l or '关注' in l:
                hot_candidates.append(l)
        
        log(f"  疑似热榜行: {len(hot_candidates)}")
        for l in hot_candidates[:15]:
            log(f"    {l[:100]}")
        for l in body_lines[:20]:
            log(f"    {l[:100]}")
        
        if items or len(hot_candidates) > 5:
            RESULT["strategies"]["hot_with_cookie"] = True
            return body_lines
    except Exception as e:
        log(f"  Error: {e}")
    RESULT["strategies"]["hot_with_cookie"] = False
    return []


# ─── Strategy 3: 搜索 (httpx + Cookie) ───
def test_search_with_cookies(cookies: list[dict], keyword: str = "收纳"):
    print(f"\n--- Strategy 3: 搜索「{keyword}」(httpx + Cookie) ---")
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
    h = {**HEADERS, "Cookie": cookie_str}
    try:
        with httpx.Client(headers=h, timeout=20, follow_redirects=True) as c:
            r = c.get(f"https://www.zhihu.com/search?type=content&q={keyword}")
        log(f"  HTTP {r.status_code} ({len(r.text)} bytes)")
        
        if "登录" in r.text[:2000]:
            log("  Cookie 过期")
            RESULT["strategies"]["search_with_cookie"] = False
            return []
        
        soup = BeautifulSoup(r.text, "lxml")
        body_lines = soup.get_text().split('\n')
        body_lines = [l.strip() for l in body_lines if l.strip() and len(l.strip()) > 8]
        log(f"  有效行: {len(body_lines)}")
        for l in body_lines[:20]:
            log(f"    {l[:100]}")
        
        RESULT["strategies"]["search_with_cookie"] = len(body_lines) > 5
        return body_lines
    except Exception as e:
        log(f"  Error: {e}")
    RESULT["strategies"]["search_with_cookie"] = False
    return []


# ─── Strategy 4: httpx → /api/v3/feed/topstory (热榜 JSON API) ───
def test_hot_api(cookies: list[dict]):
    print("\n--- Strategy 4: 热榜 JSON API (httpx + Cookie) ---")
    cookie_str = "; ".join(f"{c['name']}={c['value']}" for c in cookies)
    h = {**HEADERS, "Cookie": cookie_str, "x-requested-with": "fetch"}
    try:
        with httpx.Client(headers=h, timeout=20, follow_redirects=True) as c:
            r = c.get("https://www.zhihu.com/api/v3/feed/topstory/hot-lists/total?limit=50&desktop=true")
        log(f"  HTTP {r.status_code} ({len(r.text)} bytes)")
        if r.status_code == 200 and r.text.startswith("{"):
            data = r.json()
            items = data.get("data", [])
            log(f"  JSON API 成功! 条目数: {len(items)}")
            for item in items[:10]:
                target = item.get("target", {})
                title = target.get("title", "")[:60]
                metrics = target.get("metrics_area", {}).get("text", "")
                log(f"    {title}  [{metrics}]")
            RESULT["strategies"]["hot_api"] = True
            return data
        else:
            log(f"  API 失败: {r.text[:200]}")
    except Exception as e:
        log(f"  Error: {e}")
    RESULT["strategies"]["hot_api"] = False
    return {}


def main():
    print("=" * 60)
    print("知乎 — 多策略 Layer 1 信号测试")
    print("=" * 60)

    # Strategy 1: no login needed
    test_explore_no_login()

    # Strategies 2-4: need cookies
    cookies = get_or_prompt_cookies(SITE)
    if cookies:
        test_hot_with_cookies(cookies)
        test_search_with_cookies(cookies)
        test_hot_api(cookies)

    # Summary
    print("\n" + "=" * 60)
    print("策略汇总:")
    for name, ok in RESULT["strategies"].items():
        print(f"  {'✅' if ok else '❌'} {name}")

    out = Path(__file__).parent / "zhihu_v2_result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\n结果: {out}")


if __name__ == "__main__":
    main()
