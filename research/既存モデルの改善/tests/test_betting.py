"""買い方の部品（買い方の選び方・候補の買い目・荒れ具合の計算・回収率の幅）。合成データだけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.place_value import PlacePriceEstimator
from yosou.upset_level.dataset import BetType, UpsetLevel, UpsetLevelRule

from 馬券の買い方の検証.analysis.ticket import TicketType

from 既存モデルの改善.analysis.betting import BettingRule, RaceCandidateBuilder, RaceTicketProbabilities, RuleChooser
from 既存モデルの改善.analysis.betting.betting_rule import COMBO, ODDS, RACE, TICKET, VALUE
from 既存モデルの改善.analysis.betting.payout_table import PAYOUT
from 既存モデルの改善.analysis.market import CombinationTable, RaceCombinations
from 既存モデルの改善.analysis.race_probability import FinishOrderProbability
from 既存モデルの改善.analysis.scores import BootstrapInterval, ThresholdChooser
from 既存モデルの改善.analysis.upset import UpsetClassCalculator


def _candidates() -> pd.DataFrame:
    return pd.DataFrame({
        RACE: ["A", "A", "A", "B", "B"], TICKET: ["3連複"] * 5, COMBO: ["010203", "010204", "010205", "010203", "020304"],
        VALUE: [1.5, 1.2, 1.05, 2.0, 1.1], ODDS: [50.0, 400.0, 30.0, 20.0, 80.0], PAYOUT: [5000.0, 0, 0, 0, 8000.0],
    })


def test_betting_rule_keeps_the_best_tickets_per_race():
    chosen = BettingRule(TicketType.TRIO, 1.1, 100.0, 1).select(_candidates())
    # A は 400倍の組を上限で落とし、残りの期待値の高い1点。B は 2.0 の1点
    assert chosen[COMBO].tolist() == ["010203", "010203"] and chosen[RACE].tolist() == ["A", "B"]


def test_rule_chooser_picks_the_best_rate_and_adopts_only_above_one():
    rules = [BettingRule(TicketType.TRIO, 1.0, 100.0, 5), BettingRule(TicketType.TRIO, 1.4, 100.0, 5)]
    choice = RuleChooser(min_points=1, min_races=1).choose(_candidates(), rules)
    assert choice.rule == rules[0] and choice.adopted and choice.rate == pytest.approx(13000 / 400)
    losing = _candidates().assign(**{PAYOUT: 0.0})
    assert not RuleChooser(min_points=1, min_races=1).choose(losing, rules).adopted
    assert RuleChooser(min_points=100).choose(_candidates(), rules).rule is None


def test_place_price_estimator_learns_band_multipliers_and_round_trips():
    odds = pd.Series([1.2, 1.4, 2.5, 2.8, 12.0])
    payout = pd.Series([130.0, 0.0, 300.0, 330.0, 1500.0])
    estimator = PlacePriceEstimator().fit(odds, payout)
    estimate = estimator.estimate(pd.Series([1.3, 2.6, 12.0]))
    assert estimate.iloc[0] == pytest.approx(1.3 * 130 / 120)
    assert estimate.iloc[1] == pytest.approx(2.6 * np.mean([300 / 250, 330 / 280]))
    restored = PlacePriceEstimator.from_state(estimator.state())
    np.testing.assert_allclose(restored.estimate_array(np.array([1.3, 2.6])), estimate.to_numpy()[:2])


def test_race_candidates_value_each_ticket():
    p = np.zeros(18)
    p[:4] = [0.5, 0.3, 0.15, 0.05]
    probabilities = RaceTicketProbabilities(FinishOrderProbability()).of(p, field_size=4)
    win = RaceCombinations(np.array([[1], [2], [3], [4]]), np.array([1.8, 3.5, 8.0, 30.0]), np.array([1.8, 3.5, 8.0, 30.0]))
    trio = RaceCombinations(np.array([[1, 2, 3], [2, 3, 4]]), np.array([1.5, 60.0]), np.array([1.5, 60.0]))
    built = RaceCandidateBuilder({}).build(probabilities, {TicketType.WIN: win, TicketType.TRIO: trio})
    frame = pd.DataFrame(built)
    # 単勝 4番は 0.05 × 30 = 1.5、3連複 2-3-4 は確率 × 60 が 1 を超える。1番の単勝 0.5 × 1.8 = 0.9 は落ちる
    assert set(zip(frame[TICKET], frame[COMBO])) >= {("単勝", "04"), ("3連複", "020304")}
    assert ("単勝", "01") not in set(zip(frame[TICKET], frame[COMBO]))
    np.testing.assert_allclose(frame[VALUE], frame["当たる確率"] * frame["見込みの倍率"])


def test_combination_table_slices_races():
    frame = pd.DataFrame({"race_id": ["B", "A", "A"], "h1": [1, 2, 3], "h2": [2, 3, 1], "odds": [5.0, 7.0, 9.0],
                          "odds_high": [5.0, 7.0, 9.0]})
    table = CombinationTable(frame, width=2)
    assert len(table.race("A")) == 2 and len(table.race("B")) == 1 and len(table.race("Z")) == 0


def test_upset_levels_come_from_the_odds_of_each_combination():
    p = np.zeros(18)
    p[:3] = [0.6, 0.3, 0.1]
    # 単勝: 1番 2.0倍（固い）、2番 6.0倍（中荒れ）、3番 40倍（超荒れ）
    win = RaceCombinations(np.array([[1], [2], [3]]), np.array([2.0, 6.0, 40.0]), np.array([2.0, 6.0, 40.0]))
    levels = UpsetClassCalculator(UpsetLevelRule()).of_race(p, FinishOrderProbability(), {BetType.WIN: win})[BetType.WIN]
    np.testing.assert_allclose(levels, [0.6, 0.3, 0.0, 0.1])
    assert len(levels) == len(UpsetLevel)


def test_threshold_chooser_and_bootstrap_interval():
    value = pd.Series(np.r_[np.full(150, 1.05), np.full(150, 1.3)])
    payout = pd.Series(np.r_[np.full(150, 50.0), np.full(150, 150.0)])
    assert ThresholdChooser().choose(value, payout) == 1.1
    low, high = BootstrapInterval(rounds=200).of(pd.Series(np.arange(300) % 30), pd.Series(100.0, index=value.index), payout)
    assert low <= 1.0 <= high
