"""買い方の目録。ルール集（docs/rules/馬券の買い方/）の型と、予想モデルの出力から候補を選ぶ組み合わせ。

列の書き方: ``ColumnRule(選び方, 頭数)``。``keeps_previous=True`` は前の列の馬を含めた頭数、``same_as=0`` は1列目の写し。
広め（荒れるレース用）と少点数（自信のあるレース用）に分ける。基準の買い方（1番人気の単勝・複勝）は別の並び。
"""

from __future__ import annotations

from yosou.shared.betting import TicketType

from ..column_names import LONGSHOT_PROB
from .breadth import Breadth
from .column_rule import ColumnRule
from .picker import (
    CombinedPicker,
    ExpectedValuePicker,
    FormRankPicker,
    LongshotProbabilityPicker,
    LongshotRankPicker,
    MidPopularityByLongshotPicker,
    PopularityPicker,
)
from .ticket_plan import TicketPlan

#: 低配当目を削る線（ルール集 SRF-04・SRT-05）。
TRIO_ODDS_FLOOR = 100.0
TRIFECTA_ODDS_FLOOR = 200.0
#: 1倍台の本命を買わない線（TAN-11）。
MIN_WIN_ODDS = 2.0
#: 穴馬の区分（穴馬モデルの出力の値）。
MID_ZONE = "中穴"
#: 「条件に合う馬を全部」の列の頭数の上限（フルゲート）。
MAX_FIELD_SIZE = 18
#: 穴馬の単勝を買うオッズの帯（TAN-01 の 10.0〜19.9倍）。
LONGSHOT_WIN_ODDS_RANGE = (10.0, 19.9)
#: 確率の値で絞るしきい値（2回目の検証で足した買い方。docs/03-protocol.md）。
LONGSHOT_PLACE_THRESHOLDS: tuple[float, ...] = (0.25, 0.30, 0.35, 0.40)
LONGSHOT_WIN_THRESHOLDS: tuple[float, ...] = (0.25, 0.30, 0.35)
EXPECTED_VALUE_THRESHOLDS: tuple[float, ...] = (1.0, 1.1, 1.2)

_TOP = FormRankPicker()
_RUNNER_UP = FormRankPicker(skip=1)
_LONGSHOT = LongshotRankPicker()
_MID_LONGSHOT = LongshotRankPicker(zone=MID_ZONE)

#: 少点数（自信のあるレース用）。
NARROW_PLANS: tuple[TicketPlan, ...] = (
    TicketPlan("本命単勝", ("TAN-09", "TAN-11"), TicketType.WIN, (ColumnRule(_TOP, 1),), Breadth.NARROW,
               min_first_odds=MIN_WIN_ODDS),
    TicketPlan("本命複勝", ("FUK-03",), TicketType.PLACE, (ColumnRule(_TOP, 1),), Breadth.NARROW),
    TicketPlan("本命→穴馬3 ワイド", ("WID-01", "WID-02"), TicketType.WIDE,
               (ColumnRule(_TOP, 1), ColumnRule(_LONGSHOT, 3)), Breadth.NARROW, excludes_dangerous=True),
    TicketPlan("本命→穴馬3 馬連", ("UMR-03",), TicketType.QUINELLA,
               (ColumnRule(_TOP, 1), ColumnRule(_LONGSHOT, 3)), Breadth.NARROW),
    TicketPlan("3連複 1-2-4", ("SRF-P01",), TicketType.TRIO,
               (ColumnRule(_TOP, 1), ColumnRule(_RUNNER_UP, 2), ColumnRule(_LONGSHOT, 4, keeps_previous=True)),
               Breadth.NARROW, excludes_dangerous=True),
    TicketPlan("3連単 1-2-5", ("SRT-P08",), TicketType.TRIFECTA,
               (ColumnRule(_TOP, 1), ColumnRule(_RUNNER_UP, 2), ColumnRule(_LONGSHOT, 5, keeps_previous=True)),
               Breadth.NARROW, excludes_dangerous=True),
    TicketPlan("3連単 人気の和", ("SRT-P10",), TicketType.TRIFECTA,
               (ColumnRule(PopularityPicker(1, 1), 1), ColumnRule(PopularityPicker(5, 6), 2),
                ColumnRule(PopularityPicker(3, 6), 4, keeps_previous=True)),
               Breadth.NARROW, requires_top_favorite=True),
)

_TRIO_1_2_10 = (ColumnRule(_TOP, 1), ColumnRule(_MID_LONGSHOT, 2), ColumnRule(_LONGSHOT, 10, keeps_previous=True))
_TRIO_1_3_10 = (
    ColumnRule(_TOP, 1), ColumnRule(CombinedPicker(((_RUNNER_UP, 1), (_LONGSHOT, 2))), 3),
    ColumnRule(_LONGSHOT, 10, keeps_previous=True),
)
_TRIFECTA_WAITING = (
    ColumnRule(MidPopularityByLongshotPicker(3, 9), 4), ColumnRule(PopularityPicker(1, 2), 2),
    ColumnRule(MidPopularityByLongshotPicker(3, 9), 4, same_as=0),
)

