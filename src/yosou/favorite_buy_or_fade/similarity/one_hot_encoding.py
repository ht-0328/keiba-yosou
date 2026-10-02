"""カテゴリの列を、値ごとの 0 と 1 の列にする。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 0 と 1 の列に掛ける値。値が違う2頭の距離への寄与（2つの列が 1 ずつ違う）を、標準化した数の列の
#: 標準偏差1つ分にそろえる。0 と 1 の列を標準化すると、めったに無い値ほど強く効いてしまうので、標準化はしない。
FLAG_SCALE = 1 / np.sqrt(2)


class OneHotEncoding:
    """カテゴリの列を、学習データにある値ごとの 0 と 1 の列にする（one-hot。設計書 12 の 1。方針の ``categorical = "one-hot"``）。

    学習データに無い値と欠損値は、どの列も 0。0 と 1 の列は標準化せず、1/√2（``FLAG_SCALE``）を掛ける（設計書 12 の 3）。
    """

    def __init__(self) -> None:
        self._categories: dict[str, list[str]] = {}

    def fit(self, values: pd.DataFrame, is_out: pd.Series | None = None) -> OneHotEncoding:
        """``values`` はカテゴリの列だけの表。``is_out`` は使わない（馬券外率に直す ``OutRateEncoding`` と同じ呼び方にするため）。"""
        self._categories = {column: sorted(str(value) for value in values[column].dropna().unique())
                            for column in values.columns}
        return self

    @property
    def column_names(self) -> list[str]:
        """「馬場状態=良」の形。"""
        return [f"{column}={value}" for column, values in self._categories.items() for value in values]

    @property
    def sources(self) -> list[str]:
        """列ごとの、元の特徴量の名前（``column_names`` と同じ並び）。"""
        return [column for column, values in self._categories.items() for _ in values]

    def transform(self, values: pd.DataFrame) -> pd.DataFrame:
        parts = [self._one_hot(values[column], categories) for column, categories in self._categories.items()]
        if not parts:
            return pd.DataFrame(index=values.index)
        return pd.concat(parts, axis=1)

    def _one_hot(self, values: pd.Series, categories: list[str]) -> pd.DataFrame:
        texts = values.astype(object).where(values.notna()).map(str, na_action="ignore")
        return pd.DataFrame({f"{values.name}={value}": (texts == value).astype(float) * FLAG_SCALE
                             for value in categories}, index=values.index)
