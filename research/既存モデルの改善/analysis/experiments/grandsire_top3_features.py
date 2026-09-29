"""父の父の産駒の、近1年の3着以内の割合（共通の特徴量に足すかを決める実験）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature.history import PedigreeTop3Rate

#: 特徴量の名前（予想のパッケージの「父の産駒の近1年の3着以内の割合」と同じ言い方）。
GRANDSIRE_TOP3_RATE = "父の父の産駒の近1年の3着以内の割合"
NAMES: tuple[str, ...] = (GRANDSIRE_TOP3_RATE,)


class GrandsireTop3Features:
    """父の父の産駒の、開催日の前日までの 365日の3着以内の割合（芝ダを問わない）。

    父・母の父の割合（予想のパッケージのまとまり H）と同じ部品（``PedigreeTop3Rate``）と同じ読み方
    （``PedigreeDayRepository`` を ``grandsire`` の列で）で作る。採用なら、この作り方のまま H に移す。
    """

    def build(self, history: pd.DataFrame, grandsire_days: pd.DataFrame) -> pd.DataFrame:
        """``history`` は全出走（``race_id``・``horse_id``・``race_date``・``grandsire``）、``grandsire_days`` は
        父の父ごと・開催日ごと・芝ダごとの出走数と3着以内の数。列は race_id・horse_id と ``NAMES``。"""
        rate = PedigreeTop3Rate(history, "grandsire").of_all_surfaces(grandsire_days)
        return history[["race_id", "horse_id"]].assign(**{GRANDSIRE_TOP3_RATE: rate.to_numpy()})
