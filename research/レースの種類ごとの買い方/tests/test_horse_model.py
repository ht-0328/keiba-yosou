"""手順4（馬の予想モデルを分ける案）の部品のテスト。値は架空で、DB は使わない。"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from レースの種類ごとの買い方.analysis.horse_model_comparison import HorseModelComparison
from レースの種類ごとの買い方.analysis.horse_windows import HORSE_WINDOWS
from レースの種類ごとの買い方.analysis.kind_columns import OTHER_SEGMENT, TARGET_SEGMENT, KindColumns


def test_区切りは2015年から2026年までの23() -> None:
    names = [window.name for window in HORSE_WINDOWS]
    assert len(names) == 23 and names[0] == "2015年前半" and names[-1] == "2026年" and len(set(names)) == 23


def test_上のクラスかハンデ戦なら対象の区分にする() -> None:
    kinds = pd.DataFrame({"race_id": ["1", "2", "3"], "class_group": ["上のクラス", "1〜2勝", "1〜2勝"],
                          "handicap": [False, True, False], "weight_type": ["定量", "ハンデ", "馬齢"]})
    columns = KindColumns(kinds)
    assert columns._segment.tolist() == [TARGET_SEGMENT, TARGET_SEGMENT, OTHER_SEGMENT]


def test_対象の区分のテスト期間だけで誤差を比べる() -> None:
    labels = pd.DataFrame({"レースID": ["a", "a", "b", "b"], "馬番": [1, 2, 1, 2], "y": [1, 0, 1, 0], "target": [True, True, False, False]})
    def frame(p_good: float) -> pd.DataFrame:
        return pd.DataFrame({"区切り": ["X"] * 4, "期間": ["テスト"] * 4, "レースID": ["a", "a", "b", "b"], "馬番": [1, 2, 1, 2],
                             "確率": [p_good, 1 - p_good, 0.01, 0.99]})
    comparison = HorseModelComparison(labels, "y", "target")
    table = comparison.table({"今": frame(0.6), "分ける": frame(0.9)}, "今")
    assert table.loc["X", "行"] == 2                                   # レース b（対象外）は数えない
    assert table.loc["X", "分ける"] == pytest.approx(-np.log(0.9)) and table.loc["X", "今"] == pytest.approx(-np.log(0.6))
    assert comparison.verdict(table, "分ける", "今") == (1, 1, True)
