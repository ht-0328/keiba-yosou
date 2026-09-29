"""材料を足す部品。

| 名前 | 仕事 |
|---|---|
| ``RaceRelativeColumns`` | 数値の材料を、同じレースの馬と比べた値（平均との差・順位）にした列を足す |
| ``SalePriceFeatures`` | セリの取引価格（レースの日より前に終わったセリ）の列を足す |
| ``PreDeadlineOddsFeatures`` | 単勝オッズの4個と、馬連・複勝の支持の比を、締め切り前のオッズで作り直す |
"""

from .pre_deadline_odds_features import PreDeadlineOddsFeatures
from .race_relative_columns import RaceRelativeColumns
from .sale_price_features import SalePriceFeatures

__all__ = ["PreDeadlineOddsFeatures", "RaceRelativeColumns", "SalePriceFeatures"]
