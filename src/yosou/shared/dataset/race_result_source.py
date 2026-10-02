"""レースごとの結果を読むクラスに共通の決まり。"""

from __future__ import annotations

from datetime import date
from typing import Protocol

import pandas as pd


class RaceResultSource(Protocol):
    """レースごとの結果の表の読み方（展開の設計書 04 の 2）。``RaceDatasetBuilder`` は、何の結果かを知らずに済む。

    荒れ具合の予想は払戻（``RacePayoutRepository``）、展開の予想は前半・後半タイムとその基準（``PaceRecordSource``）を渡す。
    """

    def read(self, first_day: date) -> pd.DataFrame:
        """開催日が ``first_day`` 以降のレースの結果（1行 = 1レース、列 ``race_id`` を持つ）。
        目的変数の元と、過去の結果から作る特徴量の材料になる。
        """
        ...
