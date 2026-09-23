"""券種プールの列を作る部品のテスト。架空の値だけを使う。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from 回収率100超.analysis.feature import PoolFeatures

POOLS = ("3連単から見た勝率", "3連複から見た3着以内率")
BUILDER = PoolFeatures(POOLS, "単勝から見た勝率", "単勝から見た複勝率")


def _race() -> pd.DataFrame:
    """1レース3頭。3連単プールは1頭目を単勝より高く見ている。"""
    return pd.DataFrame({
        "rid": ["R1"] * 3,
        "単勝から見た勝率": [0.5, 0.3, 0.2],
        "単勝から見た複勝率": [0.9, 0.7, 0.4],
        "3連単から見た勝率": [0.6, 0.25, 0.15],
        "3連複から見た3着以内率": [0.9, 0.7, 0.4],
    })


def test_log_と順位と差の3種類を足す() -> None:
    _, added = BUILDER.add_to(_race())
    assert "log_3連単から見た勝率" in added
    assert "順位_3連単から見た勝率" in added
    assert "3連単から見た勝率と単勝の差" in added


def test_順位はレース内で確率の高い順() -> None:
    frame, _ = BUILDER.add_to(_race())
    assert list(frame["順位_3連単から見た勝率"]) == [1, 2, 3]


def test_3連単が単勝より高く見ている馬は差が正になる() -> None:
    frame, _ = BUILDER.add_to(_race())
    assert frame["3連単から見た勝率と単勝の差"].iloc[0] > 0
    assert frame["3連単から見た勝率と単勝の差"].iloc[2] < 0


def test_同じ値どうしを比べると差は0() -> None:
    frame, _ = BUILDER.add_to(_race())
    assert frame["3連複から見た3着以内率と単勝の差"].to_numpy() == pytest.approx(np.zeros(3))


def test_確率が0でも計算できる() -> None:
    race = _race()
    race.loc[2, "3連単から見た勝率"] = 0.0
    frame, _ = BUILDER.add_to(race)
    assert np.isfinite(frame["log_3連単から見た勝率"]).all()
