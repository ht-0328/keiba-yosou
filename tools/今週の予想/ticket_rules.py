"""印のルールの買い目（設計書「買うレースと買い目を決める」08 の 2）。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from yosou.shared.betting import TicketType

from 今週の予想.axis_ticket_rule import HORSE_AXIS, TOP_AXIS, AxisTicketRule

#: 1単位の金額（円）。08 の 2 の「1点の額」は単位で書いてあるので、合計を金額で出すときに使う。
UNIT_YEN = 1000
#: 1点の額の最小の単位（円）。回収率は 1点 100円で数える。
POINT_YEN = 100
#: 複勝を買う期待値の線と、1レースで買う点数の上限（08 の「採用している券種（複勝）」）。
PLACE_VALUE_LINE = 1.25
PLACE_MAX_POINTS = 3
PLACE_STAKE_UNITS = 1.0
#: 3連複・3連単の、軸から流す買い目の期待値の線（固定。検証期間では決めない。08 の 2）。
COMBO_VALUE_LINE = 1.0
#: 合計の行の組。元の買い目だけ（軸から流す3連複・3連単を足す前）と、それに軸から流す形を足した2パターン（◎軸・軸馬）。
#: 元の3連複・3連単（◎−○▲☆−○▲△☆ と ◎→○▲☆→○▲△☆）は必ず買う買い目なので、どの合計にも入る（利用者の決定）。
ORIGINAL = "元の買い目だけ"
TOTAL_GROUPS: tuple[str, ...] = (ORIGINAL, TOP_AXIS, HORSE_AXIS)
#: 複勝の買い方の名前（複勝は印ではなく期待値で選ぶので、``MarkTickets`` が別に作る）。
PLACE_LABEL = TicketType.PLACE.label


@dataclass(frozen=True)
class TicketRule:
    """印の位置で組む券種のルール。``positions`` は組の1頭目・2頭目・3頭目に置く印（券種の馬の数だけ）。

    ``△`` は3頭全部を指す。``label`` は表に出す買い方の名前（設計書 08 の 2 に無い券種は、そう分かるように書く）。
    ``totals`` は、この買い方を入れる合計の組（``TOTAL_GROUPS``）。
    """

    ticket_type: TicketType
    positions: tuple[tuple[str, ...], ...]
    stake_units: float
    label: str
    totals: tuple[str, ...] = TOTAL_GROUPS

    @property
    def value_line(self) -> float | None:
        """期待値では絞らない。"""
        return None

    def combos(self, by_mark: dict[str, list[int]], axes: dict[str, int]) -> list[tuple[int, ...]]:
        """印の組み合わせを全部作り、同じ馬が2回入る組と、順不同の券種で並びだけが違う組は1点にまとめる。
        印の付いた馬がいない位置（☆ の無いレースのワイドなど）は、その印を飛ばす。"""
        choices = [[horse for mark in position for horse in by_mark.get(mark, [])] for position in self.positions]
        if any(not choice for choice in choices):
            return []
        ordered = self.ticket_type.spec.is_ordered
        combos = {tuple(combo) if ordered else tuple(sorted(combo)) for combo in product(*choices) if len(set(combo)) == len(combo)}
        return sorted(combos)


#: 印で組む買い方のルール（08 の 2 の表の順）。馬単は、全券種をそろえるために ◎ を1着に固定した形で足したもので、設計書には無い。
#: 元の3連複・3連単（印の位置で組む）は必ず買う買い目で、どの合計にも入る。軸から流す3連複・3連単（軸の2パターン × 期待値で絞る・絞らない）は、
#: その軸のパターンの合計にだけ入る（期待値で絞らない3連単・絞った3連複は、比べるための行で、どの合計にも入らない）。
#: 複勝は印ではなく期待値で選ぶので、``MarkTickets`` が別に作る。
BET_RULES: tuple[TicketRule | AxisTicketRule, ...] = (
    TicketRule(TicketType.WIN, (("◎",),), 1.0, "単勝"),
    TicketRule(TicketType.WIDE, (("◎",), ("☆", "注")), 1.0, "ワイド"),
    TicketRule(TicketType.QUINELLA, (("◎",), ("○", "▲", "☆")), 0.5, "馬連"),
    TicketRule(TicketType.EXACTA, (("◎",), ("○", "▲", "☆")), 0.5, "馬単（設計書に無い）"),
    TicketRule(TicketType.TRIO, (("◎",), ("○", "▲", "☆"), ("○", "▲", "△", "☆")), 0.3, "3連複（◎−○▲☆−○▲△☆）"),
    TicketRule(TicketType.TRIFECTA, (("◎",), ("○", "▲", "☆"), ("○", "▲", "△", "☆")), 0.1, "3連単（◎→○▲☆→○▲△☆）"),
    AxisTicketRule(TicketType.TRIO, TOP_AXIS, None, 0.3, (TOP_AXIS,)),
    AxisTicketRule(TicketType.TRIO, TOP_AXIS, COMBO_VALUE_LINE, 0.3, ()),
    AxisTicketRule(TicketType.TRIO, HORSE_AXIS, None, 0.3, (HORSE_AXIS,)),
    AxisTicketRule(TicketType.TRIO, HORSE_AXIS, COMBO_VALUE_LINE, 0.3, ()),
    AxisTicketRule(TicketType.TRIFECTA, TOP_AXIS, None, 0.1, ()),
    AxisTicketRule(TicketType.TRIFECTA, TOP_AXIS, COMBO_VALUE_LINE, 0.1, (TOP_AXIS,)),
    AxisTicketRule(TicketType.TRIFECTA, HORSE_AXIS, None, 0.1, ()),
    AxisTicketRule(TicketType.TRIFECTA, HORSE_AXIS, COMBO_VALUE_LINE, 0.1, (HORSE_AXIS,)),
)
#: 表に並べる買い方の名前の順（複勝は単勝の次）。
RULE_LABELS: tuple[str, ...] = (BET_RULES[0].label, PLACE_LABEL, *(rule.label for rule in BET_RULES[1:]))
#: 合計の組 → その合計に入れる買い方の名前（複勝はどの合計にも入る）。
TOTAL_MEMBERS: dict[str, tuple[str, ...]] = {
    group: (BET_RULES[0].label, PLACE_LABEL, *(rule.label for rule in BET_RULES[1:] if group in rule.totals)) for group in TOTAL_GROUPS
}


def combo_text(horses: tuple[int, ...]) -> str:
    """馬番の並びを、払戻・オッズの表の組番（2桁ずつ並べた文字列）にする。例: (1, 5) → ``0105``。"""
    return "".join(f"{int(horse):02d}" for horse in horses)
