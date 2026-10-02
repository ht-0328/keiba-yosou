"""契約: 区切りごとに 線を決める → 枠A → 枠B の順で当て、テスト期間の買い目とまとめを返す。目安・表・運用の数値も合成データで出る。"""

import numpy as np
import pandas as pd

from 共通 import render

from 馬券の買い方の検証.analysis.value_betting import (
    BASELINES,
    BaselineBets,
    HorseSelection,
    LineRule,
    OperationalSummary,
    RaceRule,
    ResultTables,
    Round3Strategy,
    SearchAdoptionRule,
    StrategyEvaluator,
    UpsetBreakdown,
    WindowPreparer,
)
from 馬券の買い方の検証.analysis.value_betting import columns as c
from 馬券の買い方の検証.analysis.value_betting.protocol import FIXED_LINE, LINE_CANDIDATES, MAX_POINTS_PER_RACE, RACES_PER_DAY

from round3_fixtures import WINDOW_1, WINDOW_2, materials

_WINDOWS = [WINDOW_1, WINDOW_2]


def test_window_preparer_builds_history_from_the_previous_valid_half_year():
    preparer = WindowPreparer(materials(days=4, races=3))
    first, second = preparer.prepare(WINDOW_1), preparer.prepare(WINDOW_2)
    assert not first.history_is_full_year and second.history_is_full_year
    assert len(second.history) == 2 * len(first.history)
    assert {c.PLACE_VALUE, c.EXCLUDED, c.MARK, c.DANGER} <= set(first.test.columns)
    assert first.test[c.PLACE_VALUE].notna().sum() == first.test[c.LONGSHOT_ZONE].notna().sum()
    assert (first.test.groupby(c.RACE_ID)[c.MARK].apply(lambda marks: (marks == "◎").sum()) == 1).all()
    assert preparer.prepare(WINDOW_1) is first  # 2回目は作り直さない


def test_evaluator_applies_fixed_line_and_race_cap():
    built = materials(days=8, races=5)
    evaluator = StrategyEvaluator(WindowPreparer(built))
    fixed = evaluator.evaluate(Round3Strategy(HorseSelection.BOTH, LineRule.FIXED, RaceRule.ALL), _WINDOWS)
    assert list(fixed.by_window) == _WINDOWS and fixed.lines == {WINDOW_1: FIXED_LINE, WINDOW_2: FIXED_LINE}
    tickets = fixed.tickets
    assert (tickets[c.PLACE_VALUE] >= FIXED_LINE).all() and tickets[c.LONGSHOT_ZONE].isin(["中穴", "大穴"]).all()
    assert tickets.groupby([c.WINDOW, c.RACE_ID]).size().max() <= MAX_POINTS_PER_RACE
    assert (tickets[c.PART] == c.PART_TEST).all() and fixed.total.points == len(tickets)
    assert fixed.total.stake_yen == 100 * len(tickets) and fixed.total.payout_yen == int(tickets[c.PAYOUT_YEN].sum())
    capped = evaluator.evaluate(Round3Strategy(HorseSelection.BOTH, LineRule.FIXED, RaceRule.CAP3), _WINDOWS)
    races = capped.tickets.drop_duplicates([c.WINDOW, c.RACE_ID])
    graded = races[c.RACE_ID].str.endswith("06")
    assert races[~graded].groupby([c.WINDOW, c.RACE_DATE]).size().max() <= RACES_PER_DAY
    assert capped.total.points <= fixed.total.points and set(capped.tickets[c.RACE_ID]) <= set(tickets[c.RACE_ID])
    big = evaluator.evaluate(Round3Strategy(HorseSelection.BIG, LineRule.FIXED, RaceRule.ALL), _WINDOWS)
    assert (big.tickets[c.LONGSHOT_ZONE] == "大穴").all()


def test_evaluator_chooses_the_line_on_the_history_only():
    built = materials(days=8, races=5)
    evaluator = StrategyEvaluator(WindowPreparer(built))
    result = evaluator.evaluate(Round3Strategy(HorseSelection.BOTH, LineRule.CHOSEN, RaceRule.ALL), _WINDOWS)
    for name, line in result.lines.items():
        if np.isnan(line):
            assert result.by_window[name].points == 0
        else:
            assert line in LINE_CANDIDATES and (result.tickets.loc[result.tickets[c.WINDOW] == name, c.PLACE_VALUE] >= line).all()
    assert result.windows_at_or_above(0.0) == sum(1 for summary in result.by_window.values() if summary.points > 0)


def test_baselines_tables_breakdown_and_operational_summary_render():
    built = materials(days=3, races=4)
    baselines = BaselineBets(built)
    summaries = baselines.summaries(_WINDOWS)
    assert list(summaries) == list(BASELINES)
    test_rows = pd.concat([built.runners_of(window, c.PART_TEST) for window in _WINDOWS])
    assert summaries["全頭の複勝"].points == len(test_rows) and summaries["1番人気の複勝"].points == test_rows[c.RACE_ID].nunique()
    assert summaries["全穴馬の複勝"].points == int(test_rows[c.LONGSHOT_ZONE].notna().sum())
    evaluator = StrategyEvaluator(WindowPreparer(built))
    results = [evaluator.evaluate(Round3Strategy(HorseSelection.BOTH, LineRule.FIXED, rule), _WINDOWS) for rule in RaceRule]
    tables = ResultTables()
    rule = SearchAdoptionRule()
    produced = [
        tables.baseline_table(summaries, title="目安"),
        tables.results_table(results, [rule.verdict(result) for result in results], title="結果"),
        tables.lines_table(results, title="線"), tables.window_table(results[0], title="区切り"),
    ]
    races = pd.concat([built.races_of(window, c.PART_TEST) for window in _WINDOWS], ignore_index=True)
    produced.append(UpsetBreakdown().table(results[0].tickets, races, title="荒れ具合"))
    summary = OperationalSummary.of(results[1].tickets, races)
    produced.append(tables.operational_table(summary, title="運用"))
    text = render.render(produced, "markdown")
    assert "目安" in text and "採否" in text and "1開催日のレース数（最大）" in text
    assert summary.races_per_day_max <= RACES_PER_DAY + 1 and summary.points == len(results[1].tickets)
    assert OperationalSummary.of(results[1].tickets.iloc[0:0], races).races == 0
