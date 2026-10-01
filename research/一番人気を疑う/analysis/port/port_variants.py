"""移したあとの確かめで比べる作り方（時点ごとに、今の予想と移した作り方）。"""

from __future__ import annotations

from dataclasses import dataclass

from 既存モデルの改善.analysis.variants import ModelVariant

from yosou.form_aptitude_top3.feature import ABILITY_CATALOG, CATALOG, POOL_CATALOG
from yosou.shared.feature import PredictionTiming

_THURSDAY, _DAY_BEFORE, _RACE_DAY = PredictionTiming.THURSDAY, PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY


def _variant(table: str, key: str, name: str, columns: tuple[str, ...], timing: PredictionTiming) -> ModelVariant:
    """オッズの分かる前日・当日は、今の予想と同じく、オッズから作った基準を出発点にして学ぶ。"""
    return ModelVariant(table, key, name, columns, uses_baseline=timing is not _THURSDAY, timing=timing)


#: 作り方の一覧。今の予想は、今の本番のモデルと同じ特徴量（A〜L・J の 79個のうち、その時点で分かるもの）。
PORT_VARIANTS: tuple[ModelVariant, ...] = (
    _variant("form_pool", "current-thursday", "今の予想（木曜）", CATALOG.columns_for(_THURSDAY), _THURSDAY),
    _variant("form_ability", "ability-thursday", "馬の力の材料（木曜）", ABILITY_CATALOG.columns_for(_THURSDAY), _THURSDAY),
    _variant("form_pool", "current-day_before", "今の予想（前日）", CATALOG.columns_for(_DAY_BEFORE), _DAY_BEFORE),
    _variant("form_ability", "ability-day_before", "馬の力の材料 ＋ 市場の評価（前日）",
             ABILITY_CATALOG.columns_for(_DAY_BEFORE), _DAY_BEFORE),
    _variant("form_pool", "current-race_day", "今の予想（当日）", CATALOG.columns_for(_RACE_DAY), _RACE_DAY),
    _variant("form_pool", "pool-race_day", "今の予想 ＋ 券種の支持（当日）", POOL_CATALOG.columns_for(_RACE_DAY), _RACE_DAY),
)


@dataclass(frozen=True)
class PortComparisonSpec:
    """1つの時点の比べ方（今の予想の作り方と、移した作り方）。"""

    timing: PredictionTiming
    current: ModelVariant
    ported: ModelVariant


def variant_keyed(key: str) -> ModelVariant:
    """保存する名前から引く。知らなければ ``ValueError``。"""
    for variant in PORT_VARIANTS:
        if variant.key == key:
            return variant
    raise ValueError(f"知らない作り方です: {key}（{' / '.join(variant.key for variant in PORT_VARIANTS)}）")


#: 時点ごとの比べ方。
PORT_COMPARISONS: tuple[PortComparisonSpec, ...] = (
    PortComparisonSpec(_THURSDAY, variant_keyed("current-thursday"), variant_keyed("ability-thursday")),
    PortComparisonSpec(_DAY_BEFORE, variant_keyed("current-day_before"), variant_keyed("ability-day_before")),
    PortComparisonSpec(_RACE_DAY, variant_keyed("current-race_day"), variant_keyed("pool-race_day")),
)
