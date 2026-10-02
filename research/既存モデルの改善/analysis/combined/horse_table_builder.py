"""区切りごとの、組み合わせの1頭ごとの表を作る。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_ID, RACE_ID, TrainingData

from ..walk_forward import PART, PREDICTION_COLUMN, WINDOW
from ..windows import TestWindow
from .horse_columns import (
    BASE_TOP3,
    FAVORITE_PROBABILITY,
    FAVORITE_SHIFT,
    FORM_PROBABILITY,
    FORM_SHIFT,
    LONGSHOT_PROBABILITY,
    LONGSHOT_SHIFT,
)

#: 予測の表と学習データの表を突き合わせる鍵。
_KEYS = [RACE_ID, HORSE_ID]
#: ロジットにするときの端の丸め。
_EDGE = 1e-6
#: 予想の名前 → その確率を入れる列。
_PROBABILITY_COLUMNS: dict[str, str] = {
    "form_aptitude_top3": FORM_PROBABILITY,
    "longshots_in_top3": LONGSHOT_PROBABILITY,
    "favorites_out_of_top3": FAVORITE_PROBABILITY,
}


class HorseTableBuilder:
    """全頭の学習データの表（ID・評価用の列・目的変数・基準）に、3つの予想の予測を並べる。

    - ``form``: 全頭の予想の学習データの表（全期間）。表の行は出走した全頭なので、組み合わせの行の元にする。
    - ``predictions``: 予想の名前 → その予想の、区切りごとの予測の表（``walk_forward`` の出力）。

    1つの区切りの、検証期間とテスト期間の行を返す。3つの予想の上げ下げ（予想の確率のロジット − 基準のロジット、
    3着以内の向き）も足す。穴馬・人気馬の予想の対象でない馬の上げ下げは 0（基準のまま）。
    """

    def __init__(self, form: TrainingData, predictions: Mapping[str, pd.DataFrame]) -> None:
        base = form.baseline.probabilities().to_numpy() if form.baseline is not None else np.nan
        self._table = pd.concat([form.ids, form.evaluation, form.targets], axis=1).assign(**{BASE_TOP3: base})
        self._predictions = dict(predictions)

    def build(self, window: TestWindow) -> pd.DataFrame:
        rows = self._rows_of(window)
        merged = rows
        for name, column in _PROBABILITY_COLUMNS.items():
            merged = merged.merge(self._window_predictions(name, window, column), on=_KEYS, how="left")
        return self._with_shifts(merged.dropna(subset=[FORM_PROBABILITY]))

    def _rows_of(self, window: TestWindow) -> pd.DataFrame:
        days = self._table["開催日"]
        inside = (days >= pd.Timestamp(window.valid_first_day)) & (days <= pd.Timestamp(window.test_last_day))
        return self._table[inside]

    def _window_predictions(self, name: str, window: TestWindow, column: str) -> pd.DataFrame:
        """その予想の、その区切りの予測（鍵と確率と期間）。全頭の予想だけ、期間（検証・テスト）の列も持ってくる。"""
        frame = self._predictions[name]
        chosen = frame[frame[WINDOW] == window.name]
        keep = [*_KEYS, PREDICTION_COLUMN, PART] if column == FORM_PROBABILITY else [*_KEYS, PREDICTION_COLUMN]
        return chosen[keep].rename(columns={PREDICTION_COLUMN: column})

    def _with_shifts(self, table: pd.DataFrame) -> pd.DataFrame:
        base = _logit(table[BASE_TOP3])
        return table.assign(**{
            FORM_SHIFT: _logit(table[FORM_PROBABILITY]) - base,
            LONGSHOT_SHIFT: (_logit(table[LONGSHOT_PROBABILITY]) - base).fillna(0.0),
            FAVORITE_SHIFT: (_logit(1.0 - table[FAVORITE_PROBABILITY]) - base).fillna(0.0),
        })


def _logit(probability: pd.Series) -> pd.Series:
    clipped = probability.clip(_EDGE, 1.0 - _EDGE)
    return np.log(clipped / (1.0 - clipped))
