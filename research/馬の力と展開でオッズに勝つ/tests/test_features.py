"""材料を作る部品のテスト。架空の値だけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from 馬の力と展開でオッズに勝つ.analysis.race_log_loss import RaceLogLoss
from 馬の力と展開でオッズに勝つ.analysis.race_relative import RaceRelative
from 馬の力と展開でオッズに勝つ.analysis.recent_record_rates import RecentRecordRates
from 馬の力と展開でオッズに勝つ.analysis.track_record_rates import TrackRecordRates


def _facts() -> pd.DataFrame:
    """騎手 A が 1月1日に1勝、1月2日に1敗、1月3日に走る架空の事実表。"""
    return pd.DataFrame({
        "race_id": ["r1", "r2", "r3"], "horse_no": [1, 1, 1], "ran": [True, True, True],
        "race_date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
        "finish": [1, 5, 2], "jockey_code": ["A", "A", "A"],
    })


def test_通算の成績はその日より前の結果だけで数える() -> None:
    rates = TrackRecordRates().build(_facts(), ["jockey_code"], "騎手").set_index("race_id")
    # 1月1日は前の結果が無いので全体の平均。1月3日は 2戦1勝を全体の平均に寄せた値で、当日の2着は入らない。
    overall = 1 / 3
    assert rates.loc["r1", "騎手_勝率"] == pytest.approx(overall)
    assert rates.loc["r3", "騎手_勝率"] == pytest.approx((1 + 100 * overall) / (2 + 100))
    assert rates.loc["r3", "騎手_出走数"] == 2


def test_直近の成績は期間の外の結果を数えない() -> None:
    recent = RecentRecordRates(_facts(), "jockey_code", window_days=1)
    found = recent.rate_on(pd.Series(["A"]), pd.Series(pd.to_datetime(["2026-01-03"])))
    # 1日間なので、1月2日の1敗だけを数える（1月1日の1勝は入らない）。
    overall = 1 / 3
    assert found["win"].iloc[0] == pytest.approx((0 + 50 * overall) / (1 + 50))


def test_レース内の位置は小さいほど良い列を逆に数える() -> None:
    table = pd.DataFrame({"race_id": ["r"] * 3, "着順": [3.0, 1.0, 2.0], "指数": [70.0, 80.0, 75.0]})
    added = RaceRelative().add(table, {"着順": False, "指数": True})
    assert list(added["着順_順位"]) == [3, 1, 2]
    assert list(added["指数_最良との差"]) == [-10.0, 0.0, -5.0]


def test_ログ損失は勝ち馬が1頭に決まるレースだけで測る() -> None:
    table = pd.DataFrame({"race_id": ["a", "a", "b", "b"], "won": [1, 0, 1, 1],
                          "p": [0.25, 0.75, 0.5, 0.5], "market_win": [0.5, 0.5, 0.5, 0.5]})
    losses = RaceLogLoss().per_race(table, "p")
    assert list(losses["race_id"]) == ["a"]
    assert losses["model"].iloc[0] == pytest.approx(-np.log(0.25))
