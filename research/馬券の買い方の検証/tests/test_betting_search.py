"""契約: 格子はパターンが使う軸だけを回し、評価はレース単位に広めと少点数を足し、採否の基準は境界で決まり、選んだ戦略は JSON で往復する。"""

import numpy as np
import pandas as pd
import pytest

from yosou.upset_level.dataset import BetType

from 馬券の買い方の検証.analysis import column_names as names
from 馬券の買い方の検証.analysis.participation import PATTERNS, PATTERNS_BY_KEY, pattern_by_key
from 馬券の買い方の検証.analysis.search import (
    AdoptionRule,
    ChosenStrategiesFile,
    ConfirmRunner,
    SearchRunner,
    Strategy,
    StrategyEvaluator,
    StrategyGrid,
)
from 馬券の買い方の検証.analysis.settlement import PlanResult, SettlementTable
from 馬券の買い方の検証.analysis.summary import ReturnSummary
from 馬券の買い方の検証.analysis.summary.strategy_tables import StrategyTables
from 馬券の買い方の検証.analysis.ticket import NARROW_PLANS, WIDE_PLANS, plan_named

_IDS = ["r1", "r2", "r3", "r4"]


def _races():
    return pd.DataFrame({
        names.RACE_ID: _IDS, names.RACE_DATE: pd.to_datetime(["2025-07-05", "2025-07-06", "2025-08-02", "2025-08-03"]),
        names.WEEK: ["2025-07-05", "2025-07-05", "2025-08-02", "2025-08-02"], names.IS_GRADED: [False, True, False, False],
        **{names.upset_column(bet): [0.9, 0.2, 0.7, 0.4] for bet in BetType},
        names.FAVORITE_PROB: [0.4, 0.6, 0.5, 0.7], names.FAVORITE_DANGER: [0.3, 0.2, 0.5, np.nan],
    })


def _settlement():
    wide, narrow, baseline = "3連複 1-2-10", "本命複勝", "1番人気 単勝"
    return SettlementTable.from_results([
        PlanResult("r1", wide, 17, 1700, 5000, 1), PlanResult("r2", wide, 17, 1700, 0, 0),
        PlanResult("r3", wide, 17, 1700, 0, 0), PlanResult.skip("r4", wide, "候補が足りない"),
        PlanResult("r1", narrow, 1, 100, 0, 0), PlanResult("r2", narrow, 1, 100, 300, 1),
        PlanResult("r3", narrow, 1, 100, 150, 1), PlanResult("r4", narrow, 1, 100, 0, 0),
        *[PlanResult(race, baseline, 1, 100, 200 if race == "r2" else 0, int(race == "r2")) for race in _IDS],
        *[PlanResult(race, "1番人気 複勝", 1, 100, 110, 1) for race in _IDS],
    ])


def test_grid_uses_only_the_axes_each_pattern_needs():
    grid = StrategyGrid(PATTERNS, WIDE_PLANS, NARROW_PLANS)
    strategies = grid.strategies(_races())
    by_pattern = {key: [s for s in strategies if s.pattern_key == key] for key in PATTERNS_BY_KEY}
    assert len(by_pattern["02upset"]) == 3 * len(WIDE_PLANS)
    assert len(by_pattern["03conf"]) == 3 * 2 * len(NARROW_PLANS)
    assert len(by_pattern["04union"]) == 3 * 3 * 2 * len(WIDE_PLANS) * len(NARROW_PLANS)
    assert len(by_pattern["01all-narrow"]) == len(NARROW_PLANS) and by_pattern["01all-narrow"][0].upset_threshold is None
    upset_only = by_pattern["02upset"][0]
    assert upset_only.narrow_plan is None and upset_only.form_threshold is None
    assert upset_only.upset_threshold == pytest.approx(float(_races()["upset_trio"].quantile(0.8)))


def test_evaluator_sums_wide_and_narrow_per_race():
    evaluator = StrategyEvaluator(_settlement(), PATTERNS_BY_KEY)
    strategy = Strategy("04union", "3連複 1-2-10", "本命複勝", 0.5, 0.6, 0.5, 0.4, None)
    result = evaluator.evaluate(strategy, _races())
    assert (result.wide_races, result.narrow_races, result.selected_races) == (2, 1, 3)   # 荒れ: r1・r3、自信: r2
    assert result.total.stake_yen == 3500 and result.total.payout_yen == 5300 and result.total.bet_races == 3
    assert result.total.max_race_payout == 5000 and result.total.return_rate == pytest.approx(5300 / 3500)
    assert result.wide.stake_yen == 3400 and result.narrow.payout_yen == 300
    assert {month: summary.stake_yen for month, summary in result.by_month.items()} == {"2025-07": 1800, "2025-08": 1700}
    weekly = evaluator.evaluate(Strategy("05week-upset", "3連複 1-2-10", None, None, None, None, None, 1), _races())
    assert weekly.wide_races == 2 and weekly.narrow is None and weekly.total.stake_yen == 3400
    with pytest.raises(LookupError):
        evaluator.evaluate(Strategy("02upset", "3連単 待ちの型", None, 0.5, 0.6, None, None, None), _races())


def test_adoption_rule_boundaries():
    rule = AdoptionRule(min_return_rate=1.0, min_races=2, min_points=10, min_return_rate_without_max=0.9)
    good = ReturnSummary(races=3, bet_races=3, points=3, stake_yen=300, payout_yen=310, hit_races=2, max_race_payout=30)
    assert rule.is_adopted(good) and rule.verdict(good) == "候補"
    lucky = ReturnSummary(3, 3, 3, 300, 310, 1, 310)
    assert not rule.is_adopted(lucky)  # 最大の1レースを除くと 0%
    few = ReturnSummary(1, 1, 1, 100, 200, 1, 50)
    assert not rule.is_adopted(few)
    assert not rule.is_adopted(ReturnSummary(0, 0, 0, 0, 0, 0, 0))


def test_search_and_confirm_runners_and_json(tmp_path):
    settlement = _settlement()
    evaluator = StrategyEvaluator(settlement, PATTERNS_BY_KEY)
    grid = StrategyGrid([pattern_by_key("02upset"), pattern_by_key("03conf")], [plan_named("3連複 1-2-10")], [plan_named("本命複勝")])
    runner = SearchRunner(evaluator, grid, AdoptionRule(min_races=1, min_points=1, min_return_rate_without_max=0.0))
    results = runner.run(_races())
    assert len(results) == 3 + 6
    rates = [result.return_rate if result.return_rate is not None else -1 for result in results]
    assert rates == sorted(rates, reverse=True)
    chosen = runner.chosen(results, limit=2)
    assert len(chosen) <= 2 and all(isinstance(strategy, Strategy) for strategy in chosen)
    file = ChosenStrategiesFile(tmp_path / "chosen.json")
    file.write(chosen, {"period": "2025H2"})
    assert file.read() == chosen
    confirmed = ConfirmRunner(evaluator).run(chosen, _races())
    assert [result.strategy for result in confirmed] == chosen
    tables = StrategyTables(PATTERNS_BY_KEY, AdoptionRule())
    table = tables.results_table(results, title="探索", limit=5)
    assert len(table.rows) == 5 and table.columns[0] == "番号" and table.columns[-1] == "採否"
    monthly = tables.monthly_table(confirmed, title="月別")
    assert monthly.columns[:2] == ["番号", "戦略"]
    baseline = tables.baseline_table(settlement, _IDS, title="基準")
    assert [row[0] for row in baseline.rows] == ["1番人気 単勝", "1番人気 複勝", "本命複勝"] and baseline.rows[1][6] == "110.0%"
