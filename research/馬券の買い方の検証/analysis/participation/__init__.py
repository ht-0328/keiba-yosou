"""参加パターン（どのレースを買い、広めと少点数のどちらで買うか）。

| クラス | 仕事 |
|---|---|
| ``Participation`` | 1行 = 1レースの（レースID, 広めで買うか, 少点数で買うか）を持つ値 |
| ``UpsetJudge`` | 荒れるレースか（券種に対応する「中荒れ以上の確率」がしきい値以上か）。順位付けの点も出す |
| ``ConfidenceJudge`` | 自信のあるレースか（本命の確率がしきい値以上、かつ本命の危険確率がしきい値未満）。順位付けの点も出す |
| ``RacePattern`` | 参加パターンの決まり（インターフェース）。``select`` で ``Participation`` を返し、``needs`` で要る軸を答える |
| ``PatternNeeds`` | そのパターンが探索の格子のどの軸（荒れ度・本命・危険・週の上位 k・広め・少点数）を使うか |
| ``AllRacesPattern`` | ①全レース。荒れ判定なら広め、そうでなければ少点数（片方に固定した版もある） |
| ``UpsetRacesPattern`` | ②荒れるレースだけ広め |
| ``ConfidentRacesPattern`` | ③自信のあるレースだけ少点数 |
| ``UnionPattern`` | ④荒れ → 広め、自信 → 少点数（両方なら両方買う） |
| ``WeeklyTopPattern`` | ⑤週ごとに上位 k レース（荒れる／自信／両方） |
| ``WeeklyWithGradedPattern`` | ⑥ ⑤に重賞を必ず足す（重賞は荒れ判定なら広め、そうでなければ少点数） |
| ``WeeklyMode`` | ⑤⑥の選び方（荒れる・自信・両方） |

一覧は ``patterns.py`` の ``PATTERNS``、鍵から引くのは ``pattern_by_key``。
"""

from .all_races_pattern import AllRacesPattern
from .confidence_judge import ConfidenceJudge
from .confident_races_pattern import ConfidentRacesPattern
from .participation import BUY_NARROW, BUY_WIDE, Participation
from .pattern_needs import PatternNeeds
from .patterns import PATTERNS, PATTERNS_BY_KEY, pattern_by_key
from .race_pattern import RacePattern
from .union_pattern import UnionPattern
from .upset_judge import UpsetJudge
from .upset_races_pattern import UpsetRacesPattern
from .weekly_mode import WeeklyMode
from .weekly_top_pattern import WeeklyTopPattern
from .weekly_with_graded_pattern import WeeklyWithGradedPattern

__all__ = [
    "Participation", "BUY_WIDE", "BUY_NARROW", "UpsetJudge", "ConfidenceJudge", "RacePattern", "PatternNeeds",
    "AllRacesPattern", "UpsetRacesPattern", "ConfidentRacesPattern", "UnionPattern", "WeeklyTopPattern",
    "WeeklyWithGradedPattern", "WeeklyMode", "PATTERNS", "PATTERNS_BY_KEY", "pattern_by_key",
]
