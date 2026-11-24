"""買い目の決まりと、年ごとの成績の数え方のテスト。値は架空。"""

from __future__ import annotations

import pandas as pd
import pytest

from yosou.shared.betting import TicketType

from ..betting import HighPayoutRule
from ..dataset import DEFAULT_BANDS, PayoutBand
from ..evaluation import YearlyPickSummary, weighted_log_loss

RACE_A, RACE_B = "2025010506010101", "2025010506010102"


def _combos() -> pd.DataFrame:
    """馬連（線 30倍・上限 1,000倍）とワイド（線 10倍・上限 300倍）の架空の組。"""
    rows = [
        (RACE_A, "馬連", "0102", 25.0, 0.060),      # 期待値 1.50 だが、高配当の線（30倍）より下
        (RACE_A, "馬連", "0103", 30.0, 0.035),      # 線ちょうど・期待値 1.05 → 買う
        (RACE_A, "馬連", "0104", 40.0, 0.026),      # 期待値 1.04 → 線に届かない
        (RACE_A, "馬連", "0205", 200.0, 0.006),     # 期待値 1.20 → 買う
        (RACE_A, "馬連", "0509", 1_000.0, 0.002),   # 上限（1,000倍）以上 → 買わない
        (RACE_A, "ワイド", "0102", 12.0, 0.100),    # 期待値 1.20 → 買う
        (RACE_B, "馬連", "0304", 50.0, 0.030),      # 期待値 1.50 → 買う
        (RACE_B, "単勝", "03", 50.0, 0.030),        # 帯の無い券種 → 買わない
    ]
    return pd.DataFrame(rows, columns=["race_id", "ticket_type", "combo", "odds", "probability"])


def test_高配当の線以上で上限未満_期待値が線以上の組だけを選ぶ() -> None:
    picks = HighPayoutRule(DEFAULT_BANDS).pick(_combos())
    assert list(zip(picks["ticket_type"], picks["combo"])) == [("馬連", "0103"), ("馬連", "0205"), ("ワイド", "0102"), ("馬連", "0304")]
    assert list(picks.columns) == list(_combos().columns)   # 列は変えない


def test_期待値の線を上げると_選ぶ組が減る() -> None:
    picks = HighPayoutRule(DEFAULT_BANDS, value_line=1.3).pick(_combos())
    assert list(picks["combo"]) == ["0304"]


def test_点数の上限は_1レース1券種につき確率の高い順() -> None:
    picks = HighPayoutRule(DEFAULT_BANDS, max_points=1).pick(_combos())
    assert list(zip(picks["race_id"], picks["ticket_type"], picks["combo"])) == [
        (RACE_A, "馬連", "0103"), (RACE_A, "ワイド", "0102"), (RACE_B, "馬連", "0304"),
    ]


def test_帯を渡した券種だけを選ぶ_空の表は空のまま() -> None:
    only_wide = {TicketType.WIDE: PayoutBand(TicketType.WIDE, 3.0, 10.0, 300.0)}
    assert list(HighPayoutRule(only_wide).pick(_combos())["ticket_type"]) == ["ワイド"]
    assert HighPayoutRule(DEFAULT_BANDS).pick(_combos().iloc[0:0]).empty


def test_年ごとの成績は_選んだ組を100円ずつ買ったときの点数と的中数と回収率() -> None:
    predictions = _combos().assign(
        race_date=pd.to_datetime(["2024-12-28"] * 6 + ["2025-01-05"] * 2),
        payout=[0, 3_000, 0, 0, 0, 0, 5_000, 0], hit=[0, 1, 0, 0, 0, 0, 1, 0],
    )
    summary = YearlyPickSummary(HighPayoutRule(DEFAULT_BANDS)).summarize(predictions).set_index("年")
    assert summary.loc[2024, "点数"] == 3 and summary.loc[2024, "的中数"] == 1 and summary.loc[2024, "買ったレース"] == 1
    assert summary.loc[2024, "回収率%"] == pytest.approx(1_000.0)  # 300円買って 3,000円
    assert summary.loc[2025, "回収率%"] == pytest.approx(5_000.0)  # 100円買って 5,000円
    assert summary.loc["合計", "点数"] == 4 and summary.loc["合計", "回収率%"] == pytest.approx(2_000.0)   # 400円買って 8,000円


def test_重みつきの対数損失は_重みの大きい行を重く見る() -> None:
    hit, probability = pd.Series([1.0, 0.0]).to_numpy(), pd.Series([0.5, 0.5]).to_numpy()
    assert weighted_log_loss(hit, probability, pd.Series([1.0, 1.0]).to_numpy()) == pytest.approx(0.6931, abs=1e-4)
    confident = pd.Series([0.9, 0.5]).to_numpy()   # 当たった行だけ良く当てた
    even = weighted_log_loss(hit, confident, pd.Series([1.0, 1.0]).to_numpy())
    hit_heavy = weighted_log_loss(hit, confident, pd.Series([9.0, 1.0]).to_numpy())
    assert hit_heavy < even
