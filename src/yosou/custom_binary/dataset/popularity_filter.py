"""人気範囲に入る馬を選ぶ。"""

import pandas as pd

from yosou.shared.feature.value_types import as_numbers

from ..setting import PopularityRange


class PopularityFilter:
    """人気範囲（両端を含む）に入る行を真にする。範囲が無ければ全頭。範囲があるのに人気が不明・不正なら止める。"""

    def mask(self, rows: pd.DataFrame, bounds: PopularityRange) -> pd.Series:
        if not bounds.bounded:
            return pd.Series(True, index=rows.index)
        popularity = as_numbers(rows["popularity"])
        invalid = popularity.isna() | (popularity < 1) | (popularity % 1 != 0)
        if invalid.any():
            raise ValueError(f"人気範囲の判定に必要な人気が不明・不正です（{int(invalid.sum())}頭）。予想時は--popsで指定してください")
        kept = pd.Series(True, index=rows.index)
        if bounds.minimum is not None:
            kept &= popularity >= bounds.minimum
        if bounds.maximum is not None:
            kept &= popularity <= bounds.maximum
        return kept
