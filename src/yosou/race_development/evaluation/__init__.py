"""当たり具合を測る（設計書 16）。

| クラス | 仕事 |
|---|---|
| ``RaceMetrics`` | レースの中で見る指標（レースごとのログ損失・確率1位の的中・順位相関・多クラスのログ損失）をまとめて計算する |
| ``StageYearMetrics`` | ①〜⑥ の、年ごとの当たり具合と簡単な基準（年ごとの確かめの表4） |
| ``StageBaselines`` | ①〜③ のモデルによらない基準（割合は、その年より前の年で数える） |
| ``FinishYearMetrics`` | ⑦ の、年ごとの当たり具合（年ごとの確かめの表3） |
| ``PlaceCalibration`` | 3着以内の確率の、帯ごとの実際の割合 |

券種ごとの的中率と回収率（表1・表2）は、``betting/`` の ``ReturnSummary`` が出す。
"""

from .finish_year_metrics import FinishYearMetrics
from .place_calibration import TOP3_PROBABILITY, PlaceCalibration
from .race_metrics import RaceMetrics
from .stage_baselines import StageBaselines
from .stage_year_metrics import KIND, METRIC, RECENT_CLOSING, RECENT_CORNER4, VALUE, YEAR, StageYearMetrics

__all__ = [
    "RaceMetrics", "StageYearMetrics", "StageBaselines", "FinishYearMetrics", "PlaceCalibration",
    "YEAR", "KIND", "METRIC", "VALUE", "RECENT_CORNER4", "RECENT_CLOSING", "TOP3_PROBABILITY",
]
