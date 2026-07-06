"""
B站 API 实验 — 验证所有公开端点，确认数据格式。
无需登录，境外 IP 可直接访问。
"""
import sys, json, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import httpx

BASE = "https://api.bilibili.com"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Referer": "https://www.bilibili.com",
}

RESULT = {"source": "Bilibili API", "findings": [], "endpoints": {}}
CLIENT = httpx.Client(headers=HEADERS, timeout=20, follow_redirects=True)


def log(msg):
    print(f"  {msg}")
    RESULT["findings"].append(msg)


def get_json(url: str, params: dict = None) -> dict:
    r = CLIENT.get(url, params=params)
    code = r.status_code
    log(f"  HTTP {code} ({len(r.text)} bytes)")
    if code != 200:
        log(f"  Response: {r.text[:300]}")
        return {}
    try:
        data = r.json()
        log(f"  code={data.get('code')}, message={data.get('message', '-')}")
        return data
    except Exception as e:
        log(f"  JSON parse error: {e}")
        log(f"  Raw: {r.text[:300]}")
        return {}


def test_popular():
    print("\n--- Test 1: 热门内容 ---")
    params = {"pn": 1, "ps": 10}
    data = get_json(f"{BASE}/x/web-interface/popular", params)
    if data.get("code") == 0:
        d = data["data"]
        videos = d.get("list", [])
        log(f"  热门视频数: {len(videos)} (total: {d.get('no_more', '?')})")
        for v in videos[:5]:
            stat = v.get("stat", {})
            log(f"    [{v.get('tname','?')}] {v.get('title','')[:60]} "
                f"播放:{stat.get('view','?')} 弹幕:{stat.get('danmaku','?')} "
                f"点赞:{stat.get('like','?')}")
    RESULT["endpoints"]["popular"] = bool(data.get("code") == 0)


def test_ranking():
    print("\n--- Test 2: 全站排行榜 ---")
    params = {"rid": 0, "type": "all"}
    data = get_json(f"{BASE}/x/web-interface/ranking/v2", params)
    if data.get("code") == 0:
        d = data["data"]
        videos = d.get("list", [])
        log(f"  排行榜视频数: {len(videos)}")
        for v in videos[:5]:
            stat = v.get("stat", {})
            log(f"    #{v.get('rank','?')} [{v.get('tname','?')}] {v.get('title','')[:60]} "
                f"播放:{stat.get('view','?')} 点赞:{stat.get('like','?')}")
        # Show available rid categories
        if "archive" in d:
            log(f"  category_archives: {d.get('archive','')}")
    RESULT["endpoints"]["ranking"] = bool(data.get("code") == 0)


def test_video_detail():
    print("\n--- Test 3: 视频详情 ---")
    # First get a video bvid from popular
    pop = get_json(f"{BASE}/x/web-interface/popular", {"pn": 1, "ps": 1})
    if pop.get("code") != 0 or not pop.get("data", {}).get("list"):
        log("  Cannot get video to test — skip")
        return
    bvid = pop["data"]["list"][0]["bvid"]
    log(f"  Testing bvid={bvid}")

    data = get_json(f"{BASE}/x/web-interface/view", {"bvid": bvid})
    if data.get("code") == 0:
        d = data["data"]
        stat = d.get("stat", {})
        owner = d.get("owner", {})
        log(f"  标题: {d.get('title','')[:80]}")
        log(f"  描述: {d.get('desc','')[:100]}")
        log(f"  标签: {d.get('tname','')} / 分区: {d.get('tid','?')}")
        log(f"  UP主: {owner.get('name','?')} (mid={owner.get('mid','?')})")
        log(f"  播放:{stat.get('view','?')} 点赞:{stat.get('like','?')} "
            f"投币:{stat.get('coin','?')} 收藏:{stat.get('favorite','?')} "
            f"转发:{stat.get('share','?')}")
        RESULT["sample_video"] = {"bvid": bvid, "title": d.get("title", ""),
                                  "owner_mid": owner.get("mid", "")}
    RESULT["endpoints"]["video_detail"] = bool(data.get("code") == 0)


