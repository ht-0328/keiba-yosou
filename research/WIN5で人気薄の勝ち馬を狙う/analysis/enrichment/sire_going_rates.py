"""父の産駒の、今回の芝ダと馬場（良か道悪か）での勝率（前の年まで）を足す。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: 勝率を信じるのに要る産駒の出走数。これより少なければ欠損値にする。
MIN_RUNS = 100


@dataclass(frozen=True)
class SireGoingRates:
    """出走の表に ``sire_going_rate``（父の産駒の、同じ芝ダ・同じ馬場での前の年までの勝率）と
    ``sire_surface_rate``（同じ芝ダ全体での前の年までの勝率）を足す。``going`` の列（``RunnerHistory`` が足す）が要る。"""

    def add(self, runners: pd.DataFrame) -> pd.DataFrame:
        going = self._cumulative(runners, ["sire", "surface", "going"]).rename(columns={"rate": "sire_going_rate"})
        surface = self._cumulative(runners, ["sire", "surface"]).rename(columns={"rate": "sire_surface_rate"})
        frame = runners.merge(going, on=["sire", "surface", "going", "year"], how="left")
        return frame.merge(surface, on=["sire", "surface", "year"], how="left")

    @staticmethod
    def _cumulative(runners: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
        """keys ごと・年ごとに、その年より前の年の合計の勝率（出走が ``MIN_RUNS`` 未満なら欠損値）。"""
        frame = runners.assign(win=(runners["finish"] == 1).astype(float), run=1.0)
        yearly = frame.groupby([*keys, "year"])[["win", "run"]].sum().reset_index().sort_values("year")
        totals = yearly.groupby(keys)[["win", "run"]].cumsum() - yearly[["win", "run"]].to_numpy()
        rate = (totals["win"] / totals["run"]).where(totals["run"] >= MIN_RUNS)
        return yearly[[*keys, "year"]].assign(rate=rate)
