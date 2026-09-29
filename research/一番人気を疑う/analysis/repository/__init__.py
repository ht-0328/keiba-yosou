"""元DB から読む部品（1クラス1 SQL）。

| 名前 | 仕事 |
|---|---|
| ``SalePriceRepository`` | 競走馬の市場取引価格（hs）を、馬ごとに読む |
"""

from .sale_price_repository import SalePriceRepository

__all__ = ["SalePriceRepository"]
