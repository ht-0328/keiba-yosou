"""LateTargets（答えの列）のテスト。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 地方の直前の買い目 import late_columns as c
from 地方の直前の買い目.late_targets import RETURN, RETURN_CAP, TEACHER_BUYS, LateTargets


def _rows() -> pd.DataFrame:
    return pd.DataFrame({c.RACE_ID: ["r"] * 3, c.WIN_TEACHER: [0.6, 0.2, 0.2], c.FINAL_ODDS: [1.5, 6.0, 200.0], c.WON: [0, 0, 1]})


def test_先生の確率をレースの中で合計1に直し_確定オッズを掛けて線以上なら買う() -> None:
    rows = LateTargets().attach(_rows())
    assert rows[TEACHER_BUYS].tolist() == [0.0, 1.0, 1.0]   # 0.6×1.5=0.9、0.2×6=1.2、0.2×200=40


def test_戻りは勝った馬の確定オッズ_上限で切る() -> None:
    rows = LateTargets().attach(_rows())
    assert rows[RETURN].tolist() == [0.0, 0.0, RETURN_CAP]


def test_先生の確率の無い行は_買うかどうかが欠損() -> None:
    table = _rows()
    table.loc[0, c.WIN_TEACHER] = np.nan
    assert np.isnan(LateTargets().attach(table)[TEACHER_BUYS].iloc[0])
