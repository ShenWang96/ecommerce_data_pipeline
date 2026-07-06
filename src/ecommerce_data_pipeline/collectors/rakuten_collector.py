"""
Rakuten JP Collector — 从楽天市場采集搜索页商品数据。
"""
import re
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from ..models.product import ProductInfo

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


class RakutenCollector:
    def __init__(
        self,
        categories: Optional[list[str]] = None,
        headless: bool = True,
        timeout: int = 30000,
    ):
        self.categories = categories or ["bluetooth speaker"]
        self.headless = headless
        self.timeout = timeout

    def run(self) -> list[ProductInfo]:
        all_products = []
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            ctx = browser.new_context(user_agent=UA, viewport={"width": 1920, "height": 1080})
            for category in self.categories:
                page = ctx.new_page()
                products = self._search(page, category)
                all_products.extend(products)
                page.close()
            browser.close()
        return all_products

    def _search(self, page, keyword: str) -> list[ProductInfo]:
        url = f"https://search.rakuten.co.jp/search/mall/{keyword.replace(' ', '+')}/"

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
        except Exception:
            return []

        page.wait_for_timeout(5000)
        soup = BeautifulSoup(page.content(), "lxml")
        items = soup.select(".searchresultitem")

        products = []
        for item in items:
            product = self._parse_item(item, keyword)
            if product:
                products.append(product)
        return products

    def _parse_item(self, item, category: str) -> Optional[ProductInfo]:
        title_el = item.select_one('[class*=title]')
        title = title_el.text.strip()[:200] if title_el else ""

        link_el = item.select_one("a[href*='item.rakuten']")
        url = link_el.get("href", "") if link_el else ""

        price = None
        for div in item.find_all("div", recursive=False):
            txt = div.get_text(strip=True)
            if "円" in txt and any(c.isdigit() for c in txt):
                m = re.search(r"([\d,]+)", txt)
                if m:
                    try:
                        price = float(m.group(1).replace(",", ""))
                    except ValueError:
                        pass
                break

        review_el = item.select_one('[class*=review]')
        rating = None
        review_count = None
        if review_el:
            review_text = review_el.text.strip()
            m_rating = re.search(r"([\d.]+)", review_text)
            if m_rating:
                rating = float(m_rating.group(1))
            m_reviews = re.search(r"\(([\d,]+)件\)", review_text)
            if m_reviews:
                try:
                    review_count = int(m_reviews.group(1).replace(",", ""))
                except ValueError:
                    pass

        return ProductInfo(
            source="rakuten_jp",
            asin=url.split("/")[-2] if url else "",
            title=title,
            price=price,
            currency="JPY",
            rating=rating,
            review_count=review_count,
            region="JP",
            url=url,
            category=category,
        )
