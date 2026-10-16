"""学習に使うレースの範囲（G1だけ・重賞・全レース）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.shared.dataset import TrainingData

from .sign_training_table import GRADE


@dataclass(frozen=True)
class RaceScope:
    """学習（と、木を足すのを止める判断に使う検証）に使うレースの範囲。

    - ``key``: 予測のファイル名の頭（例 ``g1``）。
    - ``label``: 表に出す名前（例 G1だけ）。
    - ``grades``: 入れるレースのグレードコード（平地の G1 = A・G2 = B・G3 = C）。None なら全レース。
    """

    key: str
    label: str
    grades: tuple[str, ...] | None

    def rows(self, data: TrainingData) -> pd.Series:
        """範囲に入る行（真偽の列）。"""
        if self.grades is None:
            return pd.Series(True, index=data.ids.index)
        return data.evaluation[GRADE].isin(self.grades)

    def apply(self, data: TrainingData) -> TrainingData:
        return data.where(self.rows(data))


G1_ONLY = RaceScope("g1", "G1だけ", ("A",))
STAKES = RaceScope("stakes", "重賞（G1〜G3）", ("A", "B", "C"))
ALL_RACES = RaceScope("all", "全レース", None)
#: 比べる3つの範囲（利用者の指定の順）。
SCOPES: tuple[RaceScope, ...] = (G1_ONLY, STAKES, ALL_RACES)
