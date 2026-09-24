"""買い方（馬の役割・券種ごとの買い目・賭け金とトリガミ・券種で期待値を積む・勝負するレース・控えめな見積もり）。合成データだけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.dataset import HORSE_NO, RACE_DATE, RACE_ID
from yosou.shared.dataset.column_names import POPULARITY

from 馬券の買い方の検証.analysis.ticket import TicketType

from 既存モデルの改善.analysis.betting import (
    BettingPlan, BettingPlanChooser, ProbabilityCalibrator, RaceCandidatePricer, RaceSelector, StakeAllocator, TicketSetBuilder,
)
from 既存モデルの改善.analysis.betting.candidate_columns import (
    COMBO, GROUP, ODDS, PRICE, PROBABILITY, RACE, RETURN, SET_ODDS, SET_STAKE, SET_VALUE, STAKE, TICKET, VALUE,
)
from 既存モデルの改善.analysis.betting.payout_table import PAYOUT
from 既存モデルの改善.analysis.betting.race_columns import FAVORITE_EXCLUDED, GRADED, SCORE
from 既存モデルの改善.analysis.combined.horse_columns import FORM_PROBABILITY, WIN_PROBABILITY
from 既存モデルの改善.analysis.horse_roles import AXIS, DANGER, EXCLUDED, HONMEI, POPULAR, WIN_VALUE, RoleAssigner
from 既存モデルの改善.analysis.market import CombinationTable
from 既存モデルの改善.analysis.race_probability import FinishOrderProbability
from 既存モデルの改善.analysis.scores import ConservativeRate
from 既存モデルの改善.analysis.ticket_combos import TICKET_SPECS, PairCombos, RaceHorses, TrioCombos, TrifectaCombos

_SPECS = {spec.ticket: spec for spec in TICKET_SPECS}


def _horses() -> pd.DataFrame:
    """1レース8頭。1番は危険な1番人気、2〜3番は人気、4〜8番は穴。"""
    return pd.DataFrame({
        RACE_ID: "R1", HORSE_NO: np.arange(1, 9), POPULARITY: np.arange(1, 9),
        FORM_PROBABILITY: [0.80, 0.70, 0.55, 0.40, 0.30, 0.20, 0.10, 0.05],
        DANGER: [0.20, 0.01, 0.02] + [np.nan] * 5,
        WIN_VALUE: [0.8, 0.9, 1.4, 1.1, 1.0, 0.9, 0.7, 0.5],
        POPULAR: [True, True, True, False, False, False, False, False],
    })


def test_role_assigner_excludes_only_the_really_dangerous_favorite():
    roles = RoleAssigner(exclude_line=0.15, second_axis_line=0.5).assign(_horses()).set_index(HORSE_NO)
    assert roles[EXCLUDED].tolist() == [True] + [False] * 7
    # 1番を消して、3着以内の確率が高い 2番が軸、3番も 0.5 以上なので2頭軸。単勝の期待値がいちばん高い 3番が◎
    assert roles.loc[2, AXIS] == 1 and roles.loc[3, AXIS] == 2 and roles[HONMEI].idxmax() == 3
    kept = RoleAssigner(exclude_line=0.30, second_axis_line=0.9).assign(_horses()).set_index(HORSE_NO)
    assert not kept[EXCLUDED].any() and kept.loc[1, AXIS] == 1 and (kept[AXIS] == 2).sum() == 0


def _race_horses() -> RaceHorses:
    return RaceHorses(runners=(2, 3, 4, 5, 6), popular=(2, 3), holes=(4, 5, 6), axes=(2,), honmei=3)


def test_pairs_are_popular_plus_hole_and_hole_pairs_only_when_upset():
    calm = PairCombos(ordered=False).of(_race_horses(), upset=False)
    assert {group for _, group in calm} == {"人気-穴", "人気-人気"} and len(calm) == 2 * 3 + 1
    upset = PairCombos(ordered=False).of(_race_horses(), upset=True)
    assert sum(group == "穴-穴" for _, group in upset) == 3
    assert len(PairCombos(ordered=True).of(_race_horses(), upset=False)) == 2 * len(calm)


def test_trio_uses_the_axis_and_trifecta_puts_honmei_or_axis_first():
    one_axis = TrioCombos().of(_race_horses(), upset=False)
    assert all(2 in combo for combo, _ in one_axis) and len(one_axis) == 6
    two_axes = TrioCombos().of(RaceHorses((2, 3, 4, 5), (2, 3), (4, 5), (2, 3), 3), upset=False)
    assert sorted(combo for combo, _ in two_axes) == [(2, 3, 4), (2, 3, 5)]
    firsts = {combo[0] for combo, _ in TrifectaCombos().of(_race_horses(), upset=False)}
    assert firsts == {2, 3}


def test_stake_allocator_equalizes_payouts_and_drops_torigami():
    stakes = StakeAllocator().allocate(_SPECS[TicketType.QUINELLA], np.array([4.0, 12.0]))
    # 予算 1,000円を払戻均等に: 750円と 250円 → 700円と 200円。どちらが当たっても合計 900円より多く戻る
    assert stakes.tolist() == [700.0, 200.0]
    # 3連単は 100円ずつ。3点で 300円なので、2倍（200円）の買い目はトリガミとして外す
    trifecta = StakeAllocator().allocate(_SPECS[TicketType.TRIFECTA], np.array([2.0, 50.0, 80.0]))
    assert trifecta.tolist() == [0.0, 100.0, 100.0]


def test_pricer_and_set_builder_cut_low_values_and_set_the_set_values():
    horses = pd.DataFrame({
        RACE_ID: "R1", HORSE_NO: [1, 2, 3], WIN_PROBABILITY: [0.5, 0.3, 0.2], EXCLUDED: False,
        AXIS: [1, 0, 0], HONMEI: [False, True, False], POPULAR: [True, True, False],
    })
    win = pd.DataFrame({"race_id": "R1", "h1": [1, 2, 3], "odds": [1.8, 4.0, 6.0], "odds_high": [1.8, 4.0, 6.0]})
    tables = {TicketType.WIN: CombinationTable(win, 1)}
    candidates = RaceCandidatePricer(tables, {}, FinishOrderProbability(), [_SPECS[TicketType.WIN]]).build(horses, set())
    built = TicketSetBuilder([_SPECS[TicketType.WIN]]).build(candidates.assign(**{PAYOUT: 0.0}), set())
    # 1番は 0.5 × 1.8 = 0.9 で切る。2番 1.2・3番 1.2 を買い、払戻均等で賭ける
    assert sorted(built[COMBO]) == ["02", "03"] and (built[VALUE] >= 1.0).all()
    assert built[SET_ODDS].iloc[0] > 1.0 and built[SET_STAKE].iloc[0] == built[STAKE].sum()
    assert built[SET_VALUE].iloc[0] == pytest.approx(1.2)


def _tickets() -> pd.DataFrame:
    """2レース。a は3連単（期待値 1.4・3,000円）と馬連（1.2・1,000円）と単勝（0.95）、b は馬連（1.1）だけ。"""
    return pd.DataFrame({
        RACE: ["a", "a", "a", "b"], TICKET: ["3連単", "馬連", "単勝", "馬連"], COMBO: ["010203", "0102", "01", "0304"],
        GROUP: "", SET_VALUE: [1.4, 1.2, 0.95, 1.1], SET_STAKE: [3000.0, 1000.0, 1500.0, 1000.0],
        STAKE: [3000.0, 1000.0, 1500.0, 1000.0], RETURN: [0.0, 2400.0, 0.0, 0.0],
    })


def _races() -> pd.DataFrame:
    return pd.DataFrame({RACE: ["a", "b"], RACE_DATE: pd.to_datetime(["2025-01-05"] * 2), GRADED: [False, True],
                         FAVORITE_EXCLUDED: [False, False]})


def test_betting_plan_stacks_the_best_tickets_within_the_budget():
    plan = BettingPlan(None, {"3連単": 1.0, "馬連": 1.0, "単勝": 1.0}, frozenset({"3連単", "馬連", "単勝"}))
    bought = plan.apply(_tickets(), _races())
    # a は単勝（0.95）を線で落とし、3連単と馬連で 4,000円。b は馬連
    assert sorted(zip(bought[RACE], bought[TICKET])) == [("a", "3連単"), ("a", "馬連"), ("b", "馬連")]
    only_one = BettingPlan(1, {"3連単": 1.0, "馬連": 1.0}, frozenset({"3連単", "馬連"})).apply(_tickets(), _races())
    # 1開催日1レースなら a だけ。ただし b は重賞なので別枠で入る
    assert set(only_one[RACE]) == {"a", "b"}


def test_race_selector_puts_races_with_excluded_favorites_first():
    races = pd.DataFrame({RACE: ["a", "b", "c"], RACE_DATE: pd.to_datetime(["2025-01-05"] * 3),
                          FAVORITE_EXCLUDED: [False, True, False], SCORE: [1.5, 1.1, 1.3], GRADED: False})
    assert races[RaceSelector(per_day=1).select(races)][RACE].tolist() == ["b"]


def test_conservative_rate_is_lower_when_few_hits():
    days = pd.Series(np.arange(100) % 20)
    stake = pd.Series(100.0, index=days.index)
    steady = pd.Series(np.where(np.arange(100) % 2 == 0, 240.0, 0.0))
    lucky = pd.Series(np.where(np.arange(100) == 0, 12000.0, 0.0))
    rate = ConservativeRate()
    assert rate.of(days, stake, lucky) < rate.of(days, stake, steady) < 1.2


def test_plan_chooser_needs_enough_hits():
    races = pd.DataFrame({RACE: [f"r{index}" for index in range(60)],
                          RACE_DATE: pd.to_datetime("2025-01-01") + pd.to_timedelta(np.arange(60) // 2, "D"),
                          GRADED: False, FAVORITE_EXCLUDED: False})
    tickets = pd.DataFrame({RACE: races[RACE], TICKET: "単勝", COMBO: "01", GROUP: "1頭", SET_VALUE: 1.2,
                            SET_STAKE: 1000.0, STAKE: 1000.0, RETURN: np.where(np.arange(60) % 2 == 0, 2500.0, 0.0)})
    plan, choices = BettingPlanChooser(min_hits=30).choose(tickets, races)
    win = next(choice for choice in choices if choice.ticket == "単勝")
    assert win.hits == 30 and win.adopted and "単勝" in plan.adopted
    _, strict = BettingPlanChooser(min_hits=31).choose(tickets, races)
    assert np.isnan(next(choice for choice in strict if choice.ticket == "単勝").line)


def test_probability_calibrator_shrinks_overestimated_bands():
    # 3連単の 1000倍以上で、予想の合計 30回（0.01 × 3000点）に対し、実際は 10回
    candidates = pd.DataFrame({TICKET: "3連単", ODDS: 2000.0, PROBABILITY: 0.01, PRICE: 2000.0,
                               PAYOUT: np.where(np.arange(3000) < 10, 200000.0, 0.0)})
    calibrator = ProbabilityCalibrator.learn(candidates)
    fixed = calibrator.apply(candidates)
    assert fixed[PROBABILITY].iloc[0] == pytest.approx(0.01 * (10 + 5) / (30 + 5))
    assert fixed[VALUE].iloc[0] == pytest.approx(fixed[PROBABILITY].iloc[0] * 2000.0)
    # 知らない券種・帯は直さない
    other = calibrator.apply(candidates.assign(**{TICKET: "単勝"}))
    assert other[PROBABILITY].iloc[0] == pytest.approx(0.01)
