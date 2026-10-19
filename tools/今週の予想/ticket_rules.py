"""印のルールの買い目（設計書「買うレースと買い目を決める」08 の 2）。"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product

from yosou.shared.betting import BRACKET, TicketType

from 今週の予想.axis_ticket_rule import HORSE_AXIS, TOP_AXIS, AxisTicketRule
from 今週の予想.combo_value_rule import ALL_RACES, HIGH_RACES, HIGH_TOP_COMBOS, TOP_COMBOS, ComboValueRule
from 今週の予想.place_axis_ticket_rule import PlaceAxisTicketRule
from 今週の予想.race_condition import AGREED, FAVORITE_ODDS, FIELD_SIZE, HAS_DANGER, TOP3_SHARE, RaceCondition

#: 1単位の金額（円）。08 の 2 の「1点の額」は単位で書いてあるので、合計を金額で出すときに使う。
UNIT_YEN = 1000
#: 1点の額の最小の単位（円）。回収率は 1点 100円で数える。
POINT_YEN = 100
#: ☆ を買い目の相手に入れる複勝の期待値の線（07 の 5）。複勝の買い目の線は ``PLACE_BUY_LINE``。
PLACE_VALUE_LINE = 1.25
#: 複勝の買い方（08 の「採用している券種（複勝）」。研究「レースの種類ごとの買い方」の docs/04 の手順6）: 期待度「高」で ``PLACE_MIN_FIELD`` 頭以上の
#: レースで、複勝の期待値が ``PLACE_BUY_LINE`` 以上・複勝の最低オッズが ``PLACE_ODDS_CAP`` 倍以下の馬を、期待値の高い順に ``PLACE_MAX_POINTS`` 点まで。
PLACE_BUY_LINE = 1.1
PLACE_ODDS_CAP = 5.0
PLACE_MIN_FIELD = 16
PLACE_MAX_POINTS = 3
PLACE_STAKE_UNITS = 1.0
#: 単勝（期待値）の買い方（研究「レースの種類ごとの買い方」の docs/04 の手順6）: 1番人気の単勝オッズが ``WIN_FAVORITE_MIN`` 倍以上のレースで、
#: 単勝の期待値が ``WIN_VALUE_LINE`` 以上・単勝オッズが ``WIN_ODDS_CAP`` 倍以下の馬を、期待値の高い順に1点。◎ でなくてもよい。
WIN_VALUE_LABEL = f"{TicketType.WIN.label}（期待値）"
WIN_VALUE_LINE = 1.0
WIN_ODDS_CAP = 5.0
WIN_FAVORITE_MIN = 2.3
#: 3連複・3連単の、軸から流す買い目の期待値の線（固定。検証期間では決めない。08 の 2）。
COMBO_VALUE_LINE = 1.0
#: 合計の行の組。元の買い目だけ（軸から流す3連複・3連単を足す前）と、それに軸から流す形を足した2パターン（◎軸・軸馬）。
#: 元の3連複・3連単（◎−○▲☆−○▲△☆ と ◎→○▲☆→○▲△☆）は必ず買う買い目なので、どの合計にも入る（利用者の決定）。
ORIGINAL = "元の買い目だけ"
TOTAL_GROUPS: tuple[str, ...] = (ORIGINAL, TOP_AXIS, HORSE_AXIS)
#: 複勝の買い方の名前（複勝は印ではなく期待値で選ぶので、``MarkTickets`` が別に作る）。2モデル一致の行は、複勝の買い目のうち
#: LightGBM と CatBoost のそれぞれの確率で出した期待値も線以上の馬だけ（比べるための行。合計には入らない）。
PLACE_LABEL = TicketType.PLACE.label
PLACE_AGREE_LABEL = f"{PLACE_LABEL}（2モデル一致）"


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


#: 印で組む買い方のルール（08 の 2 の表の順）。馬単は ◎ を1着に固定した形（◎→○▲☆）。
#: 元の3連複・3連単（印の位置で組む）は必ず買う買い目で、どの合計にも入る。軸から流す3連複・3連単（軸の2パターン × 期待値で絞る・絞らない）は、
#: その軸のパターンの合計にだけ入る（期待値で絞らない3連単・絞った3連複は、比べるための行で、どの合計にも入らない）。
#: 期待値で絞る行には、2モデル一致（LightGBM と CatBoost のそれぞれの確率で出した組の期待値も線以上）で絞った行も添える
#: （研究「回収率100超の施策」の施策2。比べるための行で、どの合計にも入らない）。
#: 複勝は印ではなく期待値で選ぶので、``MarkTickets`` が別に作る。
BET_RULES: tuple[TicketRule | AxisTicketRule, ...] = (
    TicketRule(TicketType.WIN, (("◎",),), 1.0, "単勝"),
    TicketRule(TicketType.WIDE, (("◎",), ("☆", "注")), 1.0, "ワイド"),
    TicketRule(TicketType.QUINELLA, (("◎",), ("○", "▲", "☆")), 0.5, "馬連"),
    TicketRule(TicketType.EXACTA, (("◎",), ("○", "▲", "☆")), 0.5, "馬単"),
    TicketRule(TicketType.TRIO, (("◎",), ("○", "▲", "☆"), ("○", "▲", "△", "☆")), 0.3, "3連複（◎−○▲☆−○▲△☆）"),
    TicketRule(TicketType.TRIFECTA, (("◎",), ("○", "▲", "☆"), ("○", "▲", "△", "☆")), 0.1, "3連単（◎→○▲☆→○▲△☆）"),
    AxisTicketRule(TicketType.TRIO, TOP_AXIS, None, 0.3, (TOP_AXIS,)),
    AxisTicketRule(TicketType.TRIO, TOP_AXIS, COMBO_VALUE_LINE, 0.3, ()),
    AxisTicketRule(TicketType.TRIO, TOP_AXIS, COMBO_VALUE_LINE, 0.3, (), agreement=True),
    AxisTicketRule(TicketType.TRIO, HORSE_AXIS, None, 0.3, (HORSE_AXIS,)),
    AxisTicketRule(TicketType.TRIO, HORSE_AXIS, COMBO_VALUE_LINE, 0.3, ()),
    AxisTicketRule(TicketType.TRIO, HORSE_AXIS, COMBO_VALUE_LINE, 0.3, (), agreement=True),
    AxisTicketRule(TicketType.TRIFECTA, TOP_AXIS, None, 0.1, ()),
    AxisTicketRule(TicketType.TRIFECTA, TOP_AXIS, COMBO_VALUE_LINE, 0.1, (TOP_AXIS,)),
    AxisTicketRule(TicketType.TRIFECTA, TOP_AXIS, COMBO_VALUE_LINE, 0.1, (), agreement=True),
    AxisTicketRule(TicketType.TRIFECTA, HORSE_AXIS, None, 0.1, ()),
    AxisTicketRule(TicketType.TRIFECTA, HORSE_AXIS, COMBO_VALUE_LINE, 0.1, (HORSE_AXIS,)),
    AxisTicketRule(TicketType.TRIFECTA, HORSE_AXIS, COMBO_VALUE_LINE, 0.1, (), agreement=True),
)
#: 複勝の買い目の馬を軸にして ◎○▲ に流すワイド・馬連（研究「複勝以外の回収率100超」の手順4。1点の額はワイド・馬連と同じ）。
#: 複勝の買い目が決まってから組むので、``MarkTickets`` が複勝のあとに作る。
PLACE_AXIS_RULES: tuple[PlaceAxisTicketRule, ...] = (
    PlaceAxisTicketRule(TicketType.WIDE, 1.0),
    PlaceAxisTicketRule(TicketType.QUINELLA, 0.5),
)
#: 当日の期待度「高」のレースで実際に買う買い方（研究「複勝以外の回収率100超」の手順4 で採用の基準を満たした。08 の 2）。
#: 金額は印の単位ではなく、単勝・馬単用の財布から決める（``Wallet.point_yen``）。◎ の単勝は、単勝（期待値）（``WIN_VALUE_LABEL``）に替えた。
HIGH_RACE_LABELS: tuple[str, ...] = (TicketType.EXACTA.label,)
#: 組の期待値で組を選ぶ買い方。組の期待値は、市場とモデルを重みで合わせた組の確率（``ComboBlend``。重みはモデルの置き場所の ``combo_blend.json``）× オッズ。
#: 採用したものは当日の予想で実際に買う（08 の 2。金額は組の期待値用の財布から ``Wallet.point_yen``）。どれも合計には入らない。
#: 馬連・馬単・3連複・3連単は、研究「レースの種類ごとの買い方」の docs/04（手順6）で、2016年〜前の年だけで選んだ決まりが 2019〜2026年で
#: 回収率 100% 超え（90% の幅の下の端も 100% 超え）で、的中率も前の決まりより高かったもの。馬連・馬単は年ごとに選び直す決まりで、ここには
#: 2016〜2026年の全部で選んだものを置く。重みは4券種とも直前1年で推定し直す（``rolling``）。
#: ワイドは手順6 で基準を満たす買い方が見つからなかったので、docs/03 の絞り方（1番人気が 2.9倍以上）を足した前の決まりのまま。
COMBO_VALUE_RULES: tuple[ComboValueRule, ...] = (
    ComboValueRule(TicketType.QUINELLA, HIGH_TOP_COMBOS, 1.1, 30, adopted=True, max_points=3, rolling=True,
                   race_conditions=(RaceCondition(FAVORITE_ODDS, None, 1.8, "1番人気が 1.9倍未満"),)),
    ComboValueRule(TicketType.EXACTA, ALL_RACES, 1.0, 30, adopted=True, max_points=1, rolling=True,
                   race_conditions=(RaceCondition(AGREED, 1.0, None, "2モデル一致"),
                                    RaceCondition(TOP3_SHARE, 0.67522, None, "市場の勝率の上位3頭の和が 0.6752 以上"))),
    ComboValueRule(TicketType.WIDE, HIGH_RACES, 1.0, 300, adopted=True, max_points=3, rolling=True,
                   race_conditions=(RaceCondition(FAVORITE_ODDS, 2.9, None, "1番人気が 2.9倍以上"),)),
    ComboValueRule(TicketType.TRIO, TOP_COMBOS, 1.2, 1000, adopted=True, max_points=5, rolling=True,
                   race_conditions=(RaceCondition(HAS_DANGER, None, 0.0, "危険な人気馬がいない"),)),
    ComboValueRule(TicketType.TRIFECTA, HIGH_TOP_COMBOS, 1.0, 300, adopted=True, rolling=True,
                   race_conditions=(RaceCondition(FIELD_SIZE, 15, None, "15頭以上"),)),
)
#: 枠連の組の期待値の買い方（研究「レースの種類ごとの買い方」の docs/04 の手順6）: 期待度「高」で、市場の勝率の上位3頭の和が 0.6231 未満
#: （人気が上位3頭に集まっていない）レースで、枠連の組の期待値が 1.1 以上・300倍以下の枠の組を全部。組の確率は馬連の組を枠の組に足し合わせて作り
#: （``BracketValuePicker``）、重みはモデルの置き場所の ``bracket_blend.json``（直前1年で推定し直す）。
BRACKET_VALUE_RULE = ComboValueRule(BRACKET, HIGH_RACES, 1.1, 300, adopted=True, rolling=True,
                                    race_conditions=(RaceCondition(TOP3_SHARE, None, 0.62312, "市場の勝率の上位3頭の和が 0.6231 未満"),))
#: 実際に買う組の期待値の買い方の全部（枠連を含む。枠連は ``ComboValuePicker`` では作らないので ``COMBO_VALUE_RULES`` とは分ける）。
ALL_COMBO_VALUE_RULES: tuple[ComboValueRule, ...] = (*COMBO_VALUE_RULES, BRACKET_VALUE_RULE)
#: 当日の予想で実際に買う、組の期待値の買い方の名前。
COMBO_VALUE_LABELS: tuple[str, ...] = tuple(rule.label for rule in ALL_COMBO_VALUE_RULES if rule.adopted)
#: 表に並べる買い方の名前の順（複勝と、その2モデル一致の行と、複勝の馬を軸にした行は単勝の次。組の期待値の行は馬単の次）。
RULE_LABELS: tuple[str, ...] = (BET_RULES[0].label, WIN_VALUE_LABEL, PLACE_LABEL, PLACE_AGREE_LABEL, *(rule.label for rule in PLACE_AXIS_RULES),
                                *(rule.label for rule in BET_RULES[1:4]), *(rule.label for rule in ALL_COMBO_VALUE_RULES),
                                *(rule.label for rule in BET_RULES[4:]))
#: 合計の組 → その合計に入れる買い方の名前（複勝はどの合計にも入る）。
TOTAL_MEMBERS: dict[str, tuple[str, ...]] = {
    group: (BET_RULES[0].label, PLACE_LABEL, *(rule.label for rule in (*PLACE_AXIS_RULES, *BET_RULES[1:]) if group in rule.totals))
    for group in TOTAL_GROUPS
}


def combo_text(horses: tuple[int, ...]) -> str:
    """馬番の並びを、払戻・オッズの表の組番（2桁ずつ並べた文字列）にする。例: (1, 5) → ``0105``。"""
    return "".join(f"{int(horse):02d}" for horse in horses)
