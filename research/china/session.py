"""
中国平台登录态管理 — 共享 Session 工具

由于 WSL 环境无图形界面，采用"手动导出 Cookie"方式：
1. 用户在 Windows 浏览器登录目标网站
2. F12 → Application → Cookies → 复制 Cookie 值
3. 运行脚本，按提示粘贴 Cookie

Cookie 文件保存在 ~/.local/china_cookies/{site}.json
"""
import json, os
from pathlib import Path

COOKIE_DIR = Path.home() / ".local" / "china_cookies"
COOKIE_DIR.mkdir(parents=True, exist_ok=True)


def load_cookies(site: str) -> list[dict] | None:
    """加载已保存的 Cookie。返回 None 表示没有。"""
    path = COOKIE_DIR / f"{site}.json"
    if path.exists():
        return json.loads(path.read_text())
    return None


def save_cookies(site: str, cookies: list[dict]):
    """保存 Cookie 到文件。"""
    path = COOKIE_DIR / f"{site}.json"
    path.write_text(json.dumps(cookies, indent=2, ensure_ascii=False))
    print(f"  Cookie 已保存到 {path}")


def prompt_cookies(site: str, example_cookies: str = "") -> list[dict]:
    """
    交互式引导用户粘贴 Cookie。

    用户操作：
    1. 在浏览器登录 {site}
    2. F12 → Application → Cookies → 找到关键 Cookie
    3. 或者更简单：在 Console 执行以下代码并复制结果：

       JSON.stringify(document.cookie.split('; ').reduce((acc, c) => {
         const [k, v] = c.split('=');
         acc[k] = v;
         return acc;
       }, {}))
    """
    print(f"\n{'='*60}")
    print(f" 需要登录 {site}")
    print(f"{'='*60}")
    print()
    print(" 操作步骤：")
    print(f" 1. 在 Windows 浏览器打开并登录 {site}")
    print(f" 2. F12 打开 DevTools → Console 标签")
    print(f" 3. 粘贴以下代码，回车，复制输出的 JSON：")
    print()
    print('   JSON.stringify(document.cookie.split("; ").reduce((a,c)=>{const[p,...v]=c.split("=");a[p]=v.join("=");return a},{}))')
    print()
    print(f" 4. 把复制的 JSON 粘贴到下方（粘贴后按 Enter，然后 Ctrl+D 结束）：")
    print()

    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass

    cookie_json = "\n".join(lines).strip()
    if not cookie_json:
        print("  [跳过] 未提供 Cookie，退出。")
        return []

    try:
        cookie_dict = json.loads(cookie_json)
        cookies = [
            {"name": k, "value": v, "domain": _guess_domain(site)}
            for k, v in cookie_dict.items()
        ]
        save_cookies(site, cookies)
        print(f"  已解析 {len(cookies)} 个 Cookie")
        return cookies
    except json.JSONDecodeError as e:
        print(f"  JSON 解析失败: {e}")
        print(f"  原始输入: {cookie_json[:200]}")
        return []


def prompt_manual_cookies(site: str) -> list[dict]:
    """
    更灵活的手动输入方式：用户一条条输入 name=value。
    输入空行结束。
    """
    print(f"\n{'='*60}")
    print(f" 需要登录 {site} — 手动输入 Cookie")
    print(f"{'='*60}")
    print()
    print(f" 请在浏览器登录 {site} 后，F12 → Application → Cookies")
    print(f" 逐个输入关键 Cookie（格式: name=value），空行结束：")
    print()

    cookies = []
    while True:
        line = input("  Cookie> ").strip()
        if not line:
            break
        if "=" not in line:
            print("    格式错误，请用 name=value 格式")
            continue
        name, _, value = line.partition("=")
        cookies.append({
            "name": name.strip(),
            "value": value.strip(),
            "domain": _guess_domain(site),
        })

    if cookies:
        save_cookies(site, cookies)
        print(f"  已添加 {len(cookies)} 个 Cookie")
    else:
        print("  [跳过] 未提供任何 Cookie")
    return cookies


def _guess_domain(site: str) -> str:
    mapping = {
        "zhihu": ".zhihu.com",
        "xiaohongshu": ".xiaohongshu.com",
        "taobao": ".taobao.com",
        "1688": ".1688.com",
        "jd": ".jd.com",
        "pdd": ".yangkeduo.com",
        "baidu_index": ".baidu.com",
        "weibo": ".weibo.com",
    }
    return mapping.get(site, f".{site}.com")


def get_or_prompt_cookies(site: str) -> list[dict]:
    """加载已有 Cookie，没有则引导用户输入。"""
    cookies = load_cookies(site)
    if cookies:
        print(f"  已加载 {len(cookies)} 个已保存的 Cookie ({site})")
        return cookies
    return prompt_cookies(site)


def make_playwright_context(browser, site: str, cookies: list[dict]) -> object:
    """创建带 Cookie 的 Playwright context。"""
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        viewport={"width": 1920, "height": 1080},
    )
    if cookies:
        ctx.add_cookies(cookies)
    return ctx
