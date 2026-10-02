"""馬の力の材料（まとまり M）を作る元の記録の入れ物。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class AbilitySources:
    """馬の力の材料を作る元の記録。どれもリポジトリが元DB から読んだもの。

    - ``runs``: 過去の全出走と対象の出走（1行 = 1頭の出走。``AbilityRunRepository``）。対象の出走は ``is_target`` が真。
    - ``figures``: 過去の全部の走のスピード指数（``SpeedFigureRepository``）。まだ走っていないレースの行は無い。
    - ``workouts``: 対象の出走ごとの、レースの前の調教のまとめ（``WorkoutSummaryRepository``）。
    - ``sales``: セリの取引（1行 = 1回の取引。``SalePriceRepository``）。
    """

    runs: pd.DataFrame
    figures: pd.DataFrame
    workouts: pd.DataFrame
    sales: pd.DataFrame
