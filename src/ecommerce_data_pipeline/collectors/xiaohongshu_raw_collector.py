"""
小红书 RawCollector — 原始笔记数据落地。

采集:
  - 热门笔记 (Explore/发现页): 平台算法推荐的热门内容 (≈ 微博热搜/知乎热榜)
  - 热搜关键词: 搜索框下拉 trending searches
  - 搜索页: 特定关键词笔记 (保留，默认不使用)

特点:
  - 使用 Playwright stealth 模式绕过反爬
  - 可保存完整 HTML 快照 (默认关闭以节省空间)
  - 自动加载 Cookie
"""
import logging
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from ..models.raw_record import RawRecord, make_raw
from ..utils.cookies import auto_load, check_valid

logger = logging.getLogger("xiaohongshu")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

STEALTH_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox", "--disable-setuid-sandbox",
    "--disable-dev-shm-usage", "--window-size=1280,800",
    "--disable-default-apps", "--disable-extensions",
    "--disable-popup-blocking", "--password-store=basic",
]

STEALTH_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => false });
window.chrome = { runtime: {} };
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
"""


class XiaohongshuRawCollector:
    def __init__(
        self,
        cookies: list[dict] | None = None,
        headless: bool = True,
        timeout: int = 60000,
        wait_seconds: int = 5,
        save_html: bool = False,
        user_data_dir: Optional[Path] = None,
    ):
        if cookies is None:
            cookies = auto_load("xiaohongshu")
        self.cookies = cookies
        self.headless = headless
        self.timeout = timeout
        self.wait_seconds = wait_seconds
        self.save_html = save_html
        self.user_data_dir = str(user_data_dir or (Path.home() / ".local" / "xhs-stealth-profile"))

    @classmethod
    def check_ready(cls) -> bool:
        info = check_valid("xiaohongshu")
        return info["exists"] and len(info["key_cookies"]) >= 3

    def _new_browser_and_context(self):
        p = sync_playwright().start()
        ctx = p.chromium.launch_persistent_context(
            self.user_data_dir,
            headless=self.headless,
            args=STEALTH_ARGS,
            user_agent=UA,
            viewport={"width": 1280, "height": 800},
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            geolocation={"latitude": 31.2304, "longitude": 121.4737},
            permissions=["geolocation"],
        )
        ctx.add_init_script(STEALTH_SCRIPT)
        if self.cookies:
            ctx.add_cookies(self.cookies)
        return p, ctx

    def collect_search(self, keyword: str, limit: int = 30) -> list[RawRecord]:
        """搜索笔记 — 完整标题+作者+URL+图片URL"""
        records = []
        p, ctx = self._new_browser_and_context()
        page = ctx.new_page()
        try:
            url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&source=web_search_result_notes"
            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(self.wait_seconds * 1000)

            html_content = page.content() if self.save_html else ""
            soup = BeautifulSoup(page.content(), "lxml")

            for item in soup.select("section.note-item")[:limit]:
                # 标题
                title_el = item.select_one(".title span") or item.select_one('[class*=title] span')
                title = title_el.get_text(strip=True)[:200] if title_el else ""

                # 作者
                author_el = item.select_one('[class*=author] .name') or item.select_one('.name')
                author = author_el.get_text(strip=True)[:50] if author_el else ""

                # 链接
                link_el = item.select_one("a[href*='/explore/']") or item.select_one("a[href*='/search_result/']")
                href = link_el.get("href", "") if link_el else ""
                note_url = f"https://www.xiaohongshu.com{href}" if href.startswith("/") else href
                note_id = href.split("/")[-1] if href else ""

                # 图片URL
                img_urls = []
                for img in item.select("img[src]"):
                    src = img.get("src", "") or img.get("data-src", "")
                    if src and "http" in src:
                        img_urls.append(src)

                # 封面
                cover_el = item.select_one(".cover img") or item.select_one("img[class*=cover]")
                cover = (cover_el.get("src") or cover_el.get("data-src", "")) if cover_el else ""
                if not cover and img_urls:
                    cover = img_urls[0]

                # 互动数据
                likes = _parse_count(item.select_one('[class*=like] span') or item.select_one('[class*=count]'))
                comments = _parse_count(item.select_one('[class*=comment] span'))

                if not title:
                    continue

                records.append(make_raw(
                    source="xiaohongshu",
                    record_type="note",
                    item_id=note_id,
                    url=note_url,
                    title=title,
                    author_name=author,
                    cover_url=cover,
                    images=img_urls,
                    likes=likes,
                    comments_count=comments,
                    html_snapshot=html_content if self.save_html else "",
                    extra={
                        "keyword": keyword,
                        "rank": 0,
                    },
                ))
        except Exception as e:
            logger.warning(f"search error: {e}")
        finally:
            page.close(); ctx.close(); p.stop()
        return records

    def collect_explore(self, limit: int = 80, scroll_times: int = 5) -> list[RawRecord]:
        """热门笔记 — 发现页推荐流。
        
        双通道采集:
          1. 拦截 /api/sns/web/v1/homefeed JSON 响应 (结构化，含互动数据)
          2. 回退: BeautifulSoup DOM 解析 (保底)
        """
        records = []
        seen = set()
        api_notes = []
        p, ctx = self._new_browser_and_context()
        page = ctx.new_page()
        try:
            # 拦截 homefeed API 响应
            def on_response(response):
                if "/api/sns/web/v1/homefeed" in response.url:
                    try:
                        data = response.json()
                        for item in data.get("data", {}).get("items", []):
                            api_notes.append(item)
                    except Exception:
                        pass

            page.on("response", on_response)

            page.goto("https://www.xiaohongshu.com/explore",
                      wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(self.wait_seconds * 1000)

            for _ in range(scroll_times):
                page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                page.wait_for_timeout(2000)

            page.wait_for_timeout(1000)

            # 通道1: 从拦截的 API 数据中提取
            for item in api_notes:
                if len(records) >= limit:
                    break
                note = item.get("note_card") or item
                note_id = item.get("id", "")
                if not note_id or note_id in seen:
                    continue

                title = note.get("display_title", "") or note.get("title", "")
                if not title:
                    continue
                seen.add(note_id)

                # 作者信息
                user = note.get("user", {}) or note.get("interact_info", {}).get("user", {})
                author = user.get("nickname", "") or user.get("nick_name", "")

                # 互动数据
                interact = note.get("interact_info", {})
                likes = _parse_count_str(interact.get("liked_count", "0"))
                comments = _parse_count_str(interact.get("comment_count", "0"))

                # 图片
                cover = note.get("cover", {})
                cover_url = cover.get("url", "") if isinstance(cover, dict) else str(cover)
                img_urls = []
                if cover_url:
                    img_urls.append(cover_url)
                for img in note.get("image_list", []):
                    u = img.get("url", "") if isinstance(img, dict) else str(img)
                    if u:
                        img_urls.append(u)

                # tag
                tag_list = []
                for tag in note.get("tag_list", []):
                    t = tag.get("name", "") if isinstance(tag, dict) else str(tag)
                    if t:
                        tag_list.append(t)

                records.append(make_raw(
                    source="xiaohongshu",
                    record_type="note",
                    item_id=note_id,
                    url=f"https://www.xiaohongshu.com/explore/{note_id}",
                    title=title,
                    author_name=author,
                    cover_url=cover_url,
                    images=img_urls,
                    likes=likes,
                    comments_count=comments,
                    html_snapshot="",
                    api_response=note,
                    extra={
                        "source_tab": "explore",
                        "tags": tag_list,
                        "collected_via": "api_intercept",
                    },
                ))

            # 通道2: DOM 回退（如果 API 数据不够）
            if len(records) < limit:
                soup = BeautifulSoup(page.content(), "lxml")
                for item in soup.select("section.note-item"):
                    if len(records) >= limit:
                        break

                    title_el = item.select_one(".title span")
                    title = title_el.get_text(strip=True)[:200] if title_el else ""
                    author_el = item.select_one('.name')
                    author = author_el.get_text(strip=True)[:50] if author_el else ""
                    link_el = item.select_one("a[href*='/explore/']")
                    href = link_el.get("href", "") if link_el else ""
                    note_url = f"https://www.xiaohongshu.com{href}" if href.startswith("/") else href
                    note_id = href.split("/")[-1] if href else ""

                    if not title or note_id in seen:
                        continue
                    seen.add(note_id)

                    img_urls = []
                    for img in item.select("img[src]"):
                        src = img.get("src", "") or img.get("data-src", "")
                        if src and "http" in src:
                            img_urls.append(src)
                    cover = img_urls[0] if img_urls else ""

                    records.append(make_raw(
                        source="xiaohongshu",
                        record_type="note",
                        item_id=note_id,
                        url=note_url,
                        title=title,
                        author_name=author,
                        cover_url=cover,
                        images=img_urls,
                        html_snapshot="",
                        extra={
                            "source_tab": "explore",
                            "collected_via": "dom_fallback",
                        },
                    ))

            logger.info(f"explore: {len(records)} notes (api={len(api_notes)}, dom_fallback={len(records)-min(len(api_notes),len(records))})")
        except Exception as e:
            logger.warning(f"explore error: {e}")
        finally:
            page.close(); ctx.close(); p.stop()
        return records

    def collect_trending_searches(self, limit: int = 30, explore_records: list[RawRecord] | None = None) -> list[RawRecord]:
        """热搜关键词 — "猜你想搜" / trending searches.
        
        策略:
          1. 尝试点击搜索区域触发 suggestion 面板 (需登录态)
          2. 如登录态不可用，从 explore 笔记标题中提取高频关键词作为 fallback
        
        Args:
            limit: 最多返回条数
            explore_records: explore 采集的笔记记录（用于 fallback 关键词提取）
        """
        records = []
        p, ctx = self._new_browser_and_context()
        page = ctx.new_page()
        try:
            page.goto("https://www.xiaohongshu.com/explore",
                      wait_until="domcontentloaded", timeout=self.timeout)
            page.wait_for_timeout(3000)

            # 检测登录态：搜索框 placeholder 是否为 "登录探索更多内容"
            ph = page.evaluate("document.getElementById('search-input')?.placeholder || ''")
            is_guest = "登录" in ph
            has_login_modal = page.query_selector('.login-modal, [class*=login-container]') is not None

            if is_guest or has_login_modal:
                logger.info(f"trending_search: XHS treats session as guest (placeholder='{ph}'), skipping web UI search")
                page.close(); ctx.close(); p.stop()
                # fallback: 从 explore 笔记提取关键词
                return self._extract_keywords_from_notes(explore_records or [], limit)

            # 已登录: 尝试点击搜索区域触发 suggestion 面板
            clicked = False
            for selector in ['#search-input', '.search-area', '[class*=search-area]',
                             '.wendian-wrapper', '[class*=wendian]', 'textarea']:
                el = page.query_selector(selector)
                if el:
                    try:
                        el.click(force=True, timeout=5000)
                        clicked = True
                        break
                    except Exception:
                        continue
            if not clicked:
                logger.info("trending_search: could not trigger search area")
                page.close(); ctx.close(); p.stop()
                return self._extract_keywords_from_notes(explore_records or [], limit)

            page.wait_for_timeout(3000)

            soup = BeautifulSoup(page.content(), "lxml")
            items = soup.select('.suggestion-item, [class*=suggestion] [class*=item]')
            if not items:
                section = soup.select_one('[class*=suggestion-section], [class*=suggest]')
                if section:
                    items = section.find_all(['div', 'span'])

            seen_terms = set()
            for el in items[:limit]:
                content_el = el.select_one('[class*=content]') or el.select_one('[class*=desc]')
                term = content_el.get_text(strip=True) if content_el else el.get_text(strip=True)

                if not term or len(term) < 2 or len(term) > 30:
                    continue
                if term in seen_terms or term == "猜你想搜":
                    continue
                if term.isdigit() or all(c in '0123456789., #' for c in term):
                    continue
                seen_terms.add(term)

                records.append(make_raw(
                    source="xiaohongshu",
                    record_type="topic",
                    item_id=f"trending_search_{hash(term) & 0x7FFFFFFF}",
                    url=f"https://www.xiaohongshu.com/search_result?keyword={term}",
                    title=term,
                    html_snapshot="",
                    extra={
                        "source_tab": "trending_search",
                        "rank": len(records),
                        "collected_via": "web_suggestion",
                    },
                ))
            
            logger.info(f"trending_search: {len(records)} keywords via web suggestion")
        except Exception as e:
            logger.warning(f"trending_search error: {e}")
        finally:
            try:
                page.close(); ctx.close(); p.stop()
            except Exception:
                pass

        # 如果 web suggestion 没拿到，用 fallback
        if not records and explore_records:
            records = self._extract_keywords_from_notes(explore_records, limit)

        return records

    def _extract_keywords_from_notes(self, notes: list[RawRecord], limit: int = 20) -> list[RawRecord]:
        """从笔记标题中提取高频关键词作为热搜 fallback。
        
        使用 n-gram 频率分析，提取出现≥2次的 2-5 字词组。
        同时保留所有标题中的完整话题标记（#xxx#）。
        """
        import re
        from collections import Counter

        titles = [r.title for r in notes if r.title]
        if not titles:
            logger.info("keyword_fallback: no titles to extract from")
            return []

        try:
            import jieba
            import jieba.analyse
            use_jieba = True
        except ImportError:
            use_jieba = False
            logger.info("keyword_fallback: jieba not available, using n-gram fallback")

        word_freq = Counter()
        for title in titles:
            # 1. 提取话题标记 #xxx#
            for tag in re.findall(r'#([^#]+)#', title):
                word_freq[tag.strip()] += 3  # 话题标记加权
            if use_jieba:
                # jieba 分词
                words = jieba.cut(title)
                for w in words:
                    w = w.strip()
                    if len(w) >= 2 and not w.isdigit():
                        word_freq[w] += 1
            else:
                # n-gram 回退
                cn = re.findall(r'[\u4e00-\u9fa5]+', title)
                for seg in cn:
                    for n in range(2, min(len(seg) + 1, 6)):
                        for i in range(len(seg) - n + 1):
                            word_freq[seg[i:i+n]] += 1
            # 英文词
            for w in re.findall(r'[A-Za-z]{3,}', title):
                word_freq[w.lower()] += 1

        stopwords = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一个',
                     '什么', '怎么', '可以', '这个', '那个', '真的', '不是', '没有', '觉得',
                     '应该', '还是', '其实', '比较', '已经', '如果', '这是', '看看', '大家',
                     '你们', '我们', '他们', '真的', '太香', '一个', '不知道', '怎么办',
                     '给你们', '的时候', '的时候', '出来', '真是', '看到', '一定要',
                     '分享', '推荐', '真的', '可以', '这个', '那个', '我们的', '他们的'}
        hot_words = [(w, c) for w, c in word_freq.most_common(limit * 5)
                     if c >= 2 and w not in stopwords and len(w) >= 2 and len(w) <= 15]

        # 去重: 如果短词是长词的子串，且频率相同，则去掉短词
        filtered = []
        for w, c in hot_words:
            is_substr = any(w != w2 and w in w2 and c2 >= c for w2, c2 in hot_words)
            if not is_substr:
                filtered.append((w, c))
        hot_words = filtered[:limit]

        records = []
        for rank, (word, count) in enumerate(hot_words):
            records.append(make_raw(
                source="xiaohongshu",
                record_type="topic",
                item_id=f"keyword_{hash(word) & 0x7FFFFFFF}",
                url=f"https://www.xiaohongshu.com/search_result?keyword={word}",
                title=word,
                body=f"在推荐流中出现 {count} 次",
                html_snapshot="",
                extra={
                    "source_tab": "keyword_fallback",
                    "rank": rank,
                    "frequency": count,
                    "collected_via": "keyword_extraction",
                },
            ))

        logger.info(f"keyword_fallback: extracted {len(records)} keywords from {len(titles)} note titles")
        return records

    def collect_all(self, keywords: list[str] | None = None) -> list[RawRecord]:
        # 1. 推荐流笔记（有信息量）
        records = self.collect_explore(limit=80, scroll_times=5)
        # 2. 热搜关键词（代表热点），传入 explore 记录用于 fallback
        trending = self.collect_trending_searches(limit=30, explore_records=records)
        records.extend(trending)
        return records


def _parse_count(el) -> int:
    if not el: return 0
    txt = el.get_text(strip=True)
    return _parse_count_str(txt)


def _parse_count_str(txt: str) -> int:
    if not txt: return 0
    txt = str(txt).replace(",", "").replace(" ", "")
    if "万" in txt:
        try: return int(float(txt.replace("万", "")) * 10000)
        except: pass
    try: return int(txt)
    except: return 0
