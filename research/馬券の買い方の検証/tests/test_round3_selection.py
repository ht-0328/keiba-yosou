"""契約: 枠A は線以上の複勝をレースごとに最大3点、枠B は見込みの利益の順に1日3レース（重賞は別枠）、線は直前の1年の回収率と点数で決まる。"""

import numpy as np
import pandas as pd
import pytest

from 馬券の買い方の検証.analysis.value_betting import CandidatePicker, DailyRaceCap, HorseSelection, ValidationLineChooser
from 馬券の買い方の検証.analysis.value_betting import columns as c
from 馬券の買い方の検証.analysis.value_betting.line_chooser import ELIGIBLE, LINE_COLUMN, POINTS, RATE


def _valued() -> pd.DataFrame:
    """1レース8頭。4〜8番が穴馬で、期待値 1.1〜1.5。6番は消。"""
    return pd.DataFrame({
        c.WINDOW: "w", c.PART: "テスト", c.RACE_ID: "r1", c.RACE_DATE: pd.Timestamp("2023-01-07"), c.HORSE_NO: range(1, 9),
        c.LONGSHOT_ZONE: [None, None, None, "中穴", "中穴", "中穴", "大穴", "大穴"],
        c.PLACE_VALUE: [np.nan, np.nan, np.nan, 1.1, 1.5, 1.4, 1.3, 1.2],
        c.EXCLUDED: [False, False, False, False, False, True, False, False],
        c.PLACE_PAYOUT: [0.0, 0.0, 0.0, 0.0, 450.0, 0.0, 0.0, 600.0],
    })


def test_horse_selection_rows():
    rows = _valued()
    assert HorseSelection.MID.rows_of(rows).sum() == 3 and HorseSelection.BIG.rows_of(rows).sum() == 2
    assert HorseSelection.BOTH.rows_of(rows).sum() == 5 and HorseSelection.parse("big") is HorseSelection.BIG
    with pytest.raises(ValueError):
        HorseSelection.parse("all")


def test_candidate_picker_keeps_top_three_by_value_above_the_line():
    tickets = CandidatePicker().pick(_valued(), 1.15)
    # 1.15 以上は 5・6・7・8番。6番は消。期待値の順に 5・7・8 の3点
    assert tickets[c.HORSE_NO].tolist() == [5, 7, 8]
    assert tickets[c.STAKE_YEN].tolist() == [100, 100, 100] and tickets[c.PAYOUT_YEN].tolist() == [450, 0, 600]
    assert (tickets[c.LINE] == 1.15).all()
    assert CandidatePicker().pick(_valued(), float("nan")).empty
    assert CandidatePicker(max_points=1).pick(_valued(), 1.0)[c.HORSE_NO].tolist() == [5]


def _tickets_for_day(day: str, race_profits: dict[str, float], window: str = "w") -> pd.DataFrame:
    rows = [{c.WINDOW: window, c.PART: "テスト", c.RACE_ID: race, c.RACE_DATE: pd.Timestamp(day), c.HORSE_NO: 9,
             c.PLACE_VALUE: 1.0 + profit / 100.0, c.STAKE_YEN: 100, c.PAYOUT_YEN: 0} for race, profit in race_profits.items()]
    return pd.DataFrame(rows)


def test_daily_race_cap_keeps_top_three_by_profit_and_graded_races_outside_the_cap():
    tickets = _tickets_for_day("2023-01-07", {"a": 50, "b": 40, "c": 30, "d": 20, "g": 5})
    races = pd.DataFrame({c.WINDOW: "w", c.PART: "テスト", c.RACE_ID: list("abcdg"), c.RACE_DATE: pd.Timestamp("2023-01-07"),
                          c.IS_GRADED: [False, False, False, False, True]})
    kept = DailyRaceCap(per_day=3).apply(tickets, races)
    assert sorted(kept[c.RACE_ID]) == ["a", "b", "c", "g"] and kept.set_index(c.RACE_ID).loc["a", c.RACE_PROFIT] == pytest.approx(50.0)
    # 同じ日でも、区切りが違えば別に数える
    both = pd.concat([tickets, _tickets_for_day("2023-01-07", {"x": 90, "y": 80}, window="v")], ignore_index=True)
    more = pd.concat([races, pd.DataFrame({c.WINDOW: "v", c.PART: "テスト", c.RACE_ID: ["x", "y"], c.RACE_DATE: pd.Timestamp("2023-01-07"),
                                            c.IS_GRADED: False})], ignore_index=True)
    assert len(DailyRaceCap(per_day=3).apply(both, more)) == 6
    assert DailyRaceCap().apply(tickets.iloc[0:0], races).empty


def _history(points_per_value: int) -> pd.DataFrame:
    """期待値 1.0・1.1・1.3 の穴馬が ``points_per_value`` 頭ずつ。1.1 以上だけ回収率が 100% を超える。"""
    values = np.repeat([1.0, 1.1, 1.3], points_per_value)
    payout = np.where(values >= 1.1, np.where(np.arange(len(values)) % 2 == 0, 240.0, 0.0), np.where(np.arange(len(values)) % 4 == 0, 200.0, 0.0))
    return pd.DataFrame({
        c.WINDOW: "w", c.PART: "検証", c.RACE_ID: [f"r{index}" for index in range(len(values))],
        c.RACE_DATE: pd.Timestamp("2022-07-02") + pd.to_timedelta(np.arange(len(values)) % 20, "D"), c.HORSE_NO: 9,
        c.PLACE_VALUE: values, c.EXCLUDED: False, c.PLACE_PAYOUT: payout,
    })


def test_line_chooser_picks_the_best_rate_among_lines_with_enough_points():
    chooser = ValidationLineChooser(CandidatePicker())
    table = chooser.table(_history(100), min_points=150)
    assert table[LINE_COLUMN].tolist() == [1.0, 1.05, 1.1, 1.15, 1.2, 1.25, 1.3, 1.4]
    by_line = table.set_index(LINE_COLUMN)
    # 1.0 は 300点だが回収率 100% 未満、1.1 は 200点で 120%、1.3 は 100点で足りない、1.4 は 0点
    assert by_line.loc[1.0, POINTS] == 300 and not by_line.loc[1.0, ELIGIBLE]
    assert by_line.loc[1.1, RATE] == pytest.approx(1.2) and by_line.loc[1.1, ELIGIBLE] and not by_line.loc[1.3, ELIGIBLE]
    # 1.05 と 1.1 は同じ 200点・120% なので、同点は低い線（点数の多いほう）を選ぶ
    assert chooser.choose(_history(100), min_points=150) == 1.05
    assert chooser.choose(_history(200), min_points=150) == 1.05
    assert np.isnan(chooser.choose(_history(10), min_points=150))
    # 1.3 の馬だけ回収率が高ければ、点数が足りるかぎり 1.3 の馬だけを買う線を選ぶ（1.15〜1.3 は同じ買い目なので、いちばん低い 1.15）
    richer = _history(100)
    richer.loc[richer[c.PLACE_VALUE] == 1.3, c.PLACE_PAYOUT] = np.where(np.arange(100) % 2 == 0, 300.0, 0.0)
    assert chooser.choose(richer, min_points=100) == 1.15 and chooser.choose(richer, min_points=150) == 1.05
