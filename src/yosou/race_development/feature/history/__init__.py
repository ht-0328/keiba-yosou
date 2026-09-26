"""過去の記録から数える部品（開催日より前のものだけを使う決まりを、ここで守る。設計書 11 の 2・7）。

| クラス | 仕事 |
|---|---|
| ``RelativeRank`` | 順位と頭数から 0〜1 の値を出す（序盤・4コーナー・上がり・着順の物差しの、ただ1つの置き場所） |
| ``EarlyPosition`` | 最初のコーナーの順位から、序盤の位置（0〜1）と区分（先団・中団・後方）を出す |
| ``PaceBaseline`` | 前半・後半タイムの基準（前日までの3年の同じ条件のレースの平均と標準偏差）を付ける（基準の、ただ1つの置き場所） |
| ``RunLags`` | 出走の行ごとに、前日までの過去走を新しい順に横に並べる |
| ``LagStatistics`` | 横に並べた過去走の、平均・最小・ばらつき・重み付きの平均など |
| ``SmoothedRate`` | 走った数の少ない馬の割合を、全体の割合に寄せる |
| ``GlobalEarlyRate`` | 前日までの 365日の、全体の先頭率・先団率 |
| ``DailyRate`` | 騎手の日ごとの数から、前日までの 365日の割合を出す |
| ``EarlyRunSummary`` | 序盤の位置取りの履歴（K のうち 13個） |
| ``ClosingRunSummary`` | 末脚の履歴（N の 10個） |
| ``CourseHistory`` | コースごとの、前日までの 1095日のレースの記録のまとめ（M） |
| ``RaceBaselineLookup`` | レースごとの前半・後半タイムの基準を引く（予測するレースには基準を付け直す） |
"""

from .closing_run_summary import ClosingRunSummary
from .course_history import CORNER_COUNT, FIRST_CORNER, LEADER_POSITION, CourseHistory
from .daily_rate import DailyRate
from .early_position import EarlyPosition
from .early_run_summary import EarlyRunSummary
from .global_early_rate import GlobalEarlyRate
from .lag_statistics import LagStatistics
from .pace_baseline import (
    BASELINE_WINDOW_DAYS,
    COUNT,
    FIRST_HALF_BASELINE,
    MEAN,
    SECOND_HALF_BASELINE,
    STAGE,
    STD,
    PaceBaseline,
)
from .race_baseline_lookup import MEASURED_METERS, RaceBaselineLookup
from .relative_rank import RelativeRank
from .run_lags import RunLags
from .smoothed_rate import SmoothedRate

__all__ = [
    "RelativeRank", "EarlyPosition", "PaceBaseline", "RunLags", "LagStatistics", "SmoothedRate",
    "GlobalEarlyRate", "DailyRate", "EarlyRunSummary", "ClosingRunSummary", "CourseHistory", "RaceBaselineLookup",
    "BASELINE_WINDOW_DAYS", "FIRST_HALF_BASELINE", "SECOND_HALF_BASELINE", "MEAN", "STD", "COUNT", "STAGE", "MEASURED_METERS",
    "FIRST_CORNER", "CORNER_COUNT", "LEADER_POSITION",
]
