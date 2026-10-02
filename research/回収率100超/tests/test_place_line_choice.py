"""複勝の線の決まりと、運用の目安のテスト。架空の値だけを使う。"""

from __future__ import annotations

import pandas as pd

from 回収率100超.analysis.backtest import OperationSummary, PlaceLineChoice, StakedPayback


def _tickets(ev: float, payout_early: float, payout_late: float, per_year: int) -> list[dict[str, object]]:
    rows = []
    for year in range(2019, 2027):
        payout = payout_early if year <= 2021 else payout_late
        rows += [{"rid": year * 1000 + i, "year": year, "day": f"{year}-{i % 50}", "ev": ev, "payout": payout}
                 for i in range(per_year)]
    return rows


def test_点数が足りない線は_回収率が高くても選ばない() -> None:
    # 線 1.0 以上: 年 400点・前半 110%。線 1.4 以上だけの買い目: 年 100点・前半 300%。
    # 線 1.4 は前半の回収率が高いが、1年あたり 300点に届かないので選ばない。
    rows = _tickets(1.05, 110.0, 110.0, 400) + _tickets(1.45, 300.0, 0.0, 100)
    study = PlaceLineChoice(StakedPayback(rounds=50)).run(pd.DataFrame(rows))
    assert study.chosen is not None and study.chosen.line == 1.00
    assert not [result for result in study.lines if result.line == 1.40][0].qualifies


def test_前半で100パーセントを超えない線は選ばない() -> None:
    study = PlaceLineChoice(StakedPayback(rounds=50)).run(pd.DataFrame(_tickets(1.5, 90.0, 200.0, 400)))
    assert study.chosen is None, "後半が良くても、前半で届かなければ選ばない"


def test_連敗と落ち込みは日付とレースの順に数える() -> None:
    bought = pd.DataFrame({
        "year": [2020] * 5, "day": ["2020-01-01", "2020-01-01", "2020-01-02", "2020-01-03", "2020-01-03"],
        "rid": [1, 2, 3, 4, 4], "payout": [300.0, 0.0, 0.0, 0.0, 150.0],
    })
    totals = OperationSummary().totals(bought)
    assert totals.longest_losing_streak == 3
    assert totals.max_drawdown == 300.0, "+200 の山から 3連敗で -100 まで下がる"
    assert totals.max_bets_per_race == 2


def test_年ごとの規模は投資と払戻と損益を出す() -> None:
    bought = pd.DataFrame({"year": [2020, 2020, 2021], "day": ["a", "b", "c"], "rid": [1, 2, 3],
                           "payout": [0.0, 250.0, 0.0]})
    yearly = OperationSummary().yearly(bought).set_index("年")
    assert yearly.loc[2020, "投資"] == 200 and yearly.loc[2020, "損益"] == 50
    assert yearly.loc[2021, "1日の点数"] == 1.0
