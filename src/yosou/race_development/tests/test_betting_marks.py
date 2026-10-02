"""契約: 1着の確率の 1〜4位に ◎○▲△、5位以下で単勝の期待値が 1.0 以上の最大の馬に ☆、印の無い馬で先頭の確率が
最大の馬に 注 を付ける（設計書 06 の図4）。人気順の印は単勝オッズの低い順に ◎○▲△ だけを付ける。
"""

import numpy as np
import pandas as pd

from yosou.race_development.betting import MarkAssigner, PopularityMarkAssigner
from yosou.race_development.betting.column_names import HORSE_NO, LEADER_PROBABILITY, MARK, WIN_ODDS, WIN_PROBABILITY


def race(win_odds: list[float]) -> pd.DataFrame:
    """架空の7頭立て。1着の確率は馬番 3 → 1 → 5 → 2 → 7 → 4 → 6 の順に高い。先頭の確率は馬番 6 がいちばん高い。"""
    return pd.DataFrame({
        HORSE_NO: [1, 2, 3, 4, 5, 6, 7],
        WIN_PROBABILITY: [0.25, 0.12, 0.30, 0.05, 0.15, 0.03, 0.10],
        WIN_ODDS: win_odds,
        LEADER_PROBABILITY: [0.10, 0.05, 0.20, 0.15, 0.05, 0.40, 0.05],
    }, index=[10, 11, 12, 13, 14, 15, 16])


def marks_of(marked: pd.DataFrame) -> dict[int, str]:
    return {int(horse): mark for horse, mark in zip(marked[HORSE_NO], marked[MARK]) if mark}


def test_marks_follow_win_probability_value_and_leader():
    # 5位以下: 馬番 7（0.10 × 12.0 = 1.2）、4（0.05 × 30.0 = 1.5）、6（0.03 × 20.0 = 0.6）→ ☆ は 4。
    marked = MarkAssigner().assign(race([3.5, 8.0, 2.8, 30.0, 6.0, 20.0, 12.0]))
    assert marks_of(marked) == {3: "◎", 1: "○", 5: "▲", 2: "△", 4: "☆", 6: "注"}
    assert list(marked.index) == [10, 11, 12, 13, 14, 15, 16]


def test_no_star_when_the_best_value_is_below_one():
    marked = MarkAssigner().assign(race([3.5, 8.0, 2.8, 10.0, 6.0, 20.0, 9.0]))
    assert "☆" not in marks_of(marked).values()
    assert marks_of(marked)[6] == "注"


def test_no_star_without_win_odds_and_leader_skips_marked_horses():
    marked = MarkAssigner().assign(race([np.nan] * 7).drop(columns=WIN_ODDS))
    assert marks_of(marked) == {3: "◎", 1: "○", 5: "▲", 2: "△", 6: "注"}
    leader_is_top = race([np.nan] * 7).assign(**{LEADER_PROBABILITY: [0.1, 0.1, 0.5, 0.1, 0.1, 0.05, 0.05]})
    # 先頭の確率がいちばん高い馬番 3 は ◎ なので、印の無い馬（4・6・7）のうち最大の 4 に 注。
    assert marks_of(MarkAssigner().assign(leader_is_top)) == {3: "◎", 1: "○", 5: "▲", 2: "△", 4: "注"}


def test_small_field_gets_only_the_marks_it_can():
    small = race([3.5, 8.0, 2.8, 30.0, 6.0, 20.0, 12.0]).iloc[:3]
    assert marks_of(MarkAssigner().assign(small)) == {3: "◎", 1: "○", 2: "▲"}


def test_popularity_marks_follow_win_odds_only():
    marked = PopularityMarkAssigner().assign(race([3.5, 8.0, 2.8, 30.0, np.nan, 20.0, 12.0]))
    assert marks_of(marked) == {3: "◎", 1: "○", 2: "▲", 7: "△"}
