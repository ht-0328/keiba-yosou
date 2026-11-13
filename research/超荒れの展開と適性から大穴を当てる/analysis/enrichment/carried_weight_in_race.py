"""斤量を、同じレースの出走馬と比べた列を足す（ハンデの見方）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class CarriedWeightInRace:
    """出走の表（``race_id``・``carried``・``body_weight`` が要る）に、レースの中での斤量の位置を足す。どれもレースの前に分かる。

    足す列:
    - ``carried_vs_mean``: 斤量 − レースの平均の斤量（kg）
    - ``carried_vs_top``: 斤量 − レースでいちばん重い斤量（トップハンデとの差。0 ならトップ。kg）
    - ``carried_ratio_vs_mean``: 斤量 ÷ 馬体重 から、レースの平均を引いたもの（体の大きさに対する重さ。馬体重が無ければ欠損値）
    - ``carried_spread``: レースの斤量の幅（いちばん重い − いちばん軽い。kg）
    """

    def add(self, runners: pd.DataFrame) -> pd.DataFrame:
        frame = runners.copy()
        race = frame.groupby("race_id", sort=False)["carried"]
        frame["carried_vs_mean"] = frame["carried"] - race.transform("mean")
        frame["carried_vs_top"] = frame["carried"] - race.transform("max")
        frame["carried_spread"] = race.transform("max") - race.transform("min")
        ratio = frame["carried"] / frame["body_weight"].where(frame["body_weight"] > 0)
        frame["carried_ratio_vs_mean"] = ratio - ratio.groupby(frame["race_id"], sort=False).transform("mean")
        return frame
