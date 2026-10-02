"""対戦レーティングの確かめで比べる作り方（時点ごとに、今の予想と、対戦レーティングを足したもの）。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.form_aptitude_top3.feature import ABILITY_CATALOG, RACE_DAY_CATALOG
from yosou.shared.feature import HEAD_TO_HEAD_FEATURES, PredictionTiming

from ..variants import ModelVariant

_THURSDAY, _DAY_BEFORE, _RACE_DAY = PredictionTiming.THURSDAY, PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY
#: 足す7個の名前。
H2H_NAMES: tuple[str, ...] = tuple(feature.name for feature in HEAD_TO_HEAD_FEATURES)
#: 対戦レーティングを足した表の名前（``BASE_TABLES`` の ``rated_name``）。
ABILITY_TABLE, RACE_DAY_TABLE = "h2h_ability", "h2h_pool_ability"


def _variant(table: str, key: str, name: str, columns: tuple[str, ...], timing: PredictionTiming) -> ModelVariant:
    """オッズの分かる前日・当日は、今の予想と同じく、オッズから作った基準を出発点にして学ぶ。"""
    return ModelVariant(table, key, name, columns, uses_baseline=timing is not _THURSDAY, timing=timing)


def _pair(table: str, timing: PredictionTiming, catalog_columns: tuple[str, ...]) -> tuple[ModelVariant, ModelVariant]:
    """1つの時点の、今の予想（対戦レーティングを足す前の列）と、それに対戦レーティングを足した作り方。

    木曜・前日の一覧（``ABILITY_CATALOG``）には、採用したあと対戦レーティングが入っているので、比べの「足す前」はそれを除く。
    """
    columns = tuple(column for column in catalog_columns if column not in H2H_NAMES)
    label = timing.label
    return (_variant(table, f"current-{timing.value}", f"今の予想（{label}）", columns, timing),
            _variant(table, f"h2h-{timing.value}", f"今の予想 ＋ 対戦レーティング（{label}）", columns + H2H_NAMES, timing))


@dataclass(frozen=True)
class TimingComparisonSpec:
    """1つの時点の比べ方（今の予想の作り方と、対戦レーティングを足した作り方）。"""

    timing: PredictionTiming
    current: ModelVariant
    rated: ModelVariant


#: 時点ごとの比べ方。木曜・前日は馬の力の材料の表、当日は今の材料に券種の支持と馬の力の材料を足した表で比べる（本番と同じ材料）。
H2H_COMPARISONS: tuple[TimingComparisonSpec, ...] = (
    TimingComparisonSpec(_THURSDAY, *_pair(ABILITY_TABLE, _THURSDAY, ABILITY_CATALOG.columns_for(_THURSDAY))),
    TimingComparisonSpec(_DAY_BEFORE, *_pair(ABILITY_TABLE, _DAY_BEFORE, ABILITY_CATALOG.columns_for(_DAY_BEFORE))),
    TimingComparisonSpec(_RACE_DAY, *_pair(RACE_DAY_TABLE, _RACE_DAY, RACE_DAY_CATALOG.columns_for(_RACE_DAY))),
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
