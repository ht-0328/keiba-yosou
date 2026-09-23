"""予想ごとの、比べるモデルの作り方の並び。"""

from __future__ import annotations

from yosou.favorites_out_of_top3.dataset import FAVORITE_BAND
from yosou.longshots_in_top3.dataset import LONGSHOT_ZONE
from yosou.shared.feature import BASE_FEATURES, ODDS_FEATURES, POPULARITY_FEATURES

from ..experiments import CONDITION_COLUMNS, EXPERIMENT_GROUPS
from ..experiments.condition_columns import DISTANCE_BAND, FIELD_BAND, SURFACE, SURFACE_DISTANCE, VENUE_GROUP
from .model_variant import ModelVariant

#: どの予想でも使う 71個。
_BASE = tuple(feature.name for feature in BASE_FEATURES)
#: 直す前の、全頭の予想の市場の評価（3個）。
_OLD_MARKET = ("単勝オッズ", "人気順位", "オッズから見た勝率")
#: 直した後に足した、オッズから見た3着以内率（Harville の式）。
_TOP3_RATE = "オッズから見た3着以内率"
#: 人気を使う予想の、人気と人気の履歴（4個）と、直した後に足した単勝オッズから見た評価（3個）。
_POPULARITY = tuple(feature.name for feature in POPULARITY_FEATURES)
_ODDS = tuple(feature.name for feature in ODDS_FEATURES)
#: オッズだけの基準に使う列（オッズから出した値と頭数だけ。馬の情報は入れない）。
_ODDS_ONLY_FORM = ("単勝オッズ", "人気順位", "オッズから見た勝率", _TOP3_RATE, "出走頭数")
_ODDS_ONLY_POPULARITY = ("人気順位", *_ODDS, "出走頭数")

_FORM, _LONGSHOTS, _FAVORITES = "form_aptitude_top3", "longshots_in_top3", "favorites_out_of_top3"
#: 材料を1つずつ足す実験の表と、その出発点（全頭の変更版の列）。
_EXPERIMENTS = "form_experiments"
_IMPROVED_FORM = _BASE + _OLD_MARKET + (_TOP3_RATE,)
#: 条件で分ける実験の、区分の列 → 保存する名前。
_SPLIT_KEYS = {SURFACE: "split_surface", VENUE_GROUP: "split_venue", DISTANCE_BAND: "split_distance",
               SURFACE_DISTANCE: "split_surface_distance", FIELD_BAND: "split_field"}

VARIANTS: tuple[ModelVariant, ...] = (
    # 全頭の3着以内
    ModelVariant(_FORM, "current", "現行", _BASE + _OLD_MARKET, uses_baseline=False),
    ModelVariant(_FORM, "odds_only", "オッズだけ", _ODDS_ONLY_FORM, uses_baseline=True),
    ModelVariant(_FORM, "improved", "変更版（基準＋補正）", _BASE + _OLD_MARKET + (_TOP3_RATE,), uses_baseline=True),
    # 穴馬の3着以内
    ModelVariant(_LONGSHOTS, "current", "現行", _BASE + _POPULARITY, uses_baseline=False),
    ModelVariant(_LONGSHOTS, "odds_only", "オッズだけ", _ODDS_ONLY_POPULARITY, uses_baseline=True),
    ModelVariant(_LONGSHOTS, "odds_baseline", "基準＋補正（分けない）", _BASE + _POPULARITY + _ODDS, uses_baseline=True),
    ModelVariant(_LONGSHOTS, "improved", "変更版（基準＋補正・中穴と大穴に分ける）", _BASE + _POPULARITY + _ODDS,
                 uses_baseline=True, segment_column=LONGSHOT_ZONE),
    # 人気馬の4着以下
    ModelVariant(_FAVORITES, "current", "現行", _BASE + _POPULARITY, uses_baseline=False),
    ModelVariant(_FAVORITES, "odds_only", "オッズだけ", _ODDS_ONLY_POPULARITY, uses_baseline=True),
    ModelVariant(_FAVORITES, "odds_baseline", "基準＋補正（分けない）", _BASE + _POPULARITY + _ODDS, uses_baseline=True),
    ModelVariant(_FAVORITES, "improved", "変更版（基準＋補正・人気帯で分ける）", _BASE + _POPULARITY + _ODDS,
                 uses_baseline=True, segment_column=FAVORITE_BAND),
    # 全頭の変更版に、材料を1つずつ足す実験と、条件で分ける実験（既存モデルの修正計画の 2・4）
    ModelVariant(_EXPERIMENTS, "base", "変更版（基準＋補正）", _IMPROVED_FORM, uses_baseline=True),
    *(ModelVariant(_EXPERIMENTS, key, f"変更版 ＋ {label}", _IMPROVED_FORM + names, uses_baseline=True)
      for key, (label, names, _) in EXPERIMENT_GROUPS.items()),
    *(ModelVariant(_EXPERIMENTS, _SPLIT_KEYS[column], f"変更版を{column.removeprefix('区分: ')}で分ける", _IMPROVED_FORM,
                   uses_baseline=True, segment_column=column) for column in CONDITION_COLUMNS),
)


def variants_of(model: str) -> list[ModelVariant]:
    """その予想の作り方の並び。"""
    return [variant for variant in VARIANTS if variant.model == model]


def variant_named(model: str, key: str) -> ModelVariant:
    """予想の名前と作り方の名前から引く。知らなければ ``ValueError``。"""
    for variant in variants_of(model):
        if variant.key == key:
            return variant
    keys = " / ".join(variant.key for variant in variants_of(model))
    raise ValueError(f"{model} に、その作り方はありません: {key}（{keys}）")
