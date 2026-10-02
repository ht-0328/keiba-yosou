"""この予想が使う特徴量の一覧（設計書 09）。

この予想は、時点によって2つの材料の組を使い分ける（設計書 07）。

- 今の材料（当日）: どの予想でも同じ A〜I（``BASE_FEATURES``）に、J（市場の評価）の4個と、
  L（騎手・調教師・血統の市場に対する成績）の4個を足す。当日のモデルは N（券種ごとのオッズから見た支持）の6個と、
  M（馬の力の材料。今の材料と同じ名前の2つを除く 200個）も足す。
  L の記号は、穴馬・人気馬の予想（K まである）とそろえた。
- 馬の力の材料（木曜・前日）: M（研究「馬の力と展開でオッズに勝つ」のオッズを使わない材料とセリの価格の 202個）と
  O（対戦レーティングの7個）に、J を足す（J は前日からなので、木曜のモデルは M と O、前日のモデルは M と O と J で学ぶ。
  前日はオッズの基準も使う）。
"""

from __future__ import annotations

from yosou.shared.feature import (
    ABILITY_FEATURES,
    BASE_FEATURES,
    HEAD_TO_HEAD_FEATURES,
    MARKET_FEATURES,
    PEOPLE_MARKET_FEATURES,
    POOL_SUPPORT_FEATURES,
    Feature,
    FeatureCatalog,
)

#: J. 市場の評価（4個）。荒れ具合の予想とも共通なので、一覧は ``yosou.shared.feature`` にある。
J_FEATURES: tuple[Feature, ...] = MARKET_FEATURES

#: 今の材料の特徴量の一覧（まとまり A〜I と J・L。当日は 79個）。当日に券種のオッズが無いときのモデルもこれで学ぶ。
#: 展開の予想・研究も、この一覧の学習データ（``dataset_builder``）を使う。
CATALOG = FeatureCatalog(BASE_FEATURES + J_FEATURES + PEOPLE_MARKET_FEATURES)

#: 今の材料に N を足した一覧（当日は 85個、前日は N を使わないので ``CATALOG`` と同じ 79個のうち前日に分かるもの）。
POOL_CATALOG = FeatureCatalog(CATALOG.features + POOL_SUPPORT_FEATURES)

#: 当日のモデルが今の材料と券種の支持に足す M（今の材料と同じ名前の2つ、前走からの日数・芝ダ替わりを除いた 200個）。
RACE_DAY_ABILITY_FEATURES: tuple[Feature, ...] = tuple(
    feature for feature in ABILITY_FEATURES if feature.name not in POOL_CATALOG.names
)

#: 当日のモデルの特徴量の一覧（今の材料 79個・N 6個・M 200個の 285個）。研究「一番人気を疑う」の直し方を移したあと、
#: 当日に M も足す作り方が、7つの区切りで N だけの作り方より確率の誤差が小さかった（設計書 15 の 11）。
RACE_DAY_CATALOG = FeatureCatalog(POOL_CATALOG.features + RACE_DAY_ABILITY_FEATURES)

#: 馬の力の材料の予想の特徴量の一覧（まとまり M と O と J。木曜は M のうち木曜に分かる 192個と O の7個の 199個）。
#: O（対戦レーティング）は、7つの区切りで木曜・前日に採用の基準を満たしたので足した（当日は満たさず、足していない。設計書 15 の 12）。
ABILITY_CATALOG = FeatureCatalog(ABILITY_FEATURES + HEAD_TO_HEAD_FEATURES + J_FEATURES)
