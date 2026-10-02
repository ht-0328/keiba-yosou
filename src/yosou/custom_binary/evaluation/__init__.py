"""目的変数に対する確率の評価と、その確率で買った場合の回収率（設計書 16）。

| 名前 | 仕事 |
|---|---|
| ``ModelReport`` | 1つの期間での当たり具合と回収率をまとめて出す（学習の検証期間・テスト期間・研究で使う） |
| ``ProbabilityScores`` | 当たり具合（件数・正例率・ログ損失・Brier・AUC）を、モデルごとと人気ごとに出す |
| ``Paybacks`` | 対象の全頭・各レースの確率1位・期待値の線ごとに買った回収率 |
| ``BetResult`` | 選んだ馬を単勝・複勝1点100円ずつ買った結果 |
| ``BootstrapLowerBound`` | 回収率の下限（開催日を丸ごと取り直したときの90%の幅の下側） |
| ``ExpectedValue`` | 学習・評価のデータの期待値 |
| ``PlaceProbability`` | 学習・評価のデータの3着以内の確率（全頭がそろったレースは合計をそろえ直す） |
| ``PredictionValues`` | 予測した1レースの期待値とその材料（その時点のオッズで計算） |
| ``PlacePriceFit`` | 複勝の想定払戻倍率を、学習期間の払戻から求める |
| ``payback_rules.py`` | 1点の金額・期待値の線・複勝の払戻の頭数の決まり |
| ``evaluation_notes.py`` | 評価の表に添える注記 |
"""

from .bet_result import BetResult
from .bootstrap_lower_bound import BootstrapLowerBound
from .evaluation_notes import HISTORICAL_NOTE, PAYBACK_NOTE
from .expected_value import ExpectedValue
from .model_report import ModelReport
from .paybacks import Paybacks
from .place_price_fit import PlacePriceFit
from .place_probability import PlaceProbability
from .prediction_values import PredictionValues
from .probability_scores import ProbabilityScores

__all__ = [
    "BetResult", "BootstrapLowerBound", "ExpectedValue", "HISTORICAL_NOTE", "ModelReport", "PAYBACK_NOTE",
    "Paybacks", "PlacePriceFit", "PlaceProbability", "PredictionValues", "ProbabilityScores",
]
