"""
统一 Cookie 管理 — 多平台登录态持久化。

存储位置: ~/.local/china_cookies/{site}.json
支持格式:
  1. Playwright 完整格式 (含 domain/path/httpOnly/secure/sameSite/expires)
  2. 简化格式 {name: value} (从浏览器 document.cookie 导出)

用法:
    from utils.cookies import load, save, auto_load

    cookies = auto_load("xiaohongshu")  # 自动检测格式并加载
"""
import json
import re
from pathlib import Path
from typing import Optional

COOKIE_DIR = Path.home() / ".local" / "china_cookies"
COOKIE_DIR.mkdir(parents=True, exist_ok=True)

DOMAIN_MAP = {
    "zhihu": ".zhihu.com",
    "xiaohongshu": ".xiaohongshu.com",
    "xhs": ".xiaohongshu.com",
    "weibo": ".weibo.com",
    "taobao": ".taobao.com",
    "jd": ".jd.com",
    "1688": ".1688.com",
    "pdd": ".yangkeduo.com",
    "baidu": ".baidu.com",
    "bilibili": ".bilibili.com",
}


def path_for(site: str) -> Path:
    return COOKIE_DIR / f"{site}.json"


def load_raw(site: str) -> Optional[list[dict]]:
    """加载原始 cookie 数据，不做格式转换。返回 None 表示文件不存在。"""
    p = path_for(site)
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text())
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return [data]
    except (json.JSONDecodeError, ValueError):
        pass
    return None


def save(site: str, cookies: list[dict]):
    """保存 Cookie 到标准位置。"""
    p = path_for(site)
    p.write_text(json.dumps(cookies, indent=2, ensure_ascii=False))


def _detect_format(cookies: list[dict]) -> str:
    """检测 Cookie 格式: 'playwright' 或 'simple'"""
    if not cookies:
        return "simple"
    first = cookies[0]
    if "name" in first and "value" in first and "domain" in first:
        return "playwright"
    return "simple"


def _normalize_domain(domain: str) -> str:
    """确保 domain 以 . 开头"""
    if domain and not domain.startswith("."):
        return f".{domain}"
    return domain


def simple_to_playwright(cookies: list[dict], site: str) -> list[dict]:
    """
    将简化格式 {name: value} 或 [{name: key, value: val}] 转换为 Playwright 格式。
    """
    domain = DOMAIN_MAP.get(site, f".{site}.com")
    result = []
    for c in cookies:
        if isinstance(c, dict) and "name" in c and "value" in c:
            result.append({
                "name": c["name"],
                "value": c["value"],
                "domain": _normalize_domain(c.get("domain", domain)),
                "path": c.get("path", "/"),
                "httpOnly": c.get("httpOnly", False),
                "secure": c.get("secure", True),
                "sameSite": c.get("sameSite", "Lax"),
            })
        elif isinstance(c, dict):
            # {name: value} dict — flatten
            for k, v in c.items():
                if not k.startswith("_"):
                    result.append({
                        "name": k,
                        "value": str(v),
                        "domain": domain,
                        "path": "/",
                        "httpOnly": False,
                        "secure": True,
                        "sameSite": "Lax",
                    })
    return result


def auto_load(site: str, format: str = "playwright") -> Optional[list[dict]]:
    """
    自动检测格式并加载 Cookie。
    
    Args:
        site: 平台名 (xiaohongshu, weibo, zhihu 等)
        format: 返回格式 — 'playwright' 或 'simple'
    
    Returns:
        Playwright 格式的 cookie 列表，或 None
    """
    cookies = load_raw(site)
    if not cookies:
        return None

    fmt = _detect_format(cookies)

    if format == "playwright":
        if fmt == "simple":
            return simple_to_playwright(cookies, site)
        return cookies
    elif format == "simple":
        if fmt == "playwright":
            return [{c["name"]: c["value"]} for c in cookies]
        return cookies

    return cookies


def check_valid(site: str) -> dict:
    """
    检查 cookie 文件是否有效。
    
    Returns:
        {"exists": bool, "format": str, "count": int, "key_cookies": list}
    """
    cookies = load_raw(site)
    if not cookies:
        return {"exists": False, "format": "none", "count": 0, "key_cookies": [], "missing_keys": []}

    fmt = _detect_format(cookies)

    # Extract cookie names
    if fmt == "playwright":
        names = [c.get("name", "") for c in cookies if isinstance(c, dict)]
    else:
        names = list(cookies[0].keys()) if isinstance(cookies[0], dict) else []

    # Known critical cookies per site
    key_map = {
        "xiaohongshu": ["a1", "web_session", "websectiga", "acw_tc", "webId"],
        "weibo": ["SUB", "SUBP", "login_sid_t"],
        "zhihu": ["z_c0", "d_c0", "zst_82"],
    }
    expected = key_map.get(site, [])
    found = [n for n in expected if n in names]

    missing = [n for n in expected if n not in names]
    return {
        "exists": True,
        "format": fmt,
        "count": len(cookies),
        "key_cookies": found,
        "missing_keys": missing,
    }
