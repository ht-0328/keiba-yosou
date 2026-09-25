"""モデルで探す設定の一覧。目的 × 特徴量の組 × レースの区分。

``form`` は馬柱の特徴量で探した最初の探索、``pool`` は券種オッズの特徴量を足した探索
（計画「券種オッズの特徴量で、custom_binary を回収率 100% 超にする計画」）。
"""

from yosou.custom_binary.repository import POOLS
from yosou.shared.feature.feature_catalog import BASE_FEATURES, ODDS_FEATURES, POPULARITY_FEATURES

from .model_config import ModelConfig
from .race_segments import DISTANCE_BANDS

TARGETS = {"win": "勝利", "top3": "馬券内"}
#: 調教（I）は 2021年8月からしか記録がそろわないので、2017年から学ぶ探索では使わない。
_FORM = tuple(
    feature.name for feature in (*BASE_FEATURES, *POPULARITY_FEATURES)
    if feature.group != "I" and feature.name != "人気順位"
)
FEATURE_SETS = {
    # 馬柱だけ（今回のオッズ・人気を使わない）。市場と違う見方ができるかを見る。
    "form": _FORM,
    # 馬柱に今回の人気とオッズを足す。市場の値段と馬柱のずれを学ばせる。
    "form_odds": (*_FORM, "人気順位", *(feature.name for feature in ODDS_FEATURES)),
    # 馬柱だけを特徴量にし、オッズから見た確率を出発点（odds_baseline）にする。
    # モデルは「同じオッズの馬より来やすいか」だけを学ぶので、確率×オッズの期待値がそのまま使える。
    "form_base": _FORM,
}
#: odds_baseline を使う特徴量の組。
BASELINE_SETS = {"form_base"}
_SURFACES = {"turf": "芝", "dirt": "ダート"}
_BANDS = {"sprint": "短距離", "mile": "マイル", "middle": "中距離", "long": "長距離"}


def segments() -> dict[str, dict]:
    result = {"all": {}}
    for surface_code, surface in _SURFACES.items():
        for band_code, band in _BANDS.items():
            low, high = DISTANCE_BANDS[band]
            distance = {key: value for key, value in (("min", low), ("max", high)) if value is not None}
            result[f"{surface_code}_{band_code}"] = {"芝ダ": [surface], "距離": distance}
    return result


#: 券種オッズの特徴量12個（券種ごとの確率と、単勝との差）。
POOL_FEATURES = (*(spec.name for spec in POOLS), *(f"{spec.name}と単勝の差" for spec in POOLS))
#: 券種オッズの探索で、区分ごとに見る人気帯。
POPULARITY_BANDS = {"pop1_3": {"min": 1, "max": 3}, "pop4_6": {"min": 4, "max": 6},
                    "pop7_9": {"min": 7, "max": 9}, "pop10_": {"min": 10}}


def model_configs(group: str = "form") -> list[ModelConfig]:
    if group == "pool":
        return pool_configs()
    return [
        ModelConfig(f"{target_code}_{set_code}_{segment_code}", target, features, conditions, {}, set_code in BASELINE_SETS)
        for target_code, target in TARGETS.items()
        for set_code, features in FEATURE_SETS.items()
        for segment_code, conditions in segments().items()
    ]


def pool_configs() -> list[ModelConfig]:
    """どれも馬券内（複勝）・odds_baseline あり・期待値の線だけから買い方を選ぶ。"""
    def config(name: str, features: tuple[str, ...], conditions: dict, popularity: dict) -> ModelConfig:
        return ModelConfig(name, "馬券内", features, conditions, popularity, odds_baseline=True, value_lines_only=True)

    main = (*_FORM, *POOL_FEATURES)
    configs = [
        config("pool_ref_form_all", _FORM, {}, {}),     # 比べる相手（券種オッズなし）
        config("pool_main_all", main, {}, {}),          # 本命
        config("pool_only_all", POOL_FEATURES, {}, {}),  # 券種オッズだけ
    ]
    configs += [config(f"pool_main_{code}", main, conditions, {}) for code, conditions in segments().items() if code != "all"]
    configs += [config(f"pool_main_{code}", main, {}, popularity) for code, popularity in POPULARITY_BANDS.items()]
    return configs
