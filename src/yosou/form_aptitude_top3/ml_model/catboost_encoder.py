"""特徴量を、CatBoost が受け取れる形に変える。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

#: カテゴリ特徴量の欠損値の代わりの文字列。CatBoost は、カテゴリ特徴量に NaN があると学習できない。
#: 特徴量の値として意味を持つ「なし」（例: 直近の調教のコースの「調教なし」）と区別するため、「不明」にする。
MISSING = "不明"


class CatBoostEncoder:
    """カテゴリ特徴量を文字列にし、欠損値だけ文字列「不明」にする（設計書 13 の 3）。

    LightGBM と違い、学習データから覚えることが無いので、``fit`` は無い。
    出走の少ない値や、学習のときに無かった値も、そのまま渡す（CatBoost が全体の割合に寄せて扱う）。
    """

    def __init__(self, columns: Sequence[str], categorical_columns: Sequence[str]) -> None:
        """``columns`` は学習のときの特徴量の列の並び、``categorical_columns`` はそのうちのカテゴリ特徴量。"""
        self._columns = tuple(columns)
        self._categorical_columns = tuple(categorical_columns)

    @property
    def categorical_columns(self) -> tuple[str, ...]:
        """ライブラリの ``fit`` の ``cat_features`` に渡す列名。"""
        return self._categorical_columns

    def transform(self, features: pd.DataFrame) -> pd.DataFrame:
        """列を学習と同じ並びにし、カテゴリ特徴量を文字列にする。数値特徴量はそのまま（欠損値も NaN のまま）。"""
        encoded = features[list(self._columns)].copy()
        for column in self._categorical_columns:
            encoded[column] = encoded[column].astype("str").fillna(MISSING).astype(object)
        return encoded
