"""能力スコアの4列の式。DB を使わず、手で作った表で確かめる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..ability_score_columns import ABILITY_INDEX, CARRIED, AbilityScoreColumns
from ..features import DEVIATION, GAP_TO_SECOND, RANK, SCORE


def test_斤量の分を引き_レース内の偏差と2位との差と順位を出す():
    features = pd.DataFrame({ABILITY_INDEX: [83.0, 80.0, 76.0, 90.0, np.nan], CARRIED: [58.0, 55.0, 54.0, 57.0, 55.0]},
                            index=[10, 11, 12, 13, 14])
    race = pd.Series(["r1", "r1", "r1", "r2", "r2"], index=features.index)
    table = AbilityScoreColumns().of(features, race)
    # 能力スコア = 能力指数 − 0.5 ×（斤量 − 55）。83.0 で 58kg なら 81.5、76.0 で 54kg なら 76.5
    assert table[SCORE].tolist()[:3] == [81.5, 80.0, 76.5]
    # 偏差は、レースの平均 79.333・標準偏差（不偏）2.566 で
    assert abs(table.loc[10, DEVIATION] - (81.5 - 79.333333) / 2.565801) < 1e-5
    # 2位との差: 1位は2位との差で正、2位は1位との差で負
    assert table.loc[10, GAP_TO_SECOND] == 1.5 and table.loc[11, GAP_TO_SECOND] == -1.5 and table.loc[12, GAP_TO_SECOND] == -5.0
    assert table[RANK].tolist()[:3] == [1.0, 2.0, 3.0]
    # 能力指数の無い馬は4つとも欠損値。相手が1頭しかいなければ偏差は欠損値、2位との差も欠損値（自分を除くと誰もいない）
    assert table.loc[14].isna().all()
    assert table.loc[13, SCORE] == 89.0 and np.isnan(table.loc[13, DEVIATION]) and table.loc[13, RANK] == 1.0
    assert list(table.index) == [10, 11, 12, 13, 14] and all(dtype == "float64" for dtype in table.dtypes)
