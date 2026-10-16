"""レースの範囲（学習に使う範囲と、予想して確かめる範囲）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.shared.dataset import TrainingData

from .sign_training_table import GRADE

#: 平地の重賞のグレードコード（G1 = A・G2 = B・G3 = C）。
_STAKES_GRADES = ("A", "B", "C")


@dataclass(frozen=True)
class RaceScope:
    """レースの範囲。

    - ``key``: ファイル名に使う名前（例 ``g1``）。
    - ``label``: 表に出す名前（例 G1だけ）。
    - ``grades``: 範囲に入るグレードコード。None なら全レース。
    """

    key: str
    label: str
    grades: tuple[str, ...] | None

    def matches(self, grade: pd.Series) -> pd.Series:
        """グレードコードの列から、範囲に入るか（真偽の列）。重賞でないレースのグレードコードは空。"""
        if self.grades is None:
            return pd.Series(True, index=grade.index)
        return grade.fillna("").isin(self.grades)

    def rows(self, data: TrainingData) -> pd.Series:
        """学習データのうち、範囲に入る行（真偽の列）。"""
        return self.matches(data.evaluation[GRADE])

    def apply(self, data: TrainingData) -> TrainingData:
        return data.where(self.rows(data))


G1_ONLY = RaceScope("g1", "G1だけ", ("A",))
STAKES = RaceScope("stakes", "重賞（G1〜G3）", _STAKES_GRADES)
ALL_RACES = RaceScope("all", "全レース", None)
#: 学習に使う3つの範囲（利用者の指定の順）。
SCOPES: tuple[RaceScope, ...] = (G1_ONLY, STAKES, ALL_RACES)

G1_RACES = RaceScope("g1", "G1", ("A",))
LOWER_STAKES = RaceScope("g2g3", "G2・G3", ("B", "C"))
#: 予想して確かめる2つの範囲（G1 のために作った予想を、G1 と G1以外の重賞に当てる）。
#: 重賞以外のレースは、利用者の指示で確かめない。
EVALUATION_SCOPES: tuple[RaceScope, ...] = (G1_RACES, LOWER_STAKES)
