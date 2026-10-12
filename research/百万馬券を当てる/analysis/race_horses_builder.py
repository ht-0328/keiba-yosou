"""保存した予測（1着と3着以内）から、レースごとの出走馬の予想を作る。"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_NO, RACE_ID
from yosou.upset_premise.betting import RaceHorses

from 既存モデルの改善.analysis.walk_forward.prediction_frame import PART, PART_TEST, PREDICTION_COLUMN

#: 予測を突き合わせたあとの列の名前。
_WIN, _TOP3, _USUAL_TOP3 = "1着の確率", "3着以内の確率", "今の予想の3着以内の確率"


class RaceHorsesBuilder:
    """1着の予測と3着以内の予測（どちらも区切りごとに学んだ予測の表）のテスト期間の行を、馬番で突き合わせてレースごとにまとめる。

    1着の確率は、レースの中で合計 1 になるように直す（Harville の式の前提）。片方の予測しか無い馬は使わない。
    ``usual_top3`` は今の予想の3着以内の予測（一律の買い方の2着・3着の重みに使う）。渡すと、それも馬番で突き合わせる。
    """

    def __init__(self, win: pd.DataFrame, top3: pd.DataFrame, usual_top3: pd.DataFrame | None = None) -> None:
        merged = _test(win).rename(columns={PREDICTION_COLUMN: _WIN}).merge(
            _test(top3).rename(columns={PREDICTION_COLUMN: _TOP3}), on=[RACE_ID, HORSE_NO], how="inner")
        if usual_top3 is not None:
            merged = merged.merge(_test(usual_top3).rename(columns={PREDICTION_COLUMN: _USUAL_TOP3}), on=[RACE_ID, HORSE_NO], how="inner")
        merged[_WIN] = merged[_WIN] / merged.groupby(RACE_ID)[_WIN].transform("sum")
        self._with_usual = usual_top3 is not None
        self._by_race = {race_id: rows for race_id, rows in merged.groupby(RACE_ID)}

    def build(self, race_ids: Iterable[str]) -> dict[str, RaceHorses]:
        return {race_id: self._race(race_id) for race_id in race_ids if race_id in self._by_race}

    def _race(self, race_id: str) -> RaceHorses:
        rows = self._by_race[race_id]
        usual = rows[_USUAL_TOP3].to_numpy(dtype=float) if self._with_usual else None
        return RaceHorses(race_id, rows[HORSE_NO].to_numpy(dtype=int), rows[_WIN].to_numpy(dtype=float),
                          rows[_TOP3].to_numpy(dtype=float), usual)


def _test(predictions: pd.DataFrame) -> pd.DataFrame:
    """テスト期間の行の、レースID・馬番・確率。馬番は整数にそろえる。"""
    test = predictions[predictions[PART].eq(PART_TEST)][[RACE_ID, HORSE_NO, PREDICTION_COLUMN]]
    return test.assign(**{HORSE_NO: pd.to_numeric(test[HORSE_NO], errors="coerce")}).dropna().astype({HORSE_NO: np.int64})
