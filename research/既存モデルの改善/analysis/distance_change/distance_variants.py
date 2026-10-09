"""距離の変更の傾向を足したモデルの、時点と目的変数ごとの作り方と、比べる相手（今の本番のモデルの予測）。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.form_aptitude_top3.feature import ABILITY_CATALOG, RACE_DAY_CATALOG
from yosou.shared.dataset import TOP3, WIN
from yosou.shared.feature import FINISH_POWER_NAMES, PredictionTiming
from yosou.shared.feature.history import DISTANCE_CHANGE_NAMES

from ..pace_forecast import PACE_NAMES
from ..variants import ModelVariant
from .distance_tables import DISTANCE_TABLES, PAYBACK_RESEARCH, THIS_RESEARCH, DistanceTable

_THURSDAY, _DAY_BEFORE, _RACE_DAY = PredictionTiming.THURSDAY, PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY
_TABLES = {table.name: table for table in DISTANCE_TABLES}


@dataclass(frozen=True)
class DistanceVariantSpec:
    """1つの時点・1つの目的変数の作り方。``table`` は読む表、``variant`` は学ぶ列と時点、``label`` は目的変数（3着以内・1着）。

    比べる相手は今の本番のモデルを同じ7つの区切りで学んだ予測（``current_research`` の ``predictions/<current_table>/<current_key>.pkl``）。
    列は今の本番と同じ（木曜は M・O・P、前日は M・O・J、当日は A〜L・N・M、当日の1着はそれに Q）に、R の 7個を足したもの。
    オッズの分かる前日・当日は、オッズから作った基準（1着のモデルはオッズから見た勝率）を出発点にして学ぶ。
    """

    table: DistanceTable
    variant: ModelVariant
    label: str
    current_research: str
    current_table: str
    current_key: str

    @property
    def key(self) -> str:
        return self.variant.key

    @property
    def timing(self) -> PredictionTiming:
        return self.variant.timing


def _spec(table: str, timing: PredictionTiming, label: str, columns: tuple[str, ...], current_key: str,
          current_research: str = THIS_RESEARCH) -> DistanceVariantSpec:
    target = "3着以内" if label == TOP3 else "1着"
    prefix = "dist" if label == TOP3 else "dist-win"
    variant = ModelVariant(table, f"{prefix}-{timing.value}", f"{target}のモデル ＋ 距離の変更の傾向（{timing.label}）",
                           columns + DISTANCE_CHANGE_NAMES, uses_baseline=timing is not _THURSDAY, timing=timing)
    return DistanceVariantSpec(_TABLES[table], variant, label, current_research, _TABLES[table].base, current_key)


_THURSDAY_COLUMNS = ABILITY_CATALOG.columns_for(_THURSDAY) + PACE_NAMES
_DAY_BEFORE_COLUMNS = ABILITY_CATALOG.columns_for(_DAY_BEFORE)
_RACE_DAY_COLUMNS = RACE_DAY_CATALOG.columns_for(_RACE_DAY)

#: 時点ごと・目的変数ごとの作り方（回す順。前日が道具「印の成績」の既定なので先）。
DISTANCE_VARIANTS: tuple[DistanceVariantSpec, ...] = (
    _spec("dist_ability", _DAY_BEFORE, TOP3, _DAY_BEFORE_COLUMNS, "h2h-day_before"),
    _spec("dist_ability", _DAY_BEFORE, WIN, _DAY_BEFORE_COLUMNS, "win-day_before"),
    _spec("dist_thursday", _THURSDAY, TOP3, _THURSDAY_COLUMNS, "pace-thursday"),
    _spec("dist_thursday", _THURSDAY, WIN, _THURSDAY_COLUMNS, "win-thursday"),
    _spec("dist_pool_ability", _RACE_DAY, TOP3, _RACE_DAY_COLUMNS, "current-race_day"),
    _spec("dist_finish_pool_ability", _RACE_DAY, WIN, _RACE_DAY_COLUMNS + FINISH_POWER_NAMES, "finish-win-race_day",
          PAYBACK_RESEARCH),
)


def spec_keyed(key: str) -> DistanceVariantSpec:
    """保存する名前（``dist-<時点>``・``dist-win-<時点>``）から引く。知らなければ ``ValueError``。"""
    for spec in DISTANCE_VARIANTS:
        if spec.key == key:
            return spec
    raise ValueError(f"知らない作り方です: {key}（{' / '.join(spec.key for spec in DISTANCE_VARIANTS)}）")
