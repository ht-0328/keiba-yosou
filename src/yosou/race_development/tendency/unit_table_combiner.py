"""単位（区分・券種）ごとの予測の表を、1つの既存の予想の表にまとめる。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd


class UnitTableCombiner:
    """単位ごとの予測の表（ID 列と予測の列）を、1行 = 1頭（1レース）の表にまとめる。

    区分で分ける予想（人気帯・穴馬の区分）は、単位ごとに行が違い、列が同じ。券種で分ける予想（荒れ具合）は、
    単位ごとに行が同じで、列が違う。どちらも、縦につないでから ID ごとに欠損値でない値を取れば、1行にまとまる。
    """

    def combine(self, parts: Sequence[pd.DataFrame | None], keys: list[str]) -> pd.DataFrame:
        present = [part.astype({key: "str" for key in keys}) for part in parts if part is not None]
        if not present:
            return pd.DataFrame(columns=keys)
        return pd.concat(present, ignore_index=True).groupby(keys, as_index=False, sort=False).first()
