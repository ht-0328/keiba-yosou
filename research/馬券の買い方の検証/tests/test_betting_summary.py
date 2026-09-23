"""契約: 回収率のまとめは、買った行だけを数え、回収率 = 払戻 ÷ 賭け金、最大の1レースを除いた回収率も出す。"""

from 馬券の買い方の検証.analysis.settlement import PlanResult, SettlementTable
from 馬券の買い方の検証.analysis.summary import PlanSummaryTables, ReturnSummary


def _table():
    return SettlementTable.from_results([
        PlanResult("r1", "本命複勝", 1, 100, 300, 1), PlanResult("r2", "本命複勝", 1, 100, 0, 0),
        PlanResult("r3", "本命複勝", 1, 100, 900, 1), PlanResult.skip("r4", "本命複勝", "不成立"),
        PlanResult("r1", "3連複 1-2-4", 5, 500, 0, 0), PlanResult.skip("r2", "3連複 1-2-4", "候補が足りない"),
    ])


def test_return_summary_counts_only_bet_rows():
    summary = ReturnSummary.from_rows(_table().for_plan("本命複勝"))
    assert (summary.races, summary.bet_races, summary.points, summary.stake_yen, summary.payout_yen) == (4, 3, 3, 300, 1200)
    assert summary.return_rate == 4.0 and summary.hit_races == 2 and summary.max_race_payout == 900
    assert summary.return_rate_without_max == 1.0 and summary.hit_race_rate == 2 / 3
    empty = ReturnSummary.from_rows(_table().for_plan("3連複 1-2-4").iloc[1:])
    assert empty.return_rate is None and empty.bet_races == 0
    added = summary + ReturnSummary.from_rows(_table().for_plan("3連複 1-2-4"))
    assert added.stake_yen == 800 and added.payout_yen == 1200 and added.max_race_payout == 900


def test_plan_summary_tables():
    returns, skips = PlanSummaryTables(_table()).tables()
    assert returns.columns[0] == "買い方" and [row[0] for row in returns.rows] == ["本命複勝", "3連複 1-2-4"]
    assert returns.rows[0][6] == "400.0%" and returns.rows[1][6] == "0.0%"
    assert skips.rows == [["3連複 1-2-4", "候補が足りない", 1], ["本命複勝", "不成立", 1]]
