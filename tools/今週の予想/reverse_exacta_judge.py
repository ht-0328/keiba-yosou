"""当日の予想の1レースで、裏が当たる確率を出し、馬単の裏（○▲☆→◎）まで買うかを決める。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 今週の予想.reverse_exacta_features import ReverseExactaFeatures
from 今週の予想.reverse_exacta_model import ReverseExactaModel

#: 学習済みモデルの置き場所の中のフォルダ名（全頭の予想のモデルの置き場所の下）。
FOLDER = "馬単の裏"
#: 馬単の裏まで買う、裏が当たる確率の線。研究「裏目を買うかの予想」で、決める期間（2025年9月〜2026年2月）でいちばん良く、
#: 確かめる期間（2026年3月〜）と、学びに使わなかった1年（2024年9月〜2025年8月）でも、今のまま（表だけ）より回収率と1日の儲けが上がった線。
LINE = 0.30


class ReverseExactaJudge:
    """印を付けた1レースの表から、裏（1着が ○▲☆ のどれかで、◎ が2着か3着）が当たる確率を ``ReverseExactaModel`` で出し、
    ``LINE`` 以上なら馬単の裏まで買う。モデルの無いとき・材料を作れないレース（◎ が1頭でない・相手がいない）は確率なし（買わない）。"""

    def __init__(self, model: ReverseExactaModel | None) -> None:
        self._model = model
        self._features = ReverseExactaFeatures()

    @classmethod
    def load(cls, models: Path) -> ReverseExactaJudge:
        """全頭の予想のモデルの置き場所 ``models`` の下の ``FOLDER`` から読む（無ければ、どのレースも確率なし）。"""
        return cls(ReverseExactaModel.load(Path(models) / FOLDER))

    def probability(self, race: pd.DataFrame) -> float | None:
        """裏が当たる確率。出せなければ None。"""
        if self._model is None:
            return None
        row = self._features.of(race)
        if row is None:
            return None
        return float(self._model.predict(self._features.frame([row]))[0])

    @staticmethod
    def buys(probability: float | None) -> bool:
        """馬単の裏まで買うか。"""
        return probability is not None and probability >= LINE
