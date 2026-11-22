"""見送りのロジックの候補（``logic_candidates``）を、架空のレースの表で確かめる。"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))

import logic_candidates  # noqa: E402


def _races() -> pd.DataFrame:
    return pd.DataFrame({
        "class_name": ["G3", "1勝クラス", "オープン", "未勝利"],
        "top_win_odds": [4.0, 25.0, 30.0, 6.0],
        "stake": [5000, 5000, 5000, 5000],
        "back": [0.0, 0.0, 0.0, 10000.0],
    })


def test_オープン以上の候補はオープンと重賞とLだけ見送る() -> None:
    assert logic_candidates.skip_of("オープン以上")(_races()).tolist() == [True, False, True, False]


def test_つないだ候補はどれかに当たれば見送る() -> None:
    assert logic_candidates.skip_of("オープン以上+◎の単勝20倍以上")(_races()).tolist() == [True, True, True, False]


def test_成績は見送らなかったレースだけで数える() -> None:
    result = logic_candidates.metrics(_races(), np.array([True, False, True, False]), days=2)
    assert result == {"買う": 2, "回収率": 1.0, "的中率": 0.5, "1日の儲け": 0.0}
