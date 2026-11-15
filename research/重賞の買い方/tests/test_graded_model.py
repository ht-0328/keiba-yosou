"""5回目（重賞に特化した予想の印で全部の重賞を買う）の部品。架空の値だけを使う。"""

from __future__ import annotations

import pandas as pd

from 重賞の買い方.analysis.graded_model import (
    POINTS,
    RETURN,
    SHAPE,
    SHAPES,
    TICKETS,
    RaceHorses,
    ShapeChooser,
    ShapeCounter,
    TicketShape,
    TopValueRule,
)
from 重賞の買い方.analysis.graded_model.combo_universe import COMBO, TICKET, VALUE
from 重賞の買い方.analysis.graded_model.ticket_shape import BRACKET, PLACE, TRIFECTA, TRIO, WIN, combo_key

#: 架空の1レース（馬番 1〜8。印 ◎=3 ○=1 ▲=5 △=2,7,8 ☆=6（期待値 1.3）注=なし）。
_MARKS = {3: "◎", 1: "○", 5: "▲", 2: "△", 7: "△", 8: "△", 6: "☆", 4: "－"}
_PROBABILITY = {1: 0.6, 2: 0.4, 3: 0.55, 4: 0.2, 5: 0.5, 6: 0.15, 7: 0.3, 8: 0.25}


