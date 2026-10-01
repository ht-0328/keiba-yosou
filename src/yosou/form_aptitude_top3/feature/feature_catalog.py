"""この予想が使う特徴量の一覧（設計書 09）。

この予想は、時点によって2つの材料の組を使い分ける（設計書 07）。

- 今の材料（当日）: どの予想でも同じ A〜I（``BASE_FEATURES``）に、J（市場の評価）の4個と、
  L（騎手・調教師・血統の市場に対する成績）の4個を足す。当日のモデルは N（券種ごとのオッズから見た支持）の6個も足す。
  L の記号は、穴馬・人気馬の予想（K まである）とそろえた。
- 馬の力の材料（木曜・前日）: M（研究「馬の力と展開でオッズに勝つ」のオッズを使わない材料とセリの価格の 202個）に、
  J を足す（J は前日からなので、木曜のモデルは M だけ、前日のモデルは M と J で学ぶ。前日はオッズの基準も使う）。
"""

from __future__ import annotations

from yosou.shared.feature import (
    ABILITY_FEATURES,
    BASE_FEATURES,
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

#: 馬の力の材料の予想の特徴量の一覧（まとまり M と J。木曜は M のうち木曜に分かる 192個）。
ABILITY_CATALOG = FeatureCatalog(ABILITY_FEATURES + J_FEATURES)