#: 広め（荒れるレース用）。
WIDE_PLANS: tuple[TicketPlan, ...] = (
    TicketPlan("穴馬軸→1〜3番人気 ワイド", ("WID-11",), TicketType.WIDE,
               (ColumnRule(_LONGSHOT, 2), ColumnRule(PopularityPicker(1, 3), 3)), Breadth.WIDE, excludes_dangerous=True),
    TicketPlan("本命→穴馬5 馬連", ("UMR-03", "UMR-P01"), TicketType.QUINELLA,
               (ColumnRule(_TOP, 1), ColumnRule(_LONGSHOT, 5)), Breadth.WIDE),
    TicketPlan("3連複 1-2-10", ("SRF-P18",), TicketType.TRIO, _TRIO_1_2_10, Breadth.WIDE, excludes_dangerous=True),
    TicketPlan("3連複 1-3-10", ("SRF-P07",), TicketType.TRIO, _TRIO_1_3_10, Breadth.WIDE, excludes_dangerous=True),
    TicketPlan("3連単 待ちの型", ("SRT-P01",), TicketType.TRIFECTA, _TRIFECTA_WAITING, Breadth.WIDE, excludes_dangerous=True),
    TicketPlan("3連複 1-2-10（100倍未満カット）", ("SRF-P18", "SRF-04"), TicketType.TRIO, _TRIO_1_2_10, Breadth.WIDE,
               odds_floor=TRIO_ODDS_FLOOR, excludes_dangerous=True),
    TicketPlan("3連複 1-3-10（100倍未満カット）", ("SRF-P07", "SRF-04"), TicketType.TRIO, _TRIO_1_3_10, Breadth.WIDE,
               odds_floor=TRIO_ODDS_FLOOR, excludes_dangerous=True),
    TicketPlan("3連単 待ちの型（200倍未満カット）", ("SRT-P01", "SRT-05"), TicketType.TRIFECTA, _TRIFECTA_WAITING, Breadth.WIDE,
               odds_floor=TRIFECTA_ODDS_FLOOR, excludes_dangerous=True),
)

#: 確率の値で絞る買い方（2回目の検証で足した）。条件に合う馬を全部買うので点数はレースごとに変わる。
#: 本命の複勝の期待値だけ1点（少点数）、ほかは広め。
VALUE_NARROW_PLANS: tuple[TicketPlan, ...] = tuple(
    TicketPlan(f"本命 複勝 期待値≥{threshold:.1f}", ("FUK-03", "ALL-03"), TicketType.PLACE,
               (ColumnRule(ExpectedValuePicker(threshold, top_only=True), 1),), Breadth.NARROW)
    for threshold in EXPECTED_VALUE_THRESHOLDS
)
VALUE_WIDE_PLANS: tuple[TicketPlan, ...] = (
    *(TicketPlan(f"穴馬 確率≥{threshold:.2f} 複勝", ("FUK-01",), TicketType.PLACE,
                 (ColumnRule(LongshotProbabilityPicker(threshold), MAX_FIELD_SIZE),), Breadth.WIDE)
      for threshold in LONGSHOT_PLACE_THRESHOLDS),
    *(TicketPlan(f"穴馬 確率≥{threshold:.2f} 単勝（10〜19.9倍）", ("TAN-01",), TicketType.WIN,
                 (ColumnRule(LongshotProbabilityPicker(threshold, LONGSHOT_WIN_ODDS_RANGE), MAX_FIELD_SIZE),), Breadth.WIDE)
      for threshold in LONGSHOT_WIN_THRESHOLDS),
    *(TicketPlan(f"全頭 複勝 期待値≥{threshold:.1f}", ("ALL-03",), TicketType.PLACE,
                 (ColumnRule(ExpectedValuePicker(threshold), MAX_FIELD_SIZE),), Breadth.WIDE)
      for threshold in EXPECTED_VALUE_THRESHOLDS),
    *(TicketPlan(f"穴馬 複勝 期待値≥{threshold:.1f}", ("FUK-01", "ALL-03"), TicketType.PLACE,
                 (ColumnRule(ExpectedValuePicker(threshold, LONGSHOT_PROB), MAX_FIELD_SIZE),), Breadth.WIDE)
      for threshold in EXPECTED_VALUE_THRESHOLDS),
)

#: 基準（比べる相手）。モデルを使わず、全レースで買う。
BASELINE_PLANS: tuple[TicketPlan, ...] = (
    TicketPlan("1番人気 単勝", (), TicketType.WIN, (ColumnRule(PopularityPicker(1, 1), 1),), Breadth.NARROW),
    TicketPlan("1番人気 複勝", (), TicketType.PLACE, (ColumnRule(PopularityPicker(1, 1), 1),), Breadth.NARROW),
)

#: 探索で使う広め・少点数の買い方（順位で選ぶものと、値で絞るもの）。
ALL_NARROW_PLANS: tuple[TicketPlan, ...] = (*NARROW_PLANS, *VALUE_NARROW_PLANS)
ALL_WIDE_PLANS: tuple[TicketPlan, ...] = (*WIDE_PLANS, *VALUE_WIDE_PLANS)
#: 精算する買い方の全部（重複の無い名前）。
ALL_PLANS: tuple[TicketPlan, ...] = (*ALL_NARROW_PLANS, *ALL_WIDE_PLANS, *BASELINE_PLANS)
if len({plan.name for plan in ALL_PLANS}) != len(ALL_PLANS):
    raise ImportError("買い方の名前が重なっています")


def plan_named(name: str) -> TicketPlan:
    """名前から買い方を返す。知らなければ ``LookupError``。"""
    for plan in ALL_PLANS:
        if plan.name == name:
            return plan
    raise LookupError(f"知らない買い方です: {name}")
