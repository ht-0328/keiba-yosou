"""YAML の odds_baseline: オッズから見た確率を、モデルの出発点（基準のロジット）にする。"""

import numpy as np
import pandas as pd

from yosou.shared.dataset import BaselineLogit, Top3Baseline
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.odds import WIN_RATE, MarketPlaces

#: 確率をロジットにするときの端の丸め（0 と 1 はロジットにできない）。
EDGE = 1e-4


class OddsBaseline:
    """目的ごとの基準。勝利はオッズから見た勝率、馬券内は3着以内率、馬券外は（1 − 3着以内率）のロジット。

    モデルはこの値から「同じオッズの馬より来やすいか・来にくいか」の上げ下げだけを学ぶ。基準なしのモデルは
    大穴にも数%の確率を付けやすく、確率×オッズの期待値で買うと大穴ばかり買ってしまう。
    オッズが分かるのは前日から。オッズの無い馬は、頭数から見た割合（1 ÷ 頭数、3 ÷ 頭数）にする。
    同じレースの全頭がそろった行で作る（人気範囲・条件で絞る前）。
    """

    known_from = PredictionTiming.DAY_BEFORE

    def __init__(self, target: str) -> None:
        self._target = target

    def build(self, entries: pd.DataFrame) -> BaselineLogit:
        if self._target == "勝利":
            values = self._win_logit(entries)
        else:
            top3 = Top3Baseline().build(entries)
            values = -top3 if self._target == "馬券外" else top3
        return BaselineLogit(values, self.known_from)

    def _win_logit(self, entries: pd.DataFrame) -> pd.Series:
        win = MarketPlaces().of(entries)[WIN_RATE]
        field_size = entries.groupby("race_id")["race_id"].transform("size")
        clipped = win.fillna(1.0 / field_size).clip(EDGE, 1.0 - EDGE)
        return np.log(clipped / (1.0 - clipped))
