"""比べる作り方（学習に使うレースの範囲 × サインを足すか）の並び。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.favorites_out_of_top3.dataset import FAVORITE_BAND
from yosou.shared.feature import BASE_FEATURES, ODDS_FEATURES, PEOPLE_MARKET_FEATURES, POPULARITY_FEATURES

from 既存モデルの改善.analysis.variants import ModelVariant

from .race_scope import ALL_RACES, SCOPES, RaceScope
from .sign_features import SIGN_FEATURES

#: 学習データの表の名前（予測の置き場所のフォルダ名にもなる）。
TABLE_NAME = "favorites_signs"
#: 今の本番の人気馬の予想の列（手本の71個・人気と人気の履歴・単勝オッズから見た評価・市場に対する成績）。
CURRENT_COLUMNS: tuple[str, ...] = tuple(
    feature.name for feature in (*BASE_FEATURES, *POPULARITY_FEATURES, *ODDS_FEATURES, *PEOPLE_MARKET_FEATURES))
SIGN_NAMES: tuple[str, ...] = tuple(feature.name for feature in SIGN_FEATURES)
#: オッズだけの列（オッズから出した値と頭数だけ）。
ODDS_ONLY_COLUMNS: tuple[str, ...] = ("人気順位", *(feature.name for feature in ODDS_FEATURES), "出走頭数")


@dataclass(frozen=True)
class SignVariant:
    """比べる作り方1つ。学習に使うレースの範囲（``scope``）と、モデルの作り方（``variant``。列・基準・人気帯で分けるか）。"""

    scope: RaceScope
    variant: ModelVariant

    @property
    def key(self) -> str:
        return self.variant.key

    @property
    def name(self) -> str:
        return self.variant.name


def _variant(scope: RaceScope, with_signs: bool) -> SignVariant:
    """全レースは今の本番と同じく人気帯で分けて学ぶ。G1だけ・重賞は行が少ないので分けない。"""
    columns = CURRENT_COLUMNS + (SIGN_NAMES if with_signs else ())
    key = f"{scope.key}-{'signs' if with_signs else 'current'}"
    name = f"{scope.label}で学ぶ・{'今の材料 ＋ サイン' if with_signs else '今の材料'}"
    segment = FAVORITE_BAND if scope is ALL_RACES else None
    return SignVariant(scope, ModelVariant(TABLE_NAME, key, name, columns, uses_baseline=True, segment_column=segment))


#: オッズだけ（全レースで学ぶ。採否の物差し）。
ODDS_ONLY = SignVariant(ALL_RACES, ModelVariant(TABLE_NAME, "odds_only", "オッズだけ（全レースで学ぶ）", ODDS_ONLY_COLUMNS,
                                                uses_baseline=True))
#: 比べる作り方の並び。全レース × 今の材料が、今の本番と同じ作り。
SIGN_VARIANTS: tuple[SignVariant, ...] = (
    ODDS_ONLY,
    *(_variant(scope, with_signs) for scope in SCOPES for with_signs in (False, True)),
)


def sign_variant_named(key: str) -> SignVariant:
    for variant in SIGN_VARIANTS:
        if variant.key == key:
            return variant
    raise ValueError(f"その作り方はありません: {key}（{' / '.join(variant.key for variant in SIGN_VARIANTS)}）")
