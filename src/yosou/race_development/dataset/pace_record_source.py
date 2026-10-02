"""レースごとの前半・後半タイムと、その基準を読む。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from yosou.shared.repository import RaceEarlyRecordRepository, TargetScope

from ..feature.history import RaceBaselineLookup


class PaceRecordSource:
    """``RaceResultSource`` を守る。レースごとの記録に、前半と後半のタイムの基準を付けて返す（設計書 04 の「dataset/」）。

    ``RaceDatasetBuilder`` が読む「レースごとの結果」の表になる。③⑥の目的変数と、Q・U の特徴量の元。
    基準を作るために、``first_day`` の 1095日前からのレースを読む（``RaceEarlyRecordRepository`` の窓）。
    """

    def __init__(self, repository: RaceEarlyRecordRepository) -> None:
        self._repository = repository
        self._baselines = RaceBaselineLookup()

    def read(self, first_day: date) -> pd.DataFrame:
        """開催日が ``first_day`` の 1095日前以降のレース（1行 = 1レース）。列は ``RaceEarlyRecordRepository`` の列と、
        前半・後半の基準の4列ずつ、測る区間。
        """
        races = self._repository.read(TargetScope.since(first_day))
        return self._baselines.attach(races)
