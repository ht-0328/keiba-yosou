"""この予想の材料（特徴量）の一覧。券種ごとに1つ。"""

from __future__ import annotations

from yosou.shared.betting import TicketType
from yosou.shared.feature import Feature, FeatureCatalog, FeatureKind, PredictionTiming

from . import combo_summary_features as summary
from . import cross_market_features as cross
from . import harville_features as harville
from . import own_market_features as own
from . import race_features as race
from . import region_features as region
from .position_horse_features import PositionHorseFeatures

#: 扱う券種（組の表を作る順）。
TICKET_TYPES: tuple[TicketType, ...] = (
    TicketType.WIDE, TicketType.QUINELLA, TicketType.EXACTA, TicketType.TRIO, TicketType.TRIFECTA,
)
#: レースの材料のうち、頭数のほか。
_RACE_NAMES_AFTER_FIELD = tuple(name for name in race.RACE_MATERIALS if name != race.FIELD)


def _features(group: str, names: tuple[str, ...]) -> tuple[Feature, ...]:
    """まとまり ``group`` の数値の材料。どれも券種のオッズの板が要るので、分かるのは当日（締め切り前）から。"""
    return tuple(Feature(name, group, FeatureKind.NUMERIC, PredictionTiming.RACE_DAY) for name in names)


def feature_catalog(ticket_type: TicketType) -> FeatureCatalog:
    """1つの券種の材料の一覧。まとまりは A その券種の市場・B ほかの券種の市場・C Harville・D 組の位置ごとの馬・E 組のまとめ・F レース。

    並びは、回収率を確かめたときの並び（頭数だけ A の直後）を保つ。列の並びが変わると、木を作るときの列の選ばれ方が変わるため。
    カテゴリの材料は無い（全部数値）。数は ワイド 80・馬連 81・馬単 81・3連複 99・3連単 102。
    """
    position_names = PositionHorseFeatures().names(ticket_type.spec.horse_count)
    return FeatureCatalog(
        _features("A", own.NAMES) + _features("F", (race.FIELD,)) + _features("B", cross.NAMES[ticket_type])
        + _features("C", harville.NAMES) + _features("D", position_names) + _features("E", summary.NAMES)
        + _features("F", _RACE_NAMES_AFTER_FIELD + region.NAMES + (race.FAVORITE_OUT,))
    )


#: 券種ごとの材料の一覧。
CATALOGS: dict[TicketType, FeatureCatalog] = {ticket_type: feature_catalog(ticket_type) for ticket_type in TICKET_TYPES}
