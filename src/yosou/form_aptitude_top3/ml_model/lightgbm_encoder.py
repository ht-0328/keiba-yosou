"""特徴量を、LightGBM が受け取れる形に変える。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Self

import pandas as pd

#: 出走の少ない値を「その他」にまとめるカテゴリ特徴量（設計書 12 の 1）。値の種類が多く、過学習しやすいもの。
RARE_GROUPED_COLUMNS: tuple[str, ...] = ("騎手", "調教師", "父", "父の父", "母の父")
#: 出走の少ない値と、学習のあとに出てきた値をまとめる値。
OTHER = "その他"


class LightGbmEncoder:
    """カテゴリ特徴量を pandas の category 型にする（設計書 12 の 3）。LightGBM は文字列を扱えないため。

    カテゴリの一覧は学習データから作り（``fit``）、学習データ・検証データ・予測用データのどれにも
    同じ一覧を使う（``transform``）。一覧が違うと、同じ騎手でも別の値として扱われる。
    """

    def __init__(self, min_category_count: int) -> None:
        self._min_category_count = min_category_count
        self._columns: tuple[str, ...] = ()
        self._categories: dict[str, list[str]] = {}

    def fit(self, features: pd.DataFrame, categorical_columns: Sequence[str]) -> Self:
        """学習データから、特徴量の列の並びと、カテゴリ特徴量ごとの値の一覧を覚える。"""
        self._columns = tuple(features.columns)
        self._categories = {
            column: self._category_values(features[column]) for column in categorical_columns
        }
        return self

    def transform(self, features: pd.DataFrame) -> pd.DataFrame:
        """列を学習と同じ並びにし、カテゴリ特徴量を category 型にする。数値特徴量はそのまま。"""
        encoded = features[list(self._columns)].copy()
        for column in self._categories:
            encoded[column] = self._encoded_column(encoded[column])
        return encoded

    def _category_values(self, values: pd.Series) -> list[str]:
        """学習データに出てきた値の一覧。「その他」にまとめる列は、出走の多い値だけにして「その他」を足す。"""
        counts = values.value_counts(dropna=True)
        if values.name not in RARE_GROUPED_COLUMNS:
            return sorted(counts.index)
        frequent = counts[counts >= self._min_category_count]
        return [*sorted(frequent.index), OTHER]

    def _encoded_column(self, values: pd.Series) -> pd.Categorical:
        """一覧にある値はそのまま、欠損値は欠損値のまま。一覧に無い値は「その他」（まとめない列は欠損値）。"""
        categories = self._categories[values.name]
        known = values.where(values.isin(categories))
        if values.name not in RARE_GROUPED_COLUMNS:
            return pd.Categorical(known, categories=categories)
        grouped = known.fillna(OTHER).where(values.notna())
        return pd.Categorical(grouped, categories=categories)
