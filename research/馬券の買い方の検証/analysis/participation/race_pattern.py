"""参加パターンの決まり。"""

from __future__ import annotations

from typing import Protocol

import pandas as pd

from yosou.upset_level.dataset import BetType

from .confidence_judge import ConfidenceJudge
from .participation import Participation
from .pattern_needs import PatternNeeds
from .upset_judge import UpsetJudge


class RacePattern(Protocol):
    """参加パターン。``races``（材料表の1行 = 1レース）から、買うレースと広め・少点数の別を決める。

    - ``key``: 戦略の名前に使う短い鍵（``01all`` など）。``label``: 表に出す名前。
    - ``needs``: 探索の格子のどの軸を使うか。
    - ``select``: ``wide_bet`` は広めの買い方の券種に対応する荒れ具合の券種、``top_k`` は週の上位 k（使わないパターンでは無視）。
    """

    @property
    def key(self) -> str:
        ...

    @property
    def label(self) -> str:
        ...

    @property
    def needs(self) -> PatternNeeds:
        ...

    def select(self, races: pd.DataFrame, upset: UpsetJudge, confidence: ConfidenceJudge, wide_bet: BetType,
               top_k: int | None) -> Participation:
        ...
