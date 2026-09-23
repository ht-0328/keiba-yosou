"""精算表から回収率などをまとめ、表にする。

| クラス | 仕事 |
|---|---|
| ``ReturnSummary`` | 精算表の行の集まりからの、回収率のまとめ（レース数・点数・賭け金・払戻・的中レース率・最大を除く回収率） |
| ``PlanSummaryTables`` | 買い方ごとの回収率の表と、見送りの理由の内訳の表（``--settle-only`` の出力） |
| ``StrategyTables`` | 探索・確認の結果の表（戦略ごとの回収率、採用候補の月別、基準の買い方） |
"""

from .plan_summary_tables import PlanSummaryTables, rate_text
from .return_summary import ReturnSummary

__all__ = ["ReturnSummary", "PlanSummaryTables", "rate_text"]
