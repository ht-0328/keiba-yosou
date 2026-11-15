"""研究「地方の期待度」の部品を、架空の値で確かめる（実DB は使わない）。"""

from __future__ import annotations

import pandas as pd
import pytest

from 地方の推奨買目.ticket_plan import TicketPlan

from 地方の期待度.analysis.bulk_plan_chooser import UPSET, BulkPlanChooser
from 地方の期待度.analysis.race_scores import EXPECTED, EXPECTED_PROFIT, RaceScores

_A, _B = 2024010145110101, 2024010145110102


def _table(rows: list[tuple[int, int, int, float, float, float]]) -> pd.DataFrame:
    """(race_id, 馬番, 頭数, 確率, オッズ, 荒れ具合)。"""
    return pd.DataFrame([{"race_id": rid, "a": a, "field_size": heads, "P": p, "odds": odds, "payout": 0, UPSET: upset}
                         for rid, a, heads, p, odds, upset in rows])


def test_頭数の線と点数の上限はレースごとに引く() -> None:
    table = _table([(_A, 1, 12, 0.2, 6.0, 0.7), (_A, 2, 12, 0.1, 15.0, 0.7), (_A, 3, 12, 0.1, 11.0, 0.7),
                    (_B, 1, 12, 0.2, 9.0, 0.7), (_B, 2, 12, 0.1, 12.0, 0.7), (_B, 3, 7, 0.5, 9.0, 0.7)])
    table.loc[5, "race_id"] = 2024010145110103   # 7頭のレース
    chosen = BulkPlanChooser().choose(TicketPlan("単勝", 1.0, min_heads=8, top_k=1), table)
    # 期待値 1.0 以上の組のうち、レースごとに期待値のいちばん高い1点（全体の上位1点ではない）。7頭のレースは買わない
    assert sorted(zip(chosen["race_id"], chosen["a"])) == [(_A, 2), (_B, 1)]


def test_荒れ具合の線に届かないレースと荒れ具合の無いレースは買わない() -> None:
    table = _table([(_A, 1, 12, 0.2, 6.0, 0.59), (_B, 1, 12, 0.2, 6.0, 0.6)])
    table = pd.concat([table, _table([(2024010145110103, 1, 12, 0.2, 6.0, float("nan"))])], ignore_index=True)
    chosen = BulkPlanChooser().choose(TicketPlan("単勝", 1.0, upset_min=0.6), table)
    assert chosen["race_id"].tolist() == [_B]


def test_レースの見込みは期待値の平均で_払戻は当たった点を全部足す() -> None:
    bets = pd.DataFrame({"race_id": [_A, _A, _A], "year": 2024, "race_date": "2024-01-01", "ev": [1.0, 1.2, 1.7],
                         "payout": [0, 250, 130]})
    race = RaceScores().of(bets).iloc[0]
    assert race["points"] == 3 and race["stake"] == 300 and race["returned"] == 380 and race["best"] == 250
    assert race[EXPECTED] == pytest.approx(1.3) and race[EXPECTED_PROFIT] == pytest.approx(0.9)
