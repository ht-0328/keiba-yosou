"""対戦レーティングの確かめで比べる作り方（時点ごとに、今の予想と、対戦レーティングを足したもの）。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.form_aptitude_top3.feature import ABILITY_CATALOG, POOL_CATALOG
from yosou.shared.feature import HEAD_TO_HEAD_FEATURES, PredictionTiming

from ..variants import ModelVariant

_THURSDAY, _DAY_BEFORE, _RACE_DAY = PredictionTiming.THURSDAY, PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY
#: 足す7個の名前。
H2H_NAMES: tuple[str, ...] = tuple(feature.name for feature in HEAD_TO_HEAD_FEATURES)
#: 対戦レーティングを足した表の名前（``BASE_TABLES`` の ``rated_name``）。
ABILITY_TABLE, POOL_TABLE = "h2h_ability", "h2h_pool"


def _variant(table: str, key: str, name: str, columns: tuple[str, ...], timing: PredictionTiming) -> ModelVariant:
    """オッズの分かる前日・当日は、今の予想と同じく、オッズから作った基準を出発点にして学ぶ。"""
    return ModelVariant(table, key, name, columns, uses_baseline=timing is not _THURSDAY, timing=timing)


def _pair(table: str, timing: PredictionTiming, columns: tuple[str, ...]) -> tuple[ModelVariant, ModelVariant]:
    """1つの時点の、今の予想（本番と同じ列）と、それに対戦レーティングを足した作り方。"""
    label = timing.label
    return (_variant(table, f"current-{timing.value}", f"今の予想（{label}）", columns, timing),
            _variant(table, f"h2h-{timing.value}", f"今の予想 ＋ 対戦レーティング（{label}）", columns + H2H_NAMES, timing))


@dataclass(frozen=True)
class TimingComparisonSpec:
    """1つの時点の比べ方（今の予想の作り方と、対戦レーティングを足した作り方）。"""

    timing: PredictionTiming
    current: ModelVariant
    rated: ModelVariant


#: 時点ごとの比べ方。木曜・前日は馬の力の材料の表、当日は今の材料に券種の支持を足した表で比べる（本番と同じ材料）。
H2H_COMPARISONS: tuple[TimingComparisonSpec, ...] = (
    TimingComparisonSpec(_THURSDAY, *_pair(ABILITY_TABLE, _THURSDAY, ABILITY_CATALOG.columns_for(_THURSDAY))),
    TimingComparisonSpec(_DAY_BEFORE, *_pair(ABILITY_TABLE, _DAY_BEFORE, ABILITY_CATALOG.columns_for(_DAY_BEFORE))),
    TimingComparisonSpec(_RACE_DAY, *_pair(POOL_TABLE, _RACE_DAY, POOL_CATALOG.columns_for(_RACE_DAY))),
)
#: 作り方の一覧（回す順）。
H2H_VARIANTS: tuple[ModelVariant, ...] = tuple(
    variant for spec in H2H_COMPARISONS for variant in (spec.current, spec.rated)
)


def variant_keyed(key: str) -> ModelVariant:
    """保存する名前から引く。知らなければ ``ValueError``。"""
    for variant in H2H_VARIANTS:
        if variant.key == key:
            return variant
    raise ValueError(f"知らない作り方です: {key}（{' / '.join(variant.key for variant in H2H_VARIANTS)}）")
