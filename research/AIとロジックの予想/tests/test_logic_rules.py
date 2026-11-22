"""ロジックの決まり（``logic_rules``）を、架空のレースの表で確かめる。"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))

import logic_rules  # noqa: E402


def _races() -> pd.DataFrame:
    return pd.DataFrame({
        "field_size": [10, 10, 10, 10],
        "front_runners": [2, 2, 3, 2],
        "top_style": ["差し", "先行", "差し", None],
        "bias_z": [0.0, 2.0, -2.0, 0.0],
    })


def test_展開のロジックは逃げ先行が2割以下で本命が差し追込のレースだけ見送る() -> None:
    assert logic_rules.slow_pace(_races()).tolist() == [False, True, True, True]


def test_馬場の偏りのロジックは偏りと本命の脚質が逆のレースを見送る() -> None:
    assert logic_rules.track_bias(_races()).tolist() == [True, False, False, True]
