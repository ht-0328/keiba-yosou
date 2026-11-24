"""当たり具合を測る。

| 名前 | 仕事 |
|---|---|
| ``MarketComparison`` | 検証データでの対数損失を、モデルごと・2つの平均・市場の確率で出して比べる |
| ``YearlyPickSummary`` | 年ごとの予測から、買い目の決まりで選んだ組の年ごとの点数・的中数・回収率を数える |
| ``weighted_log_loss()`` | 行の重みを付けた対数損失 |
"""

from .log_loss import weighted_log_loss
from .market_comparison import AVERAGE, MARKET, SCALED_MARKET, MarketComparison
from .yearly_pick_summary import YearlyPickSummary

__all__ = ["MarketComparison", "AVERAGE", "MARKET", "SCALED_MARKET", "YearlyPickSummary", "weighted_log_loss"]
