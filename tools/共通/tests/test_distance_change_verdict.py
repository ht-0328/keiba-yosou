"""距離短縮と距離延長のどちらが有利かの判定の契約: 人気の偏りを除いて比べ、検定の線を超えたときだけ有利と書く。"""

from __future__ import annotations

import pandas as pd

from 共通.distance_change_verdict import EVEN, FEW, DistanceChangeVerdict
from 共通.popularity_expectation import PopularityExpectation


def _runs(rows: list[tuple[str, int, int, int]]) -> pd.DataFrame:
    """（距離の変更, 人気, 着順, 頭数）を頭数ぶん並べた出走の表。"""
    records = []
    for change, popularity, finish, count in rows:
        records += [{"label_distance_change": change, "popularity": popularity,
                     "first": finish == 1, "second": finish == 2, "third": finish == 3}] * count
    return pd.DataFrame(records)


def test_the_gap_compares_with_horses_of_the_same_popularity():
    """1番人気の勝率が5割のコースで、1番人気の延長が全部勝てば、人気から見た勝率の差は +50pt。"""
    runs = _runs([("延長", 1, 1, 10), ("短縮", 1, 4, 10), ("同じ", 9, 4, 20)])
    expectation = PopularityExpectation(runs)
    gap = expectation.win_gap(runs[runs["label_distance_change"].eq("延長")])
    assert gap.runs == 10 and round(gap.gap, 3) == 0.5


def test_longer_is_better_only_when_the_gap_beats_the_test_line():
    """人気が同じ混ざり方で、延長だけがよく勝つ → 延長が有利（1%）。"""
    runs = _runs([("延長", 1, 1, 60), ("延長", 1, 4, 40), ("短縮", 1, 1, 30), ("短縮", 1, 4, 70)])
    assert DistanceChangeVerdict().win(runs).winner == "延長が有利（1%）"


def test_a_popularity_bias_alone_is_not_an_advantage():
    """延長が人気馬ばかりで勝率が高く見えても、同じ人気の中で差が無ければ「差なし」。"""
    runs = _runs([("延長", 1, 1, 40), ("延長", 1, 4, 40), ("短縮", 1, 1, 10), ("短縮", 1, 4, 10),
                  ("短縮", 8, 1, 2), ("短縮", 8, 4, 78), ("延長", 8, 1, 1), ("延長", 8, 4, 39)])
    verdict = DistanceChangeVerdict().win(runs)
    assert verdict.results["延長"].rate > verdict.results["短縮"].rate
    assert verdict.winner == EVEN


def test_the_longshot_view_counts_only_horses_below_the_line_and_needs_enough_runs():
    """穴馬の好走は 6番人気以下だけを数える。短縮・延長のどちらかが 30頭未満なら「標本が少ない」。"""
    runs = _runs([("延長", 1, 1, 100), ("短縮", 1, 2, 100), ("延長", 7, 3, 20), ("短縮", 7, 4, 50)])
    verdict = DistanceChangeVerdict().longshot(runs)
    assert verdict.results["延長"].gap.runs == 20 and verdict.winner == FEW


def test_a_stopped_horse_without_a_finish_counts_as_out_of_the_money():
    """競走中止・失格で着順が無く、1着かどうかが欠損値（pandas の boolean の NA）でも、外れとして数えて差を出す。"""
    runs = _runs([("延長", 1, 1, 60), ("延長", 1, 4, 40), ("短縮", 1, 1, 30), ("短縮", 1, 4, 70)])
    flags = runs[["first", "second", "third"]].astype("boolean")
    flags.iloc[-1] = pd.NA
    verdict = DistanceChangeVerdict().win(runs.assign(**flags))
    assert verdict.winner == "延長が有利（1%）" and pd.notna(verdict.results["短縮"].gap.gap)
