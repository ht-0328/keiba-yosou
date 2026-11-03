"""1つの区切りで、複勝オッズから見た3着以内率を出発点にして、穴馬の予想を学ぶ。"""

from __future__ import annotations

from dataclasses import replace

import numpy as np
import pandas as pd

from yosou.shared.dataset import BaselineLogit, TrainingData

from 既存モデルの改善.analysis.variants import ModelVariant
from 既存モデルの改善.analysis.walk_forward import WindowTrainer
from 既存モデルの改善.analysis.windows import TestWindow

#: 出発点にする列（穴馬の予想の材料 M の1つ）と、予測の表に残す列の名前。
PLACE_MARKET_RATE = "複勝オッズから見た3着以内率"
PLACE_MARKET_COLUMN = "複勝オッズの確率"
#: 確率をロジットに直すときに、0 と 1 に張り付かないように抑える幅。
_CLIP = 1e-4


class PlaceMarketWindowTrainer(WindowTrainer):
    """穴馬の予想を、複勝オッズから見た3着以内率を出発点にして学ぶ。

    複勝を買うときに勝てるかどうかは、複勝の市場（複勝オッズ）より来る馬を選べるかで決まる。単勝オッズから計算した3着以内率
    （Harville の式）を出発点にすると、モデルは単勝の市場との差を学び、複勝の市場との差は見えない。
    ここでは出発点を複勝オッズから見た3着以内率にし、モデルが「複勝オッズより来る・来ない」だけを学ぶようにする。
    複勝オッズの無い馬（複勝を売らないレースなど）は、元の出発点（単勝オッズから計算した値）のまま。
    予測の表には、複勝オッズから見た3着以内率（``PLACE_MARKET_COLUMN``）を残す。買うかどうかは「予想 − この値」で決める。
    """

    def run(self, data: TrainingData, window: TestWindow,
            variant: ModelVariant) -> tuple[pd.DataFrame, list[dict[str, object]]]:
        if PLACE_MARKET_RATE not in variant.columns:
            raise ValueError(f"{variant.name}: 列に {PLACE_MARKET_RATE} がありません")
        return super().run(self._place_based(data), window, variant)

    def _predict(self, members, data: TrainingData, window: TestWindow, part: str, segment: str) -> pd.DataFrame:
        frame = super()._predict(members, data, window, part, segment)
        return frame.assign(**{PLACE_MARKET_COLUMN: data.features[PLACE_MARKET_RATE].to_numpy()})

    @staticmethod
    def _place_based(data: TrainingData) -> TrainingData:
        """出発点を、複勝オッズから見た3着以内率（のロジット）に置き換えたデータ（無い馬は元のまま）。"""
        if data.baseline is None:
            raise ValueError("オッズの分かる時点（前日・当日）のデータを渡してください")
        rate = data.features[PLACE_MARKET_RATE].to_numpy(dtype=float)
        clipped = np.clip(rate, _CLIP, 1 - _CLIP)
        values = data.baseline.values.copy()
        known = ~np.isnan(rate)
        values[known] = np.log(clipped[known] / (1 - clipped[known]))
        return replace(data, baseline=BaselineLogit(values, data.baseline.known_from))
