#!/usr/bin/env python3
"""
扫码登录 — 支持 知乎/微博/小红书

Headless 模式：截图二维码 → 用户手机扫码 → 自动检测登录 → 保存 Cookie

用法:
    python3 scripts/qr_login.py zhihu
    python3 scripts/qr_login.py weibo
    python3 scripts/qr_login.py xiaohongshu
"""
import sys
import os
import time
import json
from pathlib import Path

os.environ.setdefault("LD_LIBRARY_PATH", os.path.expanduser("~/.local/playwright-libs"))

from playwright.sync_api import sync_playwright

COOKIE_DIR = Path.home() / ".local" / "china_cookies"
COOKIE_DIR.mkdir(parents=True, exist_ok=True)

# 各平台配置
PLATFORMS = {
    "zhihu": {
        "login_url": "https://www.zhihu.com/signin",
        "verify_url": "https://www.zhihu.com/hot",
        "qr_selector": ".Qrcode-container",
        "profile_dir": "~/.local/zhihu-stealth-profile",
        "check_logged_in": lambda url: "signin" not in url and "zhihu.com" in url,
        "verify_text": ["热度", "热榜"],
        "cookie_file": "zhihu.json",
        "key_cookies": ["z_c0", "d_c0", "_zap"],
    },
    "weibo": {
        "login_url": "https://weibo.com/login.php",
        "verify_url": "https://weibo.com",
        "qr_selector": "canvas, .qrcode, img[src*='qrcode'], [class*='qr']",
        "profile_dir": "~/.local/weibo-stealth-profile",
        "check_logged_in": lambda url: "login" not in url and "weibo.com" in url,
        "verify_text": ["热搜", "微博"],
        "cookie_file": "weibo.json",
        "key_cookies": ["SUB", "SUBP"],
    },
    "xiaohongshu": {
        "login_url": "https://www.xiaohongshu.com/explore",
        "verify_url": "https://www.xiaohongshu.com/explore",
        "qr_selector": "#qr-container, .qr-container, canvas, [class*='qr'], [class*='login']",
        "profile_dir": "~/.local/xhs-stealth-profile",
        "check_logged_in": lambda url: True,
        "verify_text": ["笔记", "发现"],
        "cookie_file": "xiaohongshu.json",
        "key_cookies": ["a1", "web_session", "webId"],
    },
    "hupu": {
        "login_url": "https://passport.hupu.com/login",
        "verify_url": "https://bbs.hupu.com/all-gambia",
        "qr_selector": "canvas, .qrcode, img[src*='qrcode'], [class*='qr'], [class*='scan']",
        "profile_dir": "~/.local/hupu-stealth-profile",
        "check_logged_in": lambda url: "passport" not in url and "hupu.com" in url,
        "verify_text": ["步行街", "热帖", "帖子"],
        "cookie_file": "hupu.json",
        "key_cookies": ["u", "passport_csrf_token"],
    },
}


def stealth_init(page):
    """注入反自动化检测脚本"""
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        window.chrome = { runtime: {} };
        Object.defineProperty(navigator, 'plugins', { get: () => [1,2,3,4,5] });
        Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN','zh','en'] });
    """)


def login(platform_name: str, timeout: int = 180):
    cfg = PLATFORMS[platform_name]
    profile_dir = os.path.expanduser(cfg["profile_dir"])
    cookie_path = COOKIE_DIR / cfg["cookie_file"]
    
    print(f"\n{'='*50}")
    print(f"  {platform_name} 扫码登录")
    print(f"{'='*50}\n")
    
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            profile_dir,
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
            ],
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
            locale='zh-CN',
        )
        page = ctx.new_page()
        stealth_init(page)
        
        # 打开登录页
        print(f"正在打开 {platform_name} 登录页...")
        page.goto(cfg["login_url"], wait_until="domcontentloaded", timeout=30000)
        time.sleep(4)
        
        # 截取二维码
        qr_path = f"/tmp/{platform_name}_qrcode.png"
        full_path = f"/tmp/{platform_name}_login_full.png"
        
        qr_el = page.query_selector(cfg["qr_selector"])
        if qr_el:
            qr_el.screenshot(path=qr_path)
            print(f"✓ 二维码截图: {qr_path}")
            box = qr_el.bounding_box()
            print(f"  区域: {box['width']:.0f}x{box['height']:.0f}")
        else:
            print(f"⚠ 未找到二维码元素 ({cfg['qr_selector']})，截取全页...")
            page.screenshot(path=full_path)
            qr_path = full_path
        
        # 等待登录成功
        print(f"\n⏳ 等待扫码登录... (超时 {timeout}s)")
        print(f"   请用手机 {platform_name} APP 扫描二维码\n")
        
        start = time.time()
        logged_in = False
        
        while time.time() - start < timeout:
            time.sleep(2)
            elapsed = int(time.time() - start)
            current_url = page.url
            
            # 方法1: URL 跳转检测
            if cfg["check_logged_in"](current_url) and current_url != cfg["login_url"]:
                print(f"  [{elapsed}s] 检测到页面跳转: {current_url}")
                logged_in = True
                break
            
            # 方法2: Cookie 变化检测
            cookies = ctx.cookies()
            key_found = [k for k in cfg["key_cookies"] if any(c["name"] == k for c in cookies)]
            if len(key_found) >= 2:
                print(f"  [{elapsed}s] 检测到关键 Cookie: {', '.join(key_found)}")
                logged_in = True
                break
            
            # 每 10 秒打印一次状态
            if elapsed % 10 == 0 and elapsed > 0:
                print(f"  [{elapsed}s] 等待中... (当前 Cookie 数: {len(cookies)})")
        
        if not logged_in:
            # 最后检查一次 cookie
            cookies = ctx.cookies()
            key_found = [k for k in cfg["key_cookies"] if any(c["name"] == k for c in cookies)]
            if len(key_found) >= 1:
                print(f"\n  超时但发现部分关键 Cookie: {key_found}")
                logged_in = True
        
        if logged_in:
            # 等页面完全加载
            time.sleep(3)
            
            # 尝试访问验证页
            print(f"\n验证登录状态...")
            try:
                page.goto(cfg["verify_url"], wait_until="domcontentloaded", timeout=15000)
                time.sleep(3)
                body_text = page.inner_text("body")
                has_content = any(t in body_text for t in cfg["verify_text"])
                if has_content:
                    print(f"  ✓ 验证页内容正常")
                else:
                    print(f"  ⚠ 验证页内容异常")
            except Exception as e:
                print(f"  ⚠ 验证页访问失败: {e}")
            
            # 保存 Cookie
            cookies = ctx.cookies()
            cookie_path.write_text(json.dumps(cookies, indent=2, ensure_ascii=False))
            
            key_found = [k for k in cfg["key_cookies"] if any(c["name"] == k for c in cookies)]
            
            print(f"\n{'='*50}")
            print(f"  ✅ 登录成功!")
            print(f"  Cookie 文件: {cookie_path}")
            print(f"  Cookie 数量: {len(cookies)}")
            print(f"  关键 Cookie: {', '.join(key_found) if key_found else '未检测到'}")
            print(f"{'='*50}")
        else:
            print(f"\n❌ 登录超时 ({timeout}s)，请重试")
        
        ctx.close()
        return logged_in


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in PLATFORMS:
        print(f"用法: python3 {sys.argv[0]} <platform>")
        print(f"支持: {', '.join(PLATFORMS.keys())}")
        sys.exit(1)
    
    platform = sys.argv[1]
    timeout = int(sys.argv[2]) if len(sys.argv) > 2 else 180
    success = login(platform, timeout)
    sys.exit(0 if success else 1)
