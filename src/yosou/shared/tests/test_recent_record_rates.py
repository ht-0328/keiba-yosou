"""RecentRecordRates（直近の期間の騎手・調教師の成績）のテスト。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from yosou.shared.feature.ability.ability_columns import WIN_PRIOR
from yosou.shared.feature.ability.recent_record_rates import RecentRecordRates


def _runs() -> pd.DataFrame:
    """騎手 A が 2回走って1勝した記録（区分の列は DB から読んだときと同じ文字列の型）。"""
    return pd.DataFrame({
        "jockey_code": pd.array(["A", "A"], dtype="string"),
        "race_date": pd.to_datetime(["2026-09-01", "2026-09-08"]),
        "finish": [1.0, 5.0],
    })


def test_前日までの成績を寄せて数える() -> None:
    rates = RecentRecordRates(_runs(), "jockey_code", 365)
    found = rates.rate_on(pd.Series(["A"], dtype=object), pd.Series(pd.to_datetime(["2026-09-20"])))
    assert found.loc[0, "win"] == pytest.approx((1 + 50 * WIN_PRIOR) / (2 + 50))


def test_区分が全部欠損値でも止まらず全体の値を返す() -> None:
    # 新馬戦の「前走の騎手」は全頭が欠損値になる。型の違う空の列でも merge_asof で止まらないこと
    rates = RecentRecordRates(_runs(), "jockey_code", 365)
    found = rates.rate_on(pd.Series([np.nan, np.nan], dtype=object), pd.Series(pd.to_datetime(["2026-09-20"] * 2)))
    assert found["win"].tolist() == pytest.approx([WIN_PRIOR, WIN_PRIOR])
