from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


@dataclass
class ProductInfo:
    source: str
    asin: str
    title: str
    price: Optional[float]
    currency: str
    rating: Optional[float]
    review_count: Optional[int]
    region: str
    url: str
    category: str
    scraped_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["scraped_at"] = d["scraped_at"].isoformat()
        return d
