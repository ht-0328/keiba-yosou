"""レースの中身を、決めた期間の5分位で帯に分ける。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .race_traits import TRAITS

#: 帯の数（has_danger は いない・いる の2つ）。
BIN_COUNT = 5


class TraitBins:
    """``RaceTraits`` の表のうち ``reference``（区切りを決める期間のレース。docs/03 では 2016〜2018年）の5分位で、各レースを帯（0 から）に分ける。

    頭数のように同じ値が多い中身は、重なる区切りを1つにまとめるので、帯が5つより少なくなる。has_danger は 0・1 をそのまま帯にする。
    列 ``bin_<中身>`` に帯の番号の文字列（``RuleDayTable`` の種類として使う）を入れて返す。例: 1番人気のオッズの区切りが 1.9・2.3・2.8・3.3 なら、2.5倍は帯 "2"。
    """

    def __init__(self, reference: pd.DataFrame) -> None:
        self._edges = {trait: self._cut_points(reference[trait]) for trait in TRAITS if trait != "has_danger"}

    def labels(self, trait: str) -> list[str]:
        """その中身の帯の名前の並び（低い順）。"""
        count = 2 if trait == "has_danger" else len(self._edges[trait]) + 1
        return [str(at) for at in range(count)]

    def edges(self, trait: str) -> np.ndarray:
        return self._edges[trait]

    def of(self, traits: pd.DataFrame) -> pd.DataFrame:
        table = traits[["race_id"]].copy()
        for trait in TRAITS:
            if trait == "has_danger":
                table[f"bin_{trait}"] = traits[trait].astype(int).astype(str).to_numpy()
                continue
            table[f"bin_{trait}"] = np.searchsorted(self._edges[trait], traits[trait].to_numpy(), side="right").astype(str)
        return table

    @staticmethod
    def _cut_points(values: pd.Series) -> np.ndarray:
        """5分位の内側の区切り（重なりは1つにまとめる）。区切りちょうどの値は上の帯に入る。"""
        return np.unique(np.quantile(values.dropna().to_numpy(), np.linspace(0, 1, BIN_COUNT + 1)[1:-1]))
