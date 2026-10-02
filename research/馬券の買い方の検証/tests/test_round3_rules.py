"""契約: 戦略は 12 で名前が往復し、採否の基準は境界で決まり、確認に回す数と最後の1回に回す1つの選び方が決まりどおり。"""

import numpy as np
import pandas as pd
import pytest

from 馬券の買い方の検証.analysis.value_betting import (
    STRATEGIES,
    ConfirmAdoptionRule,
    FinalRule,
    HorseSelection,
    LineRule,
    RaceRule,
    Round3Strategy,
    SearchAdoptionRule,
    Stage,
    StrategyListFile,
    StrategyResult,
    TicketSummary,
    strategy_keyed,
)
from 馬券の買い方の検証.analysis.value_betting import columns as c


def test_strategy_grid_has_twelve_strategies_with_round_trip_keys():
    assert len(STRATEGIES) == 12 and len({strategy.key for strategy in STRATEGIES}) == 12
    strategy = Round3Strategy(HorseSelection.BIG, LineRule.CHOSEN, RaceRule.CAP3)
    assert strategy.key == "big|chosen|cap3" and strategy.name == "大穴だけ・線を選ぶ・1日3レースまで"
    assert Round3Strategy.from_dict(strategy.to_dict()) == strategy and Round3Strategy.from_key(strategy.key) == strategy
    assert strategy_keyed("mid|fixed|all").line_rule is LineRule.FIXED
    with pytest.raises(ValueError):
        strategy_keyed("mid|fixed")


def _summary(rate: float, points: int = 1000, lower: float = np.nan, conservative: float = np.nan) -> TicketSummary:
    stake = points * 100
    return TicketSummary(points, points, 10, stake, int(stake * rate), points // 3, lower, np.nan, conservative)


def _result(key: str, total_rate: float, window_rates, points: int = 1000, lower: float = np.nan, conservative: float = np.nan) -> StrategyResult:
    by_window = {f"w{index}": _summary(rate, points // len(window_rates)) for index, rate in enumerate(window_rates)}
    return StrategyResult(strategy_keyed(key), by_window, {name: 1.25 for name in by_window},
                          _summary(total_rate, points, lower, conservative), pd.DataFrame())


def test_ticket_summary_of_tickets():
    assert TicketSummary.of(pd.DataFrame(columns=[c.RACE_DATE, c.RACE_ID, c.STAKE_YEN, c.PAYOUT_YEN])).points == 0
    tickets = pd.DataFrame({c.RACE_DATE: pd.to_datetime(["2023-01-07", "2023-01-07", "2023-01-08"]), c.RACE_ID: ["a", "a", "b"],
                            c.STAKE_YEN: 100, c.PAYOUT_YEN: [0, 300, 0]})
    summary = TicketSummary.of(tickets)
    assert (summary.points, summary.races, summary.days, summary.stake_yen, summary.payout_yen, summary.hit_points) == (3, 2, 2, 300, 300, 1)
    assert summary.rate == pytest.approx(1.0) and summary.hit_rate == pytest.approx(1 / 3)
    assert summary.lower <= summary.upper


def test_search_rule_boundaries_and_ranking():
    rule = SearchAdoptionRule(min_return_rate=1.0, min_points=600, min_good_windows=3, candidate_limit=3)
    good = _result("mid|chosen|all", 1.05, [1.1, 1.0, 0.9, 1.2], conservative=0.95)
    assert rule.is_candidate(good) and rule.verdict(good) == "候補"
    assert not rule.is_candidate(_result("mid|chosen|cap3", 0.99, [1.1, 1.0, 1.1, 1.2]))     # 合計が 100% 未満
    assert not rule.is_candidate(_result("mid|fixed|all", 1.05, [1.1, 1.0, 0.9, 1.2], points=599))  # 点数が足りない
    assert not rule.is_candidate(_result("mid|fixed|cap3", 1.05, [1.1, 0.9, 0.9, 1.5]))     # 100% 以上の区切りが 2つ
    better = _result("big|chosen|all", 1.02, [1.0, 1.0, 1.0, 1.1], conservative=0.98)
    best = _result("big|fixed|all", 1.01, [1.0, 1.0, 1.0, 1.1], conservative=0.99)
    fourth = _result("both|fixed|all", 1.01, [1.0, 1.0, 1.0, 1.1], conservative=0.90)
    chosen = rule.chosen([good, fourth, better, best, _result("both|chosen|all", 0.5, [0.5] * 4)])
    assert [result.strategy.key for result in chosen] == ["big|fixed|all", "big|chosen|all", "mid|chosen|all"]
    assert "600" in rule.describe()


def test_confirm_rule_needs_rate_above_one_and_lower_bound_at_or_above_one():
    rule = ConfirmAdoptionRule()
    adopted = _result("mid|chosen|all", 1.08, [1.1, 1.05], lower=1.0)
    assert rule.is_adopted(adopted) and rule.verdict(adopted) == "採用"
    assert not rule.is_adopted(_result("mid|chosen|cap3", 1.0, [1.0, 1.0], lower=1.0))     # 100% ちょうどは超えていない
    assert not rule.is_adopted(_result("mid|fixed|all", 1.2, [1.3, 1.1], lower=0.99))      # 下限が届かない → 保留ではなく不採用
    assert not rule.is_adopted(_result("mid|fixed|cap3", 1.2, [1.3, 1.1]))                 # 下限が無い
    second = _result("big|fixed|all", 1.3, [1.3, 1.3], lower=1.1)
    assert rule.for_final([_result("big|chosen|all", 0.9, [0.9, 0.9], lower=0.8), adopted, second]) is adopted  # 探索の順位が上の1つ
    assert rule.for_final([_result("big|chosen|all", 0.9, [0.9, 0.9], lower=0.8)]) is None


def test_final_rule_and_stage():
    rule = FinalRule()
    assert rule.passes(_result("mid|chosen|all", 0.9, [0.9])) and not rule.passes(_result("mid|chosen|all", 0.89, [0.89]))
    assert rule.verdict(_result("mid|chosen|all", 1.1, [1.1])) == "提案へ"
    assert Stage.SEARCH.window_names == ("2023年前半", "2023年後半", "2024年前半", "2024年後半")
    assert Stage.CONFIRM.window_names == ("2025年前半", "2025年後半") and Stage.FINAL.window_names == ("2026年",)
    assert not Stage.SEARCH.runs_once and Stage.CONFIRM.runs_once and Stage("final").folder == "final"


def test_strategy_list_file_round_trips(tmp_path):
    file = StrategyListFile(tmp_path / "chosen.json")
    assert not file.exists()
    strategies = [strategy_keyed("big|chosen|cap3"), strategy_keyed("mid|fixed|all")]
    file.write(strategies, {"stage": "search"})
    assert file.read() == strategies and file.meta() == {"stage": "search"}
    with pytest.raises(FileNotFoundError):
        StrategyListFile(tmp_path / "none.json").read()
