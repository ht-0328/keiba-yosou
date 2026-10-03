"""1着のモデルの、時点ごとの作り方。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.form_aptitude_top3.feature import ABILITY_CATALOG, RACE_DAY_CATALOG
from yosou.shared.feature import FeatureCatalog, PredictionTiming

from ..head_to_head import base_table_rated
from ..pace_forecast import PACE_NAMES, pace_table_named
from ..variants import ModelVariant

_THURSDAY, _DAY_BEFORE, _RACE_DAY = PredictionTiming.THURSDAY, PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY


@dataclass(frozen=True)
class WinVariantSpec:
    """1つの時点の1着のモデルの作り方。``table`` は読む表の名前、``catalog`` はその表の特徴量の一覧、``variant`` は学ぶ列と時点。

    列は今の本番の3着以内のモデルと同じ（木曜は M・O・P、前日は M・O・J、当日は A〜L・N・M）。オッズの分かる前日・当日は、
    オッズから見た勝率の基準（``WinTargetData`` が付ける）を出発点にして学ぶ。
    """

    timing: PredictionTiming
    table: str
    catalog: FeatureCatalog
    variant: ModelVariant

    @property
    def key(self) -> str:
        return self.variant.key


def _spec(timing: PredictionTiming, table: str, catalog: FeatureCatalog, columns: tuple[str, ...]) -> WinVariantSpec:
    variant = ModelVariant(table, f"win-{timing.value}", f"1着のモデル（{timing.label}）", columns,
                           uses_baseline=timing is not _THURSDAY, timing=timing)
    return WinVariantSpec(timing, table, catalog, variant)


#: 時点ごとの作り方（回す順。前日が道具「印の成績」の既定なので先）。
WIN_VARIANTS: tuple[WinVariantSpec, ...] = (
    _spec(_DAY_BEFORE, "h2h_ability", base_table_rated("h2h_ability").rated_catalog, ABILITY_CATALOG.columns_for(_DAY_BEFORE)),
    _spec(_THURSDAY, "pace_thursday", pace_table_named("pace_thursday").catalog,
          ABILITY_CATALOG.columns_for(_THURSDAY) + PACE_NAMES),
    _spec(_RACE_DAY, "h2h_pool_ability", base_table_rated("h2h_pool_ability").rated_catalog, RACE_DAY_CATALOG.columns_for(_RACE_DAY)),
)


def spec_keyed(key: str) -> WinVariantSpec:
    """保存する名前（``win-<時点>``）から引く。知らなければ ``ValueError``。"""
    for spec in WIN_VARIANTS:
        if spec.key == key:
            return spec
    raise ValueError(f"知らない作り方です: {key}（{' / '.join(spec.key for spec in WIN_VARIANTS)}）")
