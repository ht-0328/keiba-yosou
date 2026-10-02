"""材料を足す部品のテスト。架空の値だけを使う。"""

from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
import pytest

from 一番人気を疑う.analysis.feature import PreDeadlineOddsFeatures, RaceRelativeColumns, SalePriceFeatures
from 一番人気を疑う.analysis.feature.pre_deadline_odds_features import PLACE_RATIO, QUINELLA_RATIO


def test_レース内の差と順位を足す() -> None:
    frame = pd.DataFrame({"レースID": ["r1"] * 3 + ["r2"] * 2, "指数": [60.0, 70.0, 80.0, 50.0, 50.0], "名前": list("abcde")})
    added = RaceRelativeColumns().add(frame, ["指数", "名前"])
    assert added == ["指数（レース内の差）", "指数（レース内の順位）"]
    assert frame.loc[2, "指数（レース内の差）"] == pytest.approx(1.0)
    assert frame.loc[2, "指数（レース内の順位）"] == pytest.approx(1.0)
    # 全員が同じ値のレースは、比べようがないので差を欠損にする
    assert np.isnan(frame.loc[3, "指数（レース内の差）"])


def test_セリの価格はレースの日より前のいちばん新しい取引を使う() -> None:
    frame = pd.DataFrame({"レースID": ["r1", "r1", "r1"], "horse_id": ["h1", "h2", "h3"],
                          "開催日": [date(2025, 6, 1)] * 3})
    sales = pd.DataFrame({"horse_id": ["h1", "h1", "h2"],
                          "sale_end": [date(2024, 7, 1), date(2025, 5, 1), date(2025, 7, 1)],
                          "price": [10_000_000, 100_000_000, 50_000_000], "sale_age": [1, 2, 2]})
    SalePriceFeatures().add(frame, sales)
    # h1 は2回の取引のうち新しいほう（1億円）。h2 のセリはレースより後なので使わない。h3 はセリに出ていない。
    assert frame.loc[0, "セリの価格（log）"] == pytest.approx(8.0)
    assert frame.loc[0, "セリの時の年齢"] == 2
    assert list(frame["セリで買われた"]) == [1, 0, 0]
    assert frame.loc[0, "セリの価格とレースの最高との差"] == pytest.approx(0.0)


def test_締め切り前のオッズで単勝の4個と馬連複勝の比を作り直す() -> None:
    rows = pd.DataFrame({"レースID": ["r1"] * 3 + ["r2"] * 3, "馬番": [1, 2, 3] * 2, "3着以内": [1, 1, 0] * 2,
                         "単勝オッズ": [9.9] * 6, QUINELLA_RATIO: [9.9] * 6})
    win_place = pd.DataFrame({"rid": ["r1"] * 3 + ["r2"] * 3, "horse_no": [1, 2, 3] * 2,
                              "win_odds": [2.0, 4.0, 4.0, 2.0, 4.0, np.nan],
                              "place_odds_low": [1.1] * 6, "place_odds_high": [1.3] * 6})
    quinella = pd.DataFrame({"rid": ["r1"] * 3 + ["r2"] * 3, "horse_no": [1, 2, 3] * 2, "馬連から見た2着以内率": [0.8, 0.6, 0.6] * 2})
    frame = PreDeadlineOddsFeatures().rebuild(rows, win_place, quinella)
    # r2 は3番の単勝オッズが欠けるので落とす
    assert list(frame["レースID"].unique()) == ["r1"]
    assert list(frame["単勝オッズ"]) == [2.0, 4.0, 4.0]
    assert list(frame["人気順位"]) == [1, 2, 2]
    assert frame["オッズから見た勝率"].sum() == pytest.approx(1.0)
    assert frame["オッズから見た勝率"].iloc[0] == pytest.approx(0.5)
    # 複勝の幅が全員同じなら、複勝から見た3着以内率は 1/3 ずつ
    assert frame[PLACE_RATIO].iloc[0] == pytest.approx(np.log((1 / 3) / frame["オッズから見た3着以内率"].iloc[0]))
    assert np.isfinite(frame[QUINELLA_RATIO]).all()
