"""過去の出走に、その年より前のレースだけで作った表 G から展開スコアを付ける。"""

from __future__ import annotations

from datetime import date

import pandas as pd

from . import names
from .advantage_table_builder import AdvantageTableBuilder
from .development_score import COLUMNS, DevelopmentScore


class YearlyScorer:
    """予測の表（1行 = 1頭。``race_id``・``horse_id`` と ①②③ の予測の列）に、レースの年ごとに「その年の1月1日より前のレースだけで
    作った表 G」で展開スコアを付ける（リークを防ぐ。学習データの材料にするときの決まり）。

    ``prepared`` は ``AdvantageRuns`` の表（表 G の材料と、レースの開催日・競馬場・芝ダ）。材料に無いレース（障害・まだ走っていない
    レースなど）の行は欠損値。例: 2024年のレースの馬は、2023年までのレースで作った表 G で数える。
    """

    def __init__(self) -> None:
        self._builder = AdvantageTableBuilder()
        self._score = DevelopmentScore()

    def of(self, forecasts: pd.DataFrame, prepared: pd.DataFrame) -> pd.DataFrame:
        """列は ``DevelopmentScore.COLUMNS`` と ``race_date``。行の並びと index は ``forecasts`` と同じ。"""
        courses = prepared.drop_duplicates("race_id")[["race_id", "race_date", names.VENUE_CODE, names.SURFACE]]
        dates = pd.Series(courses["race_date"].to_numpy(), index=courses["race_id"].astype(str))
        race_date = forecasts["race_id"].astype(str).map(dates)
        parts = []
        for year, rows in forecasts.groupby(race_date.dt.year, sort=True):
            table = self._builder.build(prepared, before=date(int(year), 1, 1))
            parts.append(self._score.of(rows, courses, table))
        scored = pd.concat(parts) if parts else pd.DataFrame(columns=list(COLUMNS))
        return scored.reindex(forecasts.index).assign(race_id=forecasts["race_id"], horse_id=forecasts["horse_id"], race_date=race_date)
