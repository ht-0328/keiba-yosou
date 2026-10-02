"""特徴量の表を、距離を測れる数の行列にする。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature import FeatureCatalog, as_numbers

from .matrix_options import MatrixOptions
from .one_hot_encoding import FLAG_SCALE

#: 標準偏差がこれより小さい列（どの行もほぼ同じ値）は、距離に効かないので使わない。
_MIN_SPREAD = 1e-9
#: 「欠損値だったか」の列の名前に付ける印。
_MISSING_SUFFIX = "（欠損値）"


class FeatureMatrix:
    """特徴量の表 → 距離を測る行列（設計書 12）。単位ごとに1つ作り、学習データで ``fit`` した変換を予測にも使う。

    - 数の列: 欠損値を単位の中央値で埋め、方針のそろえ方（標準化 か 順位。``StandardScaling``・``RankScaling``）でそろえる。
      どの行も同じ値の列は使わない。``add_missing_flags`` なら、学習データで欠損値があった列ごとに「欠損値だったか」
      （0 か 1。1/√2 を掛ける）の列も足す。
    - カテゴリの列: 方針の直し方（one-hot か 馬券外率。``OneHotEncoding``・``OutRateEncoding``）で数の列にする。
    - 重み: どの列にも、その特徴量のまとまり（A〜K）の重みと、方針の列ごとの重み（``EqualWeighting``・``AucWeighting``）を掛ける。
      ``excluded`` の特徴量と、重みが 0 のまとまりは使わない。
    """

    def __init__(self, catalog: FeatureCatalog, options: MatrixOptions) -> None:
        self._categorical = catalog.categorical
        self._group_of = {feature.name: feature.group for feature in catalog.features}
        self._options = options
        self._scaling = options.new_scaling()
        self._encoding = options.new_encoding()
        self._weighting = options.new_weighting()
        self._numeric: list[str] = []
        self._flagged: list[str] = []
        self._medians = pd.Series(dtype=float)
        self._weights = np.empty(0)

    def fit(self, features: pd.DataFrame, is_out: pd.Series | None = None) -> FeatureMatrix:
        """``features``（1つの単位の、3つのグループを合わせた学習データ）で、埋める値・そろえ方・列・重みを決める。

        ``is_out`` は行ごとに馬券外か。カテゴリを馬券外率に直すときと、列ごとの重みを馬券外との AUC で決めるときに使う。
        """
        used = [column for column in features.columns if self._weight_of(column) > 0]
        numbers = self._numbers(features, [column for column in used if column not in self._categorical])
        self._medians = numbers.median().fillna(0.0)
        filled = numbers.fillna(self._medians)
        spreads = filled.std(ddof=0)
        self._numeric = [column for column in filled.columns if spreads[column] > _MIN_SPREAD]
        self._scaling.fit(filled[self._numeric])
        self._flagged = [column for column in self._numeric
                         if self._options.add_missing_flags and numbers[column].isna().any()]
        self._encoding.fit(features[[column for column in used if column in self._categorical]], is_out)
        unweighted = self._unweighted(features).to_numpy(dtype=float)
        group_weights = np.array([self._weight_of(source) for source in self._sources()])
        column_weights = self._weighting.fit(unweighted * group_weights, is_out).weights
        self._weights = group_weights * column_weights
        return self

    @property
    def column_names(self) -> list[str]:
        """行列の列の名前（数の列 → 欠損値だったかの列 → カテゴリから直した列）。"""
        flags = [f"{column}{_MISSING_SUFFIX}" for column in self._flagged]
        return [*self._numeric, *flags, *self._encoding.column_names]

    @property
    def weights(self) -> np.ndarray:
        """列ごとの重み（まとまりの重み × 列ごとの重み）。``column_names`` と同じ並び。"""
        return self._weights

    def transform(self, features: pd.DataFrame) -> np.ndarray:
        """``fit`` で決めた変換で、行列にする。行の並びは ``features`` と同じ。"""
        return self._unweighted(features).to_numpy(dtype=float) * self._weights

    def _unweighted(self, features: pd.DataFrame) -> pd.DataFrame:
        """重みを掛ける前の行列（列は ``column_names`` の並び）。"""
        numbers = self._numbers(features, self._numeric)
        scaled = self._scaling.transform(numbers.fillna(self._medians[self._numeric]))
        flags = numbers[self._flagged].isna().astype(float).add_suffix(_MISSING_SUFFIX) * FLAG_SCALE
        return pd.concat([scaled, flags, self._encoding.transform(features)], axis=1)

    def _sources(self) -> list[str]:
        """列ごとの、元の特徴量の名前（``column_names`` と同じ並び）。"""
        return [*self._numeric, *self._flagged, *self._encoding.sources]

    def _numbers(self, features: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        return pd.DataFrame({column: as_numbers(features[column]) for column in columns}, index=features.index)

    def _weight_of(self, column: str) -> float:
        """その特徴量のまとまりの重み。使わない特徴量と、一覧に無い列は 0。"""
        if column in self._options.excluded or column not in self._group_of:
            return 0.0
        return self._options.group_weights.get(self._group_of[column], 1.0)
