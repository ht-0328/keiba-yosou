"""保存した予測と元DB から、材料表と帳簿を組み立てる（入口 ``backtest.py`` が使う）。

| クラス | 仕事 |
|---|---|
| ``MaterialsLoader`` | 予測の CSV（4つ）と事実表から ``RaceMaterials``（races と runners）を作る |
| ``MarketBooksLoader`` | 元DB から期間の確定オッズ・払戻・フラグを読み、``OddsBook`` と ``PayoutBook`` を作る |
| ``MarketBooks`` | ``OddsBook``・``PayoutBook`` と、読めた行数の数え上げを束ねた値 |
"""

from .market_books import MarketBooks
from .market_books_loader import MarketBooksLoader
from .materials_loader import MaterialsLoader

__all__ = ["MaterialsLoader", "MarketBooksLoader", "MarketBooks"]
