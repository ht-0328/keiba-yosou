"""どの予想でも使う特徴量 71個の一覧（設計書 09-features.md の表の写し）と、人気を使う予想が足す4個・オッズの3個、
オッズを使う予想が足す4個、騎手・調教師・血統の市場に対する成績の4個、馬の力の材料の202個、券種ごとのオッズから見た
支持の6個、予想ごとの一覧を表す値。

特徴量の名前・まとまり（A〜N）・数値かカテゴリか・いつから分かるか（設計書 07）は、ここだけに書く
（馬の力の材料は数が多いので、名前の並びは ``ability/ability_columns.py`` に置き、ここで時点を付ける）。
予想ごとに特徴量を足すときは、``BASE_FEATURES`` に足した一覧で ``FeatureCatalog`` を作る。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

import pandas as pd

from ..repository import POOLS
from .ability import DAY_BEFORE_COLUMNS, RACE_DAY_COLUMNS, ability_columns
from .feature import Feature
from .head_to_head import HEAD_TO_HEAD_NAMES
from .feature_kind import FeatureKind
from .prediction_timing import PredictionTiming

_N = FeatureKind.NUMERIC
_C = FeatureKind.CATEGORICAL
#: 前日から分かる（枠番・馬番は出馬表、馬場状態は前日発表）。当日から分かる（馬体重の発表は当日）。
_DAY_BEFORE = PredictionTiming.DAY_BEFORE
_RACE_DAY = PredictionTiming.RACE_DAY

#: どの予想でも使う特徴量 71個。並びは設計書 09 の表の順。時点を書いていないものは木曜から分かる。
BASE_FEATURES: tuple[Feature, ...] = (
    # A. レースの条件（9個）
    Feature("競馬場", "A", _C),
    Feature("芝ダ", "A", _C),
    Feature("コース", "A", _C),
    Feature("距離", "A", _N),
    Feature("馬場状態", "A", _C, _DAY_BEFORE),
    Feature("クラス", "A", _N),
    Feature("出走頭数", "A", _N),
    Feature("開催月", "A", _N),
    Feature("牡馬と牝馬が一緒に走るか", "A", _C),
    # B. 馬のこと（9個）
    Feature("性別", "B", _C),
    Feature("馬齢", "B", _N),
    Feature("所属", "B", _C),
    Feature("枠番", "B", _N, _DAY_BEFORE),
    Feature("馬番", "B", _N, _DAY_BEFORE),
    Feature("斤量", "B", _N),
    Feature("馬体重", "B", _N, _RACE_DAY),
    Feature("馬体重の増減", "B", _N, _RACE_DAY),
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
    # F. この条件での経験（10個）。馬場状態で分けて数えるものは、馬場状態が決まる前日から
    Feature("同じ競馬場・芝ダでの通算の出走数", "F", _N),
    Feature("同じ競馬場・芝ダでの通算の3着以内の数", "F", _N),
    Feature("同じ芝ダ・距離帯での通算の出走数", "F", _N),
    Feature("同じ芝ダ・距離帯での通算の3着以内の数", "F", _N),
    Feature("同じ芝ダ・馬場状態での通算の出走数", "F", _N, _DAY_BEFORE),
    Feature("同じ芝ダ・馬場状態での通算の3着以内の数", "F", _N, _DAY_BEFORE),
    Feature("同じ競馬場・コース・距離での出走数", "F", _N),
    Feature("同じ競馬場・コース・距離での3着以内の数", "F", _N),
    Feature("持ち時計のレース内順位（コース単位）", "F", _N, _DAY_BEFORE),
    Feature("持ち時計のレース内順位（距離単位）", "F", _N, _DAY_BEFORE),
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

#: 人気を使う予想（``favorites_out_of_top3``・``longshots_in_top3``）が A〜I に足す、J. 人気と人気の履歴（4個）。
#: どれも大小に意味がある数なので、数値特徴量にする。作るのは ``group/popularity_history_features.py``。
POPULARITY_FEATURES: tuple[Feature, ...] = (
    Feature("人気順位", "J", _N),
    Feature("前走の人気と着順の差", "J", _N),
    Feature("近5走で人気より悪い着順だった回数", "J", _N),
    Feature("近5走の平均人気", "J", _N),
)

#: オッズを使う予想（``form_aptitude_top3``・``upset_level``）が A〜I に足す、J. 市場の評価（4個）。
#: オッズが分かるのは、前日発売が始まる前日から（手本の設計書 07）。作るのは ``group/market_features.py``。
#: オッズから見た3着以内率は、既存モデルの修正計画（2「オッズの使い方」）で足した（Harville の式）。
MARKET_FEATURES: tuple[Feature, ...] = (
    Feature("単勝オッズ", "J", _N, _DAY_BEFORE),
    Feature("人気順位", "J", _N, _DAY_BEFORE),
    Feature("オッズから見た勝率", "J", _N, _DAY_BEFORE),
    Feature("オッズから見た3着以内率", "J", _N, _DAY_BEFORE),
)

#: 人気を使う予想（``favorites_out_of_top3``・``longshots_in_top3``）が、人気の履歴（J）に足す K. 単勝オッズから見た評価（3個）。
#: 人気順位だけでは分からない支持の強さを使うため（既存モデルの修正計画の 2）。前日から分かる。作るのは ``group/odds_features.py``。
ODDS_FEATURES: tuple[Feature, ...] = (
    Feature("単勝オッズ", "K", _N, _DAY_BEFORE),
    Feature("オッズから見た勝率", "K", _N, _DAY_BEFORE),
    Feature("オッズから見た3着以内率", "K", _N, _DAY_BEFORE),
)

#: 全頭の3着以内・穴馬・人気馬の予想（``form_aptitude_top3``・``longshots_in_top3``・``favorites_out_of_top3``）が足す、
#: L. 騎手・調教師・血統の市場に対する成績（4個）。オッズから期待された3着以内率をどれだけ上回ったかを、開催日の前日までの
#: 365日で数える。過去のレースのオッズだけを使うので、木曜から分かる。作るのは ``group/people_market_features.py``。
#: 研究「既存モデルの改善」の材料の実験で採用の基準を満たし、2026-09-30 に利用者が採用を決めた。
PEOPLE_MARKET_FEATURES: tuple[Feature, ...] = (
    Feature("騎手の市場に対する超過3着以内率", "L", _N),
    Feature("調教師の市場に対する超過3着以内率", "L", _N),
    Feature("父の産駒の市場に対する超過3着以内率", "L", _N),
    Feature("母の父の産駒の市場に対する超過3着以内率", "L", _N),
)


def _ability_timing(name: str) -> PredictionTiming:
    """馬の力の材料が分かる最初の時点。枠番・馬番・馬場状態を使うものは前日、馬体重を使うものは当日、ほかは木曜。"""
    if name in RACE_DAY_COLUMNS:
        return _RACE_DAY
    if name in DAY_BEFORE_COLUMNS:
        return _DAY_BEFORE
    return PredictionTiming.THURSDAY


#: 全頭の3着以内の予想（``form_aptitude_top3``）の木曜（と前日）のモデルが使う、M. 馬の力の材料（202個。どれも数値）。
#: 研究「馬の力と展開でオッズに勝つ」のオッズを使わない 197個と、研究「一番人気を疑う」で足したセリの価格の5個。
#: 作るのは ``group/horse_ability_features.py``（部品は ``ability/``）。
ABILITY_FEATURES: tuple[Feature, ...] = tuple(Feature(name, "M", _N, _ability_timing(name)) for name in ability_columns())

#: 全頭の3着以内の予想の当日のモデルが足す、N. 券種ごとのオッズから見た支持（6個）。
#: log（券種のオッズから見た確率）− log（単勝オッズから見た確率）。並びは ``POOLS``（3連単・馬単・3連複・馬連・ワイド・複勝）。
#: 券種のオッズがそろうのは当日。作るのは ``group/pool_support_features.py``。
POOL_SUPPORT_NAMES: tuple[str, ...] = tuple(f"{spec.name}と単勝の比（log）" for spec in POOLS)
POOL_SUPPORT_FEATURES: tuple[Feature, ...] = tuple(Feature(name, "N", _N, _RACE_DAY) for name in POOL_SUPPORT_NAMES)

#: O. 対戦レーティング（7個。どれも数値）。同じレースを走った馬どうしの着順の勝ち負けから、Elo のレーティングを開催日の順に
#: 更新して作る。過去のレースの結果だけから作るので、木曜から分かる。作るのは ``group/head_to_head_rating_features.py``
#: （部品は ``head_to_head/``）。研究「既存モデルの改善」で、近走と適性の予想に足して時点ごとに7つの区切りで比べる。
HEAD_TO_HEAD_FEATURES: tuple[Feature, ...] = tuple(Feature(name, "O", _N) for name in HEAD_TO_HEAD_NAMES)


@dataclass(frozen=True)
class FeatureCatalog:
    """1つの予想が使う特徴量の一覧。名前の並びと、カテゴリ特徴量と、時点ごとに使う列を答える。

    手本の予想は ``FeatureCatalog(BASE_FEATURES)``。人気を使う予想は ``FeatureCatalog(BASE_FEATURES + POPULARITY_FEATURES)``。
    同じ名前が2つあれば作れない。
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
        return tuple(feature.name for feature in self.features if feature.is_known_at(timing))

    def categorical_columns_of(self, features: pd.DataFrame) -> tuple[str, ...]:
        """特徴量の表の列のうち、カテゴリ特徴量の名前（列の並び順）。"""
        categorical = self.categorical
        return tuple(column for column in features.columns if column in categorical)
