"""予想「展開から着順を予想」の年ごとの確かめの予測を、まとまり P の元の予測の表にして読む。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from yosou.race_development.feature import (
    BACK_PROBABILITY,
    CLOSING_PREDICTION,
    CORNER4_PREDICTION,
    FIRST_HALF_QUANTILES,
    FRONT_PROBABILITY,
    HIGH_PROBABILITY,
    LEADER_PROBABILITY,
    MIDDLE_PROBABILITY,
    SECOND_HALF_QUANTILES,
    SLOW_PROBABILITY,
    GroupForecast,
)
from yosou.race_development.repository import OutOfSampleRepository
from yosou.shared.dataset import HORSE_ID, RACE_ID
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.pace_forecast import pace_forecast_columns as names

#: 前半・後半の組の名前（``ForecastGroup`` の値。年ごとの確かめの予測の置き場所のフォルダ名）。
EARLY, LATE = "early", "late"
#: 展開の予測の列 → まとまり P の元の予測の列（1頭ごと）。
_EARLY_HORSE = {LEADER_PROBABILITY: names.LEADER, FRONT_PROBABILITY: names.FRONT,
                MIDDLE_PROBABILITY: names.MIDDLE, BACK_PROBABILITY: names.BACK}
_LATE_HORSE = {CORNER4_PREDICTION: names.CORNER4, CLOSING_PREDICTION: names.CLOSING}
#: 展開の予測の列 → まとまり P の元の予測の列（1レースごと。同じレースの馬に配る）。
_EARLY_RACE = {SLOW_PROBABILITY: names.SLOW, HIGH_PROBABILITY: names.HIGH, FIRST_HALF_QUANTILES[0]: names.FIRST_LOW,
               FIRST_HALF_QUANTILES[1]: names.FIRST_MIDDLE, FIRST_HALF_QUANTILES[2]: names.FIRST_HIGH}
_LATE_RACE = {SECOND_HALF_QUANTILES[1]: names.SECOND_MIDDLE}


class OutOfSampleReader:
    """``<root>/out_of_sample/`` の前半・後半の組の、その時点の年ごとの予測を全部つなぎ、1行 = 1頭の表にする。

    どの年の予測も、その年より前だけで学習した展開のモデルのもの（展開の設計書 11 の決まり 11）なので、そのまま学習データの
    材料にできる。列は ``race_id``・``horse_id`` と ``SOURCE_COLUMNS``。後半の予測が無い年（前半より1年遅く始まる）の馬は、
    後半の列が欠損値。作った条件（設定など）は問わない（``OutOfSampleRepository.stored``）。
    """

    def __init__(self, root: Path) -> None:
        self._repository = OutOfSampleRepository(Path(root) / "out_of_sample")

    def read(self, timing: PredictionTiming) -> pd.DataFrame:
        early, late = self._group(EARLY, timing), self._group(LATE, timing)
        ids = early.horses[[RACE_ID, HORSE_ID]].astype(str).drop_duplicates().reset_index(drop=True)
        parts = [early.horse_rows(ids).rename(columns=_EARLY_HORSE), early.race_rows(ids).rename(columns=_EARLY_RACE),
                 late.horse_rows(ids).rename(columns=_LATE_HORSE), late.race_rows(ids).rename(columns=_LATE_RACE)]
        table = pd.concat([ids.rename(columns={RACE_ID: "race_id", HORSE_ID: "horse_id"}), *parts], axis=1)
        return table[[*names.KEY, *names.SOURCE_COLUMNS]]

    def years(self, timing: PredictionTiming) -> dict[str, list[int]]:
        """組 → 予測が残っている年。"""
        return {group: self._repository.years(group, timing) for group in (EARLY, LATE)}

    def _group(self, group: str, timing: PredictionTiming) -> GroupForecast:
        parts = [self._repository.stored(group, timing, year) for year in self._repository.years(group, timing)]
        if not parts:
            raise FileNotFoundError(f"{group} の組の {timing.label}の予測がありません（展開の予想の backtest --timing で作る）")
        return GroupForecast.concat(parts)
