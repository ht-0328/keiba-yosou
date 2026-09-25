"""特徴量の表を、距離を測れる数の行列にする。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from yosou.shared.feature import FeatureCatalog, as_numbers

#: 標準偏差がこれより小さい列（どの行もほぼ同じ値）は、距離に効かないので使わない。
_MIN_SPREAD = 1e-9
#: 「欠損値だったか」の列の名前に付ける印。
_MISSING_SUFFIX = "（欠損値）"
#: 0 と 1 の列に掛ける値。値が違う2頭の距離への寄与（2つの列が 1 ずつ違う）を、標準化した数の列の
#: 標準偏差1つ分にそろえる。0 と 1 の列を標準化すると、めったに無い値ほど強く効いてしまうので、標準化はしない。
_FLAG_SCALE = 1 / np.sqrt(2)


class FeatureMatrix:
    """特徴量の表 → 距離を測る行列（設計書 12）。単位ごとに1つ作り、学習データで ``fit`` した変換を予測にも使う。

    - 数の列: 欠損値を単位の中央値で埋め、標準化する（平均 0・標準偏差 1）。``add_missing_flags`` なら、
      学習データで欠損値があった列ごとに「欠損値だったか」（0 か 1）の列も足す。
    - カテゴリの列: 値ごとの 0 と 1 の列にする（one-hot）。学習データに無い値と欠損値は、どの列も 0。
    - 0 と 1 の列（欠損値だったか・one-hot）は標準化せず、1/√2 を掛ける（``_FLAG_SCALE``）。
    - どの列にも、その特徴量のまとまり（A〜K）の重みを掛ける。``excluded`` の特徴量と、重みが 0 のまとまりは使わない。
    """

    def __init__(self, catalog: FeatureCatalog, excluded: Sequence[str], group_weights: Mapping[str, float],
                 add_missing_flags: bool) -> None:
        self._categorical = catalog.categorical
        self._group_of = {feature.name: feature.group for feature in catalog.features}
        self._excluded = frozenset(excluded)
        self._group_weights = dict(group_weights)
        self._add_missing_flags = add_missing_flags
        self._numeric: list[str] = []
        self._flagged: list[str] = []
        self._categories: dict[str, list[str]] = {}
        self._medians = pd.Series(dtype=float)
        self._means = pd.Series(dtype=float)
        self._spreads = pd.Series(dtype=float)
        self._weights = np.empty(0)

    def fit(self, features: pd.DataFrame) -> FeatureMatrix:
        """``features``（1つの単位の、3つのグループを合わせた学習データ）で、埋める値・標準化の物差し・列を決める。"""
        used = [column for column in features.columns if self._weight_of(column) > 0]
        numbers = self._numbers(features, [column for column in used if column not in self._categorical])
        self._medians = numbers.median().fillna(0.0)
        filled = numbers.fillna(self._medians)
        spreads = filled.std(ddof=0)
        self._numeric = [column for column in filled.columns if spreads[column] > _MIN_SPREAD]
        self._means, self._spreads = filled[self._numeric].mean(), spreads[self._numeric]
        self._flagged = [column for column in self._numeric if self._add_missing_flags and numbers[column].isna().any()]
        self._categories = {column: self._values_of(features[column])
                            for column in used if column in self._categorical}
        self._weights = np.array([self._weight_of(self._source_of(name)) for name in self.column_names])
        return self

    @property
    def column_names(self) -> list[str]:
        """行列の列の名前（数の列 → 欠損値だったかの列 → one-hot の列）。"""
        flags = [f"{column}{_MISSING_SUFFIX}" for column in self._flagged]
        dummies = [f"{column}={value}" for column, values in self._categories.items() for value in values]
        return [*self._numeric, *flags, *dummies]

    def transform(self, features: pd.DataFrame) -> np.ndarray:
        """``fit`` で決めた変換で、行列にする。行の並びは ``features`` と同じ。"""
        numbers = self._numbers(features, self._numeric)
        scaled = (numbers.fillna(self._medians[self._numeric]) - self._means) / self._spreads
        flags = numbers[self._flagged].isna().astype(float).add_suffix(_MISSING_SUFFIX) * _FLAG_SCALE
        dummies = [self._one_hot(features[column], values) * _FLAG_SCALE
                   for column, values in self._categories.items()]
        matrix = pd.concat([scaled, flags, *dummies], axis=1)
        return matrix.to_numpy(dtype=float) * self._weights

    def _numbers(self, features: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
        return pd.DataFrame({column: as_numbers(features[column]) for column in columns}, index=features.index)

    def _one_hot(self, values: pd.Series, categories: list[str]) -> pd.DataFrame:
        """学習データの値ごとの 0 と 1 の列。学習データに無い値と欠損値は、どの列も 0。"""
        texts = values.astype(object).where(values.notna()).map(str, na_action="ignore")
        return pd.DataFrame({f"{values.name}={value}": (texts == value).astype(float) for value in categories},
                            index=values.index)

    def _values_of(self, values: pd.Series) -> list[str]:
        return sorted(str(value) for value in values.dropna().unique())

    def _source_of(self, name: str) -> str:
        """行列の列の名前から、元の特徴量の名前。"""
        return name.split("=", 1)[0].removesuffix(_MISSING_SUFFIX)

    def _weight_of(self, column: str) -> float:
        """その特徴量の重み。使わない特徴量と、一覧に無い列は 0。"""
        if column in self._excluded or column not in self._group_of:
            return 0.0
        return self._group_weights.get(self._group_of[column], 1.0)