def _race(race_id: str = "r1", day: str = "2021-05-02") -> pd.DataFrame:
    return pd.DataFrame({
        "race_id": race_id, "race_date": pd.Timestamp(day), "horse_no": list(_MARKS), "mark": list(_MARKS.values()),
        "probability": [_PROBABILITY[horse] for horse in _MARKS], "place_value": [1.3 if horse == 6 else 0.9 for horse in _MARKS],
        "frame_no": [(horse + 1) // 2 for horse in _MARKS],
    })


def test_race_horses_reads_marks_and_partner_pools():
    horses = RaceHorses.of(_race())
    assert (horses.top, horses.second, horses.third, horses.triangles, horses.star) == (3, 1, 5, (2, 7, 8), 6)
    assert horses.partners("○▲☆", (3,)) == (1, 5, 6)
    assert horses.partners("印", (3,)) == (1, 5, 2, 7, 8, 6)
    # 無印に流す: 消を除いた全頭（3着以内の確率の順）から軸を除く
    assert horses.partners("無印に流す", (3,)) == (1, 5, 2, 7, 8, 4, 6)
    assert horses.unmarked_top == (4,)


def test_shapes_build_the_expected_combos():
    horses = RaceHorses.of(_race())
    assert TicketShape(WIN, "◎").combos(horses) == [(3,)]
    assert TicketShape(PLACE, "◎・○", star=True).combos(horses) == [(3,), (1,), (6,)]
    # 枠連: ◎ の枠（2）と、○▲ の枠（1・3）
    assert TicketShape(BRACKET, "◎の枠−相手の枠", "○▲").combos(horses) == [(1, 2), (2, 3)]
    # 3連複の4頭の組: ◎○▲ と △ の1頭目（2）の4頭から3頭
    assert set(TicketShape(TRIO, "◎○▲△の4頭の組").combos(horses)) == {(1, 3, 5), (2, 3, 5), (1, 2, 3), (1, 2, 5)}
    # 3連単 ○▲ → 消以外 → ◎: 2頭 × 残りの6頭
    head = TicketShape(TRIFECTA, "○▲→消以外→◎").combos(horses)
    assert len(head) == 12 and all(combo[2] == 3 and combo[0] in (1, 5) for combo in head)
    middle = TicketShape(TRIFECTA, "相手→◎→相手", "○▲☆").combos(horses)
    assert len(middle) == 6 and all(combo[1] == 3 for combo in middle)
    assert combo_key(BRACKET, (3, 6)) == "36" and combo_key(TRIFECTA, (1, 5, 3)) == "010503"


def test_every_shape_has_a_ticket_and_win_is_only_the_top_pick():
    assert {shape.ticket for shape in SHAPES} == set(TICKETS)
    assert [shape for shape in SHAPES if shape.ticket == WIN] == [TicketShape(WIN, "◎")]


def _universe(race_id: str, day: str, ticket: str, rows: list[tuple[tuple[int, ...], float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame([{"race_id": race_id, "race_date": pd.Timestamp(day), TICKET: ticket, COMBO: combo_key(ticket, combo),
                          "odds": odds, "payout": payout, VALUE: value} for combo, odds, payout, value in rows])


def test_counter_applies_lines_caps_and_torigami():
    race = _race()
    shape = TicketShape(PLACE, "◎・○・▲", line=1.0)
    universe = _universe("r1", "2021-05-02", PLACE, [((3,), 1.5, 150.0, 1.2), ((1,), 1.1, 0.0, 1.05), ((5,), 4.0, 0.0, 0.8)])
    counts = ShapeCounter().count(race, universe, [shape])
    # ▲ は期待値の線で外れ、○（1.1倍）は2点のうちトリガミで外れる → ◎ の1点だけ
    assert counts[POINTS].tolist() == [1] and counts[RETURN].tolist() == [150.0]
    capped = ShapeCounter().count(race, universe, [TicketShape(PLACE, "◎・○・▲", cap=2.0)])
    # 上限 2倍で ▲ が外れ、残る2点の ○（1.1倍）はトリガミ
    assert capped[POINTS].tolist() == [1]


def _counts() -> pd.DataFrame:
    """2つの形（0: 単勝、1: 複勝）× 4レース。"""
    rows = []
    for index, day in enumerate(("2021-01-01", "2021-01-02", "2021-01-03", "2021-01-04")):
        rows.append({"race_id": f"r{index}", "race_date": pd.Timestamp(day), SHAPE: 0, POINTS: 1, RETURN: 300.0 if index == 0 else 0.0,
                     "mean_value": 1.2})
        rows.append({"race_id": f"r{index}", "race_date": pd.Timestamp(day), SHAPE: 1, POINTS: 2, RETURN: 220.0,
                     "mean_value": 0.9 + index * 0.1})
    return pd.DataFrame(rows)


def test_chooser_and_rule_pick_shapes_and_tickets():
    shapes = [TicketShape(WIN, "◎"), TicketShape(PLACE, "◎・○")]
    summary = ShapeChooser().summary(_counts(), shapes)
    assert summary["hits"].tolist() == [1, 4] and summary["rate"].round(3).tolist() == [0.75, 1.1]
    chosen = ShapeChooser().choose(summary)
    assert chosen == {WIN: 0, PLACE: 1}
    # 上位1券種: 期待値の高いほう（r0〜r2 は単勝、r3 は複勝 1.2 と単勝 1.2 が並ぶ）
    picked = TopValueRule(1).pick(_counts(), chosen)
    assert len(picked) == 4 and picked.groupby("race_id").size().eq(1).all()
    # 線 1.0 を付けても、2券種は残す
    assert len(TopValueRule(2, 1.0).pick(_counts(), chosen)) == 8


def test_value_rank_keeps_the_top_combos_and_drops_torigami():
    from 重賞の買い方.analysis.graded_model.value_rank_counter import ValueRankCounter, ValueRankShape

    combos = pd.DataFrame({"race_id": [1, 1, 1, 1], "odds": [1.8, 2.5, 30.0, 400.0], "payout": [0.0, 250.0, 0.0, 0.0],
                           "probability": [0.5, 0.4, 0.05, 0.001], "value": [0.9, 1.0, 1.5, 0.4]})
    counter = ValueRankCounter(folder=".")
    # 上位3点（期待値 1.5・1.0・0.9）のうち、1.8倍は3点ではトリガミ、残り2点の 2.5倍は2点より多く戻るので残る
    top3 = counter._one(combos, ValueRankShape("馬連", 3), 7)
    assert top3[POINTS].tolist() == [2] and top3[RETURN].tolist() == [250.0] and top3[SHAPE].tolist() == [7]
    # 線 1.2: 1.5 の1点だけ。線に届く組が無くても1点は買う
    assert counter._one(combos, ValueRankShape("馬連", 3, line=1.2), 0)[POINTS].tolist() == [1]
    assert counter._one(combos, ValueRankShape("馬連", 3, line=5.0), 0)[POINTS].tolist() == [1]
    # 上限 10倍・確率 0.1 以上: 1.8倍と 2.5倍の2組 → 1.8倍は2点でトリガミ
    assert counter._one(combos, ValueRankShape("馬連", 5, cap=10.0, floor=0.1), 0)[POINTS].tolist() == [1]
