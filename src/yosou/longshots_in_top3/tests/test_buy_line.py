"""「買い」の線の選び方・印の付け方・保存・回収率の幅（設計書 16 の 3）。DB を使わず、手で作った値で確かめる。"""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from yosou.shared.feature import PredictionTiming

from ..buy_line import BUY_LINE, CANDIDATES, IS_BUY, LINE, MIN_POINTS, PAYBACK, POINTS, BuyJudge, BuyLineChooser
from ..buy_line import DayBootstrapInterval
from ..dataset import LongshotZone
from ..repository import BuyLineRepository

MID, BIG = LongshotZone.MID.label, LongshotZone.BIG.label


def _bets(groups: list[tuple[float, int, int]]) -> tuple[pd.Series, pd.Series]:
    """（期待値, 点数, 1点あたりの払戻）の組から、期待値と払戻（100円あたり）の列を作る。"""
    values = [value for value, count, _ in groups for _ in range(count)]
    payouts = [payout for _, count, payout in groups for _ in range(count)]
    return pd.Series(values), pd.Series(payouts)


def test_chooser_picks_the_best_payback_among_lines_with_enough_points():
    # 期待値 1.12 の 250点は払戻 95円（回収率 0.95）、1.22 の 160点は 120円、1.35 の 50点は 300円。
    # 線 1.25 以上は 50点しか残らず選べない。線 1.15・1.2 は 1.22 と 1.35 の 210点で回収率がいちばん高い（約 1.63）。
    # 同じ回収率なら、点の多い低いほうの線を選ぶ
    value, payout = _bets([(1.12, 250, 95), (1.22, 160, 120), (1.35, 50, 300)])
    assert BuyLineChooser().choose(value, payout) == pytest.approx(1.15)


def test_chooser_gives_no_line_when_no_line_pays_back():
    value, payout = _bets([(1.1, 400, 80), (1.5, 400, 90)])
    assert math.isnan(BuyLineChooser().choose(value, payout))


def test_chooser_needs_the_minimum_points():
    value, payout = _bets([(1.5, MIN_POINTS - 1, 500)])
    assert math.isnan(BuyLineChooser().choose(value, payout))
    value, payout = _bets([(1.5, MIN_POINTS, 500)])
    # どの線でも同じ点が残り回収率も同じなので、いちばん低い線
    assert BuyLineChooser().choose(value, payout) == pytest.approx(1.0)


def test_chooser_lists_every_candidate_and_skips_missing_values():
    value, payout = _bets([(1.2, 10, 0), (1.2, 10, 250)])
    value = pd.concat([value, pd.Series([np.nan])], ignore_index=True)
    payout = pd.concat([payout, pd.Series([np.nan])], ignore_index=True)
    rates = BuyLineChooser().rates(value, payout)
    assert rates[LINE].tolist() == list(CANDIDATES)
    first = rates.iloc[0]
    assert first[POINTS] == 20 and first[PAYBACK] == pytest.approx(1.25)
    assert rates.iloc[-1][POINTS] == 0 and math.isnan(rates.iloc[-1][PAYBACK])


def test_judge_marks_the_horses_at_or_over_the_line_of_their_zone():
    value = pd.Series([1.3, 1.1, 1.3, np.nan], index=[10, 11, 12, 13])
    zone = pd.Series([MID, MID, BIG, MID], index=value.index)
    judged = BuyJudge({MID: 1.2}).judge(value, zone)
    # 大穴は線が無いので付けない。期待値の無い馬にも付けない
    assert judged[IS_BUY].tolist() == ["買い", "", "", ""]
    assert judged[BUY_LINE].tolist()[:2] == [1.2, 1.2] and math.isnan(judged[BUY_LINE].iloc[2])
    assert judged.index.equals(value.index)


def test_repository_round_trips_and_skips_missing_lines(tmp_path: Path):
    repository = BuyLineRepository(tmp_path)
    assert repository.load() == {}
    repository.save({PredictionTiming.DAY_BEFORE: {MID: 1.1, BIG: float("nan")}, PredictionTiming.RACE_DAY: {BIG: 1.25}})
    assert repository.load() == {PredictionTiming.DAY_BEFORE: {MID: 1.1}, PredictionTiming.RACE_DAY: {BIG: 1.25}}


def test_bootstrap_interval_contains_the_payback_and_counts_days():
    days = pd.Series(pd.to_datetime(["2026-01-04"] * 5 + ["2026-01-05"] * 5 + ["2026-01-11"] * 5))
    payout = pd.Series([0, 0, 0, 0, 500] * 3)
    low, high = DayBootstrapInterval().of(days, payout)
    # どの開催日も回収率 1.0 なので、幅も 1.0 ちょうど
    assert low == pytest.approx(1.0) and high == pytest.approx(1.0)
    uneven = pd.Series([0] * 10 + [0, 0, 0, 0, 1500])
    low, high = DayBootstrapInterval().of(days, uneven)
    assert low < 1.0 < high
    assert all(math.isnan(bound) for bound in DayBootstrapInterval().of(pd.Series([], dtype=object), pd.Series([])))
