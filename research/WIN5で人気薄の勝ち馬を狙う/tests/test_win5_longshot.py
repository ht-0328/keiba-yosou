"""本線（今の買い目）に足す抑え（荒れる前提）の組み方と、勝ち馬を含めた数え方・採用の決まりを、架空の値で確かめる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.form_aptitude_win5_tickets.formation import Formation
from yosou.form_aptitude_win5_tickets.formation.combo_grid import ComboGrid
from yosou.form_aptitude_win5_tickets.leg import EDGE, MARKET, SHARE
from yosou.form_aptitude_win5_tickets.settlement import HIT, PAYOUT, RACE_DATE, STAKE, STRATEGY, Win5Outcome

from 印の成績.win5_strategy_summary import RECOVERY

from WIN5で人気薄の勝ち馬を狙う.analysis.win5_longshot.hedge_adoption_judge import ADOPTED, NOT_ADOPTED, HedgeAdoptionJudge
from WIN5で人気薄の勝ち馬を狙う.analysis.win5_longshot.hedge_candidate import BY_MARKET, NEW, HedgeCandidate
from WIN5で人気薄の勝ち馬を狙う.analysis.win5_longshot.hedge_day_bets import COVERED, KIND, LONGSHOT_LEGS, WIN_PAYOUT
from WIN5で人気薄の勝ち馬を狙う.analysis.win5_longshot.hedge_formation import HedgeFormation
from WIN5で人気薄の勝ち馬を狙う.analysis.win5_longshot.hedge_summary import BIG, HUGE, HedgeSummary
from WIN5で人気薄の勝ち馬を狙う.analysis.win5_longshot.longshot_coverage import LongshotCoverage
from WIN5で人気薄の勝ち馬を狙う.analysis.win5_longshot.upset_legs import UpsetLegs


def _leg(race_id: str, field: int, longshot_share: float) -> pd.DataFrame:
    """``field`` 頭のレース。馬番の小さい順に人気。10番人気以下のオッズから見た勝率の合計が ``longshot_share``。"""
    favorites, longshots = min(field, 9), max(field - 9, 0)
    market = [(1 - longshot_share) / favorites] * favorites + ([longshot_share / longshots] * longshots if longshots else [])
    return pd.DataFrame({
        "レースID": race_id, "馬番": range(1, field + 1), "単勝オッズ": [1.0 + n for n in range(field)],
        SHARE: market, MARKET: market, EDGE: 1.0,
    })


class _Value:
    """どの組も同じ値の架空の見積もり（見積もりの払戻の合計は点数が多いほど大きい）。"""

    def grid(self, legs, pool) -> ComboGrid:
        shape = [len(leg) for leg in legs]
        return ComboGrid(np.full(shape, 0.01), np.ones(shape))


def test_荒れそうなレースは人気薄の市場合計かハンデ戦で_合計の大きい順():
    legs = [_leg("a", 12, 0.05), _leg("b", 14, 0.15), _leg("c", 16, 0.12), _leg("d", 10, 0.01), _leg("e", 8, 0.0)]
    assert UpsetLegs(frozenset({"d"})).of(legs) == [1, 2, 3]


def test_抑えは荒れそうなレースを本線に無い人気薄に差し替え_残りの点数で組む():
    legs = [_leg("a", 16, 0.15), *(_leg(name, 12, 0.02) for name in "bcde")]
    main = Formation(((1, 2, 10), (1, 2), (1,), (1,), (1, 2)))
    candidate = HedgeCandidate("t", NEW, BY_MARKET, 1, 3, 20)
    choice = HedgeFormation(_Value()).best(legs, main, [0], candidate, None)
    assert choice.formation.legs[0] == (11, 12, 13)            # 本線の10番は除く
    assert choice.formation.points == 18                       # 3頭 × ほかのレースで 6点（20 ÷ 3 = 6）
    assert not any(main.contains(combo) for combo in choice.formation.combos())
    too_small = HedgeCandidate("t", NEW, BY_MARKET, 1, 3, 2)
    assert HedgeFormation(_Value()).best(legs, main, [0], too_small, None) is None


def test_人気薄の勝ち馬をどれかの買い目に含めたかを数える():
    legs = [_leg(name, 12, 0.1) for name in "abcde"]
    main = Formation(((1,), (1,), (1,), (1,), (1,)))
    hedge = Formation(((11,), (1,), (1,), (1, 12), (1,)))
    outcome = Win5Outcome("2024-01-01", (((11, 1, 1, 10, 1), 100000),), False, tuple(frozenset() for _ in range(5)), 1, 0)
    assert LongshotCoverage().of([main, hedge], legs, outcome) == (2, 1)


def test_成績は高配当の的中を数える():
    settled = pd.DataFrame({
        STRATEGY: ["s"] * 3, KIND: ["本線だけ"] * 3, RACE_DATE: ["2024-01-01", "2024-01-02", "2024-01-03"], STAKE: [5000] * 3,
        PAYOUT: [0, 2_000_000, 30_000_000], HIT: [False, True, True], WIN_PAYOUT: [0, 2_000_000, 30_000_000],
        LONGSHOT_LEGS: [1, 0, 2], COVERED: [0, 0, 1],
    })
    row = HedgeSummary().of(settled).iloc[0]
    assert row[BIG] == 2 and row[HUGE] == 1


def test_採用は両方の期間で高配当の的中が増え_回収率が8割以上のときだけ():
    def row(recovery: float, big: int) -> pd.Series:
        return pd.Series({RECOVERY: recovery, BIG: big})

    main = {"探索": row(1.0, 1), "確認": row(1.0, 0)}
    assert HedgeAdoptionJudge().judge({"探索": row(0.9, 3), "確認": row(0.85, 1)}, main)[0] == ADOPTED
    assert HedgeAdoptionJudge().judge({"探索": row(0.9, 3), "確認": row(0.7, 1)}, main)[0] == NOT_ADOPTED
    assert HedgeAdoptionJudge().judge({"探索": row(0.9, 3), "確認": row(0.95, 0)}, main)[0] == NOT_ADOPTED
