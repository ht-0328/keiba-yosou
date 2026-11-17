"""LateWalkForward（時間の順を守った確かめ）と LateTrainingTable のテスト。学ぶ関数は偽物。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from 地方の直前の買い目 import late_columns as c
from 地方の直前の買い目.late_targets import TEACHER_BUYS
from 地方の直前の買い目.late_training_table import LateTrainingTable
from 地方の直前の買い目.late_walk_forward import LateWalkForward

from 地方の直前の買い目.testing.fake_models import FakeModels
from 地方の直前の買い目.testing.late_samples import material


def _table(tmp_path: Path) -> Path:
    path = tmp_path / "学習用の表.pkl"
    material(races=240, start="2024-01-01").to_pickle(path)
    return path


def test_区切りごとに_それより前のレースだけで学ぶ(tmp_path: Path) -> None:
    rows = LateTrainingTable(_table(tmp_path)).load()
    seen: list[pd.Timestamp] = []

    def fit(train: pd.DataFrame) -> FakeModels:
        seen.append(train[c.RACE_DATE].max())
        return FakeModels({1: 0.9}, {1: 1.5})

    scored = LateWalkForward(first_start="2024-04-01", step_months=3, fit=fit).run(rows)
    assert seen == [pd.Timestamp("2024-03-31"), pd.Timestamp("2024-06-30")]
    assert scored[c.RACE_DATE].min() == pd.Timestamp("2024-04-01") and scored[c.RACE_DATE].max() == rows[c.RACE_DATE].max()
    assert scored.loc[scored[c.HORSE_NO] == 1, c.LIKENESS].eq(0.9).all()


def test_当てられるレースが無ければ_ValueError(tmp_path: Path) -> None:
    rows = LateTrainingTable(_table(tmp_path)).load()
    with pytest.raises(ValueError, match="2030-01-01"):
        LateWalkForward(first_start="2030-01-01", fit=lambda train: FakeModels({}, {})).run(rows)


def test_学習用の表は特徴量と答えの列を足し_開催日の順(tmp_path: Path) -> None:
    rows = LateTrainingTable(_table(tmp_path)).load()
    assert set(c.FEATURES) <= set(rows.columns) and TEACHER_BUYS in rows.columns
    assert rows[c.RACE_DATE].is_monotonic_increasing


def test_学習用の表が無い_列が足りない(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="training_table.py"):
        LateTrainingTable(tmp_path / "無い.pkl").load()
    path = tmp_path / "足りない.pkl"
    material().drop(columns=[c.WIN_TEACHER]).to_pickle(path)
    with pytest.raises(ValueError, match="win_teacher"):
        LateTrainingTable(path).load()
