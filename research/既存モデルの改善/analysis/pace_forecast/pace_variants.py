"""展開の予想の確かめで比べる作り方（時点ごとに、今の予想と、展開の予想を足したもの）。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.form_aptitude_top3.feature import ABILITY_CATALOG, RACE_DAY_CATALOG
from yosou.shared.feature import PACE_FORECAST_FEATURES, PredictionTiming

from ..variants import ModelVariant

_THURSDAY, _DAY_BEFORE, _RACE_DAY = PredictionTiming.THURSDAY, PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY
#: 足す 20個の名前。
PACE_NAMES: tuple[str, ...] = tuple(feature.name for feature in PACE_FORECAST_FEATURES)


def _variant(table: str, key: str, name: str, columns: tuple[str, ...], timing: PredictionTiming) -> ModelVariant:
    """オッズの分かる前日・当日は、今の予想と同じく、オッズから作った基準を出発点にして学ぶ。"""
    return ModelVariant(table, key, name, columns, uses_baseline=timing is not _THURSDAY, timing=timing)


@dataclass(frozen=True)
class PaceComparisonSpec:
    """1つの時点の比べ方。``current`` は今の予想、``paced`` はそれに P を足した作り方。"""

    timing: PredictionTiming
    current: ModelVariant
    paced: ModelVariant


def _spec(timing: PredictionTiming, current_table: str, current_key: str, columns: tuple[str, ...]) -> PaceComparisonSpec:
    """今の予想の予測は、対戦レーティングの確かめで同じ区切り・同じ設定で学習したもの（保存した名前で引く）。"""
    label = timing.label
    current = _variant(current_table, current_key, f"今の予想（{label}）", columns, timing)
    paced = _variant(f"pace_{timing.value}", f"pace-{timing.value}", f"今の予想 ＋ 展開の予想（{label}）",
                     columns + PACE_NAMES, timing)
    return PaceComparisonSpec(timing, current, paced)


#: 時点ごとの比べ方。今の予想の列は本番と同じ（木曜・前日は ``ABILITY_CATALOG``、当日は ``RACE_DAY_CATALOG`` のその時点の列）。
#: 木曜・前日の今の予想は、対戦レーティングの確かめの「O を足した作り方」（採用されて本番になったもの）、当日は「今の予想」。
PACE_COMPARISONS: tuple[PaceComparisonSpec, ...] = (
    _spec(_THURSDAY, "h2h_ability", "h2h-thursday", ABILITY_CATALOG.columns_for(_THURSDAY)),
    _spec(_DAY_BEFORE, "h2h_ability", "h2h-day_before", ABILITY_CATALOG.columns_for(_DAY_BEFORE)),
    _spec(_RACE_DAY, "h2h_pool_ability", "current-race_day", RACE_DAY_CATALOG.columns_for(_RACE_DAY)),
)
#: 回す作り方（P を足したものだけ。今の予想は学習済み）。
PACE_VARIANTS: tuple[ModelVariant, ...] = tuple(spec.paced for spec in PACE_COMPARISONS)


def variant_keyed(key: str) -> ModelVariant:
    """保存する名前から引く。知らなければ ``ValueError``。"""
    for variant in PACE_VARIANTS:
        if variant.key == key:
            return variant
    raise ValueError(f"知らない作り方です: {key}（{' / '.join(variant.key for variant in PACE_VARIANTS)}）")
