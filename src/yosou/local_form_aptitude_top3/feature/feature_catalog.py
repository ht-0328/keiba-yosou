"""この予想が使う特徴量の一覧（設計書 09・07）。

中央の予想の今の材料（A〜I・J・L）から調教（I。地方競馬DATA に無い）を除き、対戦レーティング（O）を3つの時点で、
券種の支持（N）を当日に、勝ち切る材料（Q）を当日の1着のモデルに使う。地方には出走馬名表の段階が無く、最初の時点（出馬表）で
枠番・馬番が決まっているので、その2つは出馬表から分かるものに付け直す。
"""

from __future__ import annotations

from dataclasses import replace

from yosou.shared.feature import (
    BASE_FEATURES,
    FINISH_POWER_FEATURES,
    HEAD_TO_HEAD_FEATURES,
    MARKET_FEATURES,
    PEOPLE_MARKET_FEATURES,
    POOL_SUPPORT_FEATURES,
    Feature,
    FeatureCatalog,
    PredictionTiming,
)

#: 使わないまとまり（調教）。
_WORKOUT_GROUP = "I"
#: 出馬表の時点から分かるようになる特徴量（中央では前日から）。
_KNOWN_FROM_ENTRY_LIST: frozenset[str] = frozenset({"枠番", "馬番"})


def _local_feature(feature: Feature) -> Feature:
    """枠番・馬番は出馬表（共通の最初の時点）から分かる。ほかは中央と同じ。"""
    if feature.name in _KNOWN_FROM_ENTRY_LIST:
        return replace(feature, known_from=PredictionTiming.THURSDAY)
    return feature


#: 土台の 65個（A〜H）。
LOCAL_BASE_FEATURES: tuple[Feature, ...] = tuple(
    _local_feature(feature) for feature in BASE_FEATURES if feature.group != _WORKOUT_GROUP
)
#: 勝ち切る材料（Q）は、過去のレースの結果だけから作るので出馬表から分かるが、この予想では当日の1着のモデルだけが使う（設計書 07・09 の Q）。
#: 一覧の「いつから分かるか」を当日にして、出馬表・前日のモデルには渡さない。
_RACE_DAY_FINISH_POWER_FEATURES: tuple[Feature, ...] = tuple(
    replace(feature, known_from=PredictionTiming.RACE_DAY) for feature in FINISH_POWER_FEATURES
)

#: この予想の特徴量の一覧（96個）。出馬表は 69個、前日は 78個、当日は 86個（3着以内）・96個（1着）で学ぶ（設計書 07）。
CATALOG = FeatureCatalog(
    LOCAL_BASE_FEATURES + MARKET_FEATURES + PEOPLE_MARKET_FEATURES + HEAD_TO_HEAD_FEATURES
    + POOL_SUPPORT_FEATURES + _RACE_DAY_FINISH_POWER_FEATURES
)
