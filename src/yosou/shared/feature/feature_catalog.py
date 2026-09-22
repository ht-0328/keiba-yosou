"""どの予想でも使う特徴量 71個の一覧（設計書 09-features.md の表の写し）と、予想ごとの一覧を表す値。

特徴量の名前・まとまり（A〜I）・数値かカテゴリかは、ここだけに書く。
予想ごとに特徴量を足すときは、``BASE_FEATURES`` に足した一覧で ``FeatureCatalog`` を作る。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import pandas as pd

from .feature import Feature
from .feature_kind import FeatureKind
from .prediction_timing import PredictionTiming

_N = FeatureKind.NUMERIC
_C = FeatureKind.CATEGORICAL

#: どの予想でも使う特徴量 71個。並びは設計書 09 の表の順。
BASE_FEATURES: tuple[Feature, ...] = (
    # A. レースの条件（9個）
    Feature("競馬場", "A", _C),
    Feature("芝ダ", "A", _C),
    Feature("コース", "A", _C),
    Feature("距離", "A", _N),
    Feature("馬場状態", "A", _C),
    Feature("クラス", "A", _N),
    Feature("出走頭数", "A", _N),
    Feature("開催月", "A", _N),
    Feature("牡馬と牝馬が一緒に走るか", "A", _C),
    # B. 馬のこと（9個）
    Feature("性別", "B", _C),
    Feature("馬齢", "B", _N),
    Feature("所属", "B", _C),
    Feature("枠番", "B", _N),
    Feature("馬番", "B", _N),
    Feature("斤量", "B", _N),
    Feature("馬体重", "B", _N),
    Feature("馬体重の増減", "B", _N),
    Feature("ブリンカー", "B", _C),
    # C. 騎手と調教師（6個）
    Feature("騎手", "C", _C),
    Feature("騎手の減量", "C", _C),
    Feature("乗り替わり", "C", _C),
    Feature("調教師", "C", _C),
    Feature("騎手の近1年の3着以内の割合", "C", _N),
    Feature("調教師の近1年の3着以内の割合", "C", _N),
    # D. 前走（11個）
    Feature("前走の着順", "D", _N),
    Feature("前走の着差", "D", _N),
    Feature("前走の人気", "D", _N),
    Feature("前走の上がり3F", "D", _N),
    Feature("前走の上がり3Fのレース内順位", "D", _N),
    Feature("前走の4コーナーの位置", "D", _N),
    Feature("前走からの日数", "D", _N),
    Feature("距離の変更", "D", _C),
    Feature("芝ダ替わり", "D", _C),
    Feature("クラスの変更", "D", _C),
    Feature("前走と同じ競馬場か", "D", _C),
    # E. 近走のまとめ（10個）
    Feature("近5走の数", "E", _N),
    Feature("近5走の平均着順", "E", _N),
    Feature("近5走の最高着順", "E", _N),
    Feature("近5走の平均着差", "E", _N),
    Feature("近5走の平均上がり順位", "E", _N),
    Feature("近5走の平均4コーナー位置", "E", _N),
    Feature("推定脚質", "E", _C),
    Feature("通算の出走数", "E", _N),
    Feature("通算の勝利数", "E", _N),
    Feature("通算の3着以内の数", "E", _N),
    # F. この条件での経験（10個）
    Feature("同じ競馬場・芝ダでの通算の出走数", "F", _N),
    Feature("同じ競馬場・芝ダでの通算の3着以内の数", "F", _N),
    Feature("同じ芝ダ・距離帯での通算の出走数", "F", _N),
    Feature("同じ芝ダ・距離帯での通算の3着以内の数", "F", _N),
    Feature("同じ芝ダ・馬場状態での通算の出走数", "F", _N),
    Feature("同じ芝ダ・馬場状態での通算の3着以内の数", "F", _N),
    Feature("同じ競馬場・コース・距離での出走数", "F", _N),
    Feature("同じ競馬場・コース・距離での3着以内の数", "F", _N),
    Feature("持ち時計のレース内順位（コース単位）", "F", _N),
    Feature("持ち時計のレース内順位（距離単位）", "F", _N),
    # G. 同じレースの馬との比較（4個）
    Feature("逃げそうな馬の数", "G", _N),
    Feature("近5走の平均着差のレース内順位", "G", _N),
    Feature("斤量とレースの平均との差", "G", _N),
    Feature("騎手の3着以内の割合のレース内順位", "G", _N),
    # H. 血統（6個）
    Feature("父", "H", _C),
    Feature("父の父", "H", _C),
    Feature("母の父", "H", _C),
    Feature("父の産駒の近1年の3着以内の割合", "H", _N),
    Feature("父の産駒の同じ芝ダでの近1年の3着以内の割合", "H", _N),
    Feature("母の父の産駒の近1年の3着以内の割合", "H", _N),
    # I. 調教（6個）
    Feature("直近の調教のコース", "I", _C),
    Feature("坂路の直近の4ハロンタイム", "I", _N),
    Feature("坂路の直近のラスト1ハロン", "I", _N),
    Feature("ウッドの直近の4ハロンタイム", "I", _N),
    Feature("ウッドの直近のラスト1ハロン", "I", _N),
    Feature("14日以内の調教の本数", "I", _N),
)


@dataclass(frozen=True)
class FeatureCatalog:
    """1つの予想が使う特徴量の一覧。名前の並びと、カテゴリ特徴量と、時点ごとに使う列を答える。

    手本の予想は ``FeatureCatalog(BASE_FEATURES)``。特徴量を足す予想は、足した一覧で作る
    （例: ``FeatureCatalog(BASE_FEATURES + POPULARITY_FEATURES)``）。同じ名前が2つあれば作れない。
    """

    features: tuple[Feature, ...]

    def __post_init__(self) -> None:
        duplicated = [name for name, count in Counter(self.names).items() if count > 1]
        if duplicated:
            raise ValueError(f"特徴量の名前が重なっています: {'・'.join(duplicated)}")

    @property
    def names(self) -> tuple[str, ...]:
        """特徴量の名前の並び（一覧の順）。学習データの列の並びになる。"""
        return tuple(feature.name for feature in self.features)

    @property
    def categorical(self) -> frozenset[str]:
        """カテゴリ特徴量の名前。"""
        return frozenset(feature.name for feature in self.features if feature.is_categorical)

    def columns_for(self, timing: PredictionTiming) -> tuple[str, ...]:
        """その時点で使う特徴量の名前（設計書 07）。並びは一覧の順。"""
        unknown = timing.unknown_features
        return tuple(name for name in self.names if name not in unknown)

    def categorical_columns_of(self, features: pd.DataFrame) -> tuple[str, ...]:
        """特徴量の表の列のうち、カテゴリ特徴量の名前（列の並び順）。"""
        categorical = self.categorical
        return tuple(column for column in features.columns if column in categorical)