def test_comments():
    print("\n--- Test 4: 视频评论 ---")
    sample = RESULT.get("sample_video", {})
    bvid = sample.get("bvid", "")
    if not bvid:
        log("  No sample video — skip")
        return

    # Need aid (oid) from video detail
    detail = get_json(f"{BASE}/x/web-interface/view", {"bvid": bvid})
    if detail.get("code") != 0:
        log("  Cannot get aid — skip")
        return
    aid = detail["data"]["aid"]
    log(f"  Video aid={aid}")

    data = get_json(f"{BASE}/x/v2/reply", {"type": 1, "oid": aid, "pn": 1, "ps": 5, "sort": 2})
    if data.get("code") == 0:
        d = data["data"]
        replies = d.get("replies", [])
        total = d.get("page", {}).get("count", "?")
        log(f"  评论总数: {total}, 本页: {len(replies)}")
        for r in replies[:5]:
            content = r.get("content", {}).get("message", "")[:80]
            member = r.get("member", {}).get("uname", "?")
            log(f"    [{member}] {content} (点赞:{r.get('like',0)})")
    RESULT["endpoints"]["comments"] = bool(data.get("code") == 0)


def test_up_videos():
    print("\n--- Test 5: UP主视频列表 ---")
    mid = RESULT.get("sample_video", {}).get("owner_mid", "")
    if not mid:
        log("  No sample UP主 — skip")
        return

    log(f"  UP主 mid={mid}")
    data = get_json(f"{BASE}/x/space/arc/search", {"mid": mid, "pn": 1, "ps": 5})
    if data.get("code") == 0:
        d = data["data"]
        videos = d.get("list", {}).get("vlist", d.get("list", []))
        total = d.get("page", {}).get("count", len(videos))
        log(f"  视频总数: {total}, 本页: {len(videos) if isinstance(videos, list) else 0}")
        if isinstance(videos, list):
            for v in videos[:5]:
                log(f"    {v.get('title','')[:60]} 播放:{v.get('play','?')} 评论:{v.get('comment','?')}")
    RESULT["endpoints"]["up_videos"] = bool(data.get("code") == 0)


def test_up_info():
    print("\n--- Test 6: UP主信息 ---")
    mid = RESULT.get("sample_video", {}).get("owner_mid", "")
    if not mid:
        log("  No sample UP主 — skip")
        return

    data = get_json(f"{BASE}/x/web-interface/card", {"mid": mid})
    if data.get("code") == 0:
        card = data["data"].get("card", {})
        log(f"  UP主: {card.get('name','?')}")
        log(f"  粉丝: {card.get('fans','?')}")
        log(f"  关注: {card.get('attention','?')}")
        log(f"  等级: Lv{card.get('level_info',{}).get('current_level','?')}")
    RESULT["endpoints"]["up_info"] = bool(data.get("code") == 0)


def test_search():
    print("\n--- Test 7: 搜索 (需cookie?) ---")
    # The research said search returns 412 — let's verify
    r = CLIENT.get(f"{BASE}/x/web-interface/search/type",
                   params={"search_type": "video", "keyword": "收纳", "page": 1})
    log(f"  HTTP {r.status_code} ({len(r.text)} bytes)")
    if r.status_code == 200:
        try:
            data = r.json()
            log(f"  code={data.get('code')}, message={data.get('message','-')}")
        except:
            log(f"  Raw: {r.text[:200]}")
    else:
        log(f"  Response: {r.text[:300]}")
    RESULT["endpoints"]["search"] = r.status_code == 200


def main():
    print("=" * 60)
    print("B站 API — 全面端点验证")
    print("=" * 60)

    test_popular()
    time.sleep(1)
    test_ranking()
    time.sleep(1)
    test_video_detail()
    time.sleep(1)
    test_comments()
    time.sleep(1)
    test_up_videos()
    time.sleep(1)
    test_up_info()
    time.sleep(1)
    test_search()
    time.sleep(1)

    CLIENT.close()

    # Summary
    print("\n" + "=" * 60)
    print("端点验证汇总:")
    for name, ok in RESULT["endpoints"].items():
        print(f"  {'✅' if ok else '❌'} {name}")

    out = Path(__file__).parent / "result.json"
    out.write_text(json.dumps(RESULT, indent=2, ensure_ascii=False))
    print(f"\n结果: {out}")


if __name__ == "__main__":
    main()
