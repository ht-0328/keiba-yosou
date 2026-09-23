"""学習データを区分に分けて、区分ごとに別のモデルで学ぶときの分け方。"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

#: 分けないときの、区分の名前。
WHOLE = "全体"


@dataclass(frozen=True)
class ModelSegments:
    """学習データを区分に分けて、区分ごとに別のモデル（LightGBM と CatBoost）で学ぶときの分け方
    （既存モデルの修正計画の 1: 穴馬は中穴と大穴、人気馬は人気帯で分ける）。

    - ``column``: 区分の名前が入る列（学習データでは評価用の列、予測用データでは ID 列の横にある。例: 穴馬の区分）。
      None なら分けない（区分は「全体」1つ）。
    - ``folders``: 区分の名前 → モデルを置くフォルダの名前（例: 中穴 → mid）。モデルは ``<置き場所>/<フォルダ>/<時点>/``。
      分けないときは ``<置き場所>/<時点>/``（分ける前と同じ置き方）。
    """

    column: str | None = None
    folders: Mapping[str, str] = field(default_factory=dict)

    def labels(self) -> tuple[str, ...]:
        """区分の名前の並び。"""
        if self.column is None:
            return (WHOLE,)
        return tuple(self.folders)

    def rows(self, table: pd.DataFrame, label: str) -> pd.Series:
        """``table`` のうち、その区分の行（真偽の列）。分けないときは全部の行。"""
        if self.column is None:
            return pd.Series(True, index=table.index)
        return table[self.column].eq(label)

    def root_of(self, root: Path, label: str) -> Path:
        """その区分のモデルの置き場所。"""
        if self.column is None:
            return Path(root)
        return Path(root) / self.folders[label]
