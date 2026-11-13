"""出走の表に、この研究で使う列を足す流れ（過去走 → 斤量 → 位置 → 近走 → 期間で絞る → レースの中の斤量 → 展開 → 締め切り前の人気 → 期待の率）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import numpy as np
import pandas as pd

from .carried_weight_history import CarriedWeightHistory
from .carried_weight_in_race import CarriedWeightInRace
from .expected_rates import ExpectedRates
from .pace_attachment import PaceAttachment
from .recent_form import RecentForm
from .running_position import RunningPosition

#: 大穴とみなす確定の単勝人気（これ以下の人気。10番人気以下）。
LONGSHOT_POPULARITY = 10
#: 前半と後半の年の境（前半はこの年まで）。
PERIOD_SPLIT_YEAR = 2020


@dataclass(frozen=True)
class SideTables:
    """出走の表に結ぶ、ほかの置き場所の表（回顧の表2、展開の予想のレースと馬、締め切り前の人気）。"""

    reviews: pd.DataFrame
    race_forecasts: pd.DataFrame
    horse_forecasts: pd.DataFrame
    pre_close: pd.DataFrame


@dataclass(frozen=True)
class RunnerEnrichment:
    """``history``（``RunnerFactsRepository`` の行。過去走をたどるため、事例の期間より前から読む）から、
    ``date_from`` 以降の出走の表を作る。足す列は各部品の説明のとおり。ほかに次の列を足す。

    - ``longshot``: 確定の単勝人気が 10番人気以下 / ``top3``・``won``: 3着以内・1着（着順の無い馬は外れ）
    - ``handicap``: 「ハンデ戦」か「ハンデ戦以外」 / ``period``: 「（最初の年）〜2020年」か「2021年〜」
    - ``pre_close_longshot``: 締め切り前の人気が 10番人気以下（締め切り前の断面のある 2025年からだけ）
    """

    date_from: date

    def build(self, history: pd.DataFrame, side: SideTables) -> pd.DataFrame:
        frame = CarriedWeightHistory().add(history)
        frame = RunningPosition().add(frame)
        frame = RecentForm().add(frame)
        frame = frame.loc[frame["race_date"] >= self.date_from.isoformat()]
        frame = CarriedWeightInRace().add(frame.loc[frame["popularity"].notna()])
        frame = PaceAttachment().add(frame, side.reviews, side.race_forecasts, side.horse_forecasts)
        frame = frame.merge(side.pre_close, on=["race_id", "horse_no"], how="left")
        frame["longshot"] = frame["popularity"] >= LONGSHOT_POPULARITY
        frame["pre_close_longshot"] = (frame["pre_close_popularity"] >= LONGSHOT_POPULARITY).where(frame["pre_close_popularity"].notna())
        frame["top3"] = (frame["finish"] <= 3).astype(float)
        frame["won"] = (frame["finish"] == 1).astype(float)
        frame["handicap"] = np.where(frame["weight_type"] == "ハンデ", "ハンデ戦", "ハンデ戦以外")
        frame["period"] = np.where(frame["year"] <= PERIOD_SPLIT_YEAR, f"{self.date_from.year}〜{PERIOD_SPLIT_YEAR}年", f"{PERIOD_SPLIT_YEAR + 1}年〜")
        frame = ExpectedRates().add(frame)
        return frame.sort_values(["race_id", "horse_no"], kind="stable").reset_index(drop=True)
