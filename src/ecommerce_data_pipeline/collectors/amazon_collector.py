"""
Amazon Collector — 从多个 Amazon 站点采集搜索页商品数据。

使用方式:
    from collectors.amazon_collector import AmazonCollector

    collector = AmazonCollector(market="jp", categories=["bluetooth speaker"], headless=True)
    products = collector.run()
"""
import re
from pathlib import Path
from typing import Optional

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from ..models.product import ProductInfo


AMAZON_MARKETS = {
    "us": {"domain": "amazon.com", "currency": "USD"},
    "au": {"domain": "amazon.com.au", "currency": "AUD"},
    "jp": {"domain": "amazon.co.jp", "currency": "JPY"},
    "sg": {"domain": "amazon.sg", "currency": "SGD"},
    "in": {"domain": "amazon.in", "currency": "INR"},
    "de": {"domain": "amazon.de", "currency": "EUR"},
    "fr": {"domain": "amazon.fr", "currency": "EUR"},
    "uk": {"domain": "amazon.co.uk", "currency": "GBP"},
    "ca": {"domain": "amazon.ca", "currency": "CAD"},
}

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"


class AmazonCollector:
    def __init__(
        self,
        market: str = "us",
        categories: Optional[list[str]] = None,
        headless: bool = True,
        timeout: int = 30000,
    ):
        if market not in AMAZON_MARKETS:
            raise ValueError(f"Unknown market: {market}. Available: {list(AMAZON_MARKETS)}")
        self.market = market
        self.market_info = AMAZON_MARKETS[market]
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
        domain = self.market_info["domain"]
        currency = self.market_info["currency"]
        url = f"https://www.{domain}/s?k={keyword.replace(' ', '+')}"

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=self.timeout)
        except Exception:
            return []

        page.wait_for_timeout(5000)

        if "captcha" in page.content().lower()[:2000]:
            return []

        soup = BeautifulSoup(page.content(), "lxml")
        items = soup.select('div[data-component-type="s-search-result"]')

        products = []
        for item in items:
            product = self._parse_item(item, keyword, currency, domain)
            if product:
                products.append(product)
        return products

    def _parse_item(self, item, category: str, currency: str, domain: str) -> Optional[ProductInfo]:
        asin = item.get("data-asin", "")
        if not asin:
            return None

        h2 = item.select_one("h2 span")
        title = h2.text.strip()[:200] if h2 else ""

        pw = item.select_one(".a-price-whole")
        pf = item.select_one(".a-price-fraction")
        price_text = (pw.text if pw else "") + (pf.text if pf else "")
        try:
            price = float(price_text.replace(",", "")) if price_text else None
        except ValueError:
            price = None

        rating_el = item.select_one(".a-icon-alt")
        rating = None
        if rating_el:
            text = rating_el.text.strip()
            # Amazon JP: "5つ星のうち4.4" -> 4.4
            m = re.search(r"([\d.]+)\s*out", text)
            if not m:
                m = re.search(r"のうち([\d.]+)", text)  # Amazon JP format
            if not m:
                m = re.search(r"([\d.]+)", text)  # fallback
            if m:
                rating = float(m.group(1))

        review_count = None
        # Try aria-label "1,069 ratings" first (most reliable)
        for el in item.select('[aria-label]'):
            aria = el.get("aria-label", "")
            m = re.search(r"([\d,]+)\s*(ratings|件)", aria)
            if m:
                try:
                    review_count = int(m.group(1).replace(",", ""))
                except ValueError:
                    pass
                break
        if review_count is None:
            # Fallback: old text-based approach
            reviews_el = (
                item.select_one("span.a-size-base.s-underline-text")
                or item.select_one('[data-cy="reviews-block"] span')
            )
            if reviews_el:
                txt = reviews_el.text.strip()
                m = re.search(r"([\d,]+)", txt)
                if m:
                    try:
                        review_count = int(m.group(1).replace(",", ""))
                    except ValueError:
                        pass

        product_url = f"https://www.{domain}/dp/{asin}"

        return ProductInfo(
            source=f"amazon_{self.market}",
            asin=asin,
            title=title,
            price=price,
            currency=currency,
            rating=rating,
            review_count=review_count,
            region=self.market.upper(),
            url=product_url,
            category=category,
        )
