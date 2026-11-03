"""線を検証期間の危険度の上位 x% にして、テスト期間の消を決める。架空の値だけを使う。"""

from __future__ import annotations

import pandas as pd
import pytest

from 危険な人気馬を見極める.analysis.calibrated_window_trainer import ODDS_ONLY_COLUMN
from 危険な人気馬を見極める.analysis.strict_danger_flags import StrictDangerFlags


def _rows() -> pd.DataFrame:
    rows = []
    # 検証期間: 1番人気・2〜3番人気とも、危険度 0.00〜0.09 の 10頭（上位 10% の線は 0.081）
    for band in ("1番人気", "2〜3番人気"):
        rows += [{"レースID": f"V{band}{i}", "馬ID": f"v{i}", "区分": band, "期間": "検証", "確率": 0.3 + i / 100} for i in range(10)]
    # テスト期間: レース A は1番人気が線を超える。レース B は1番人気が線未満で、2〜3番人気が線を超える
    rows += [{"レースID": "A", "馬ID": "a1", "区分": "1番人気", "期間": "テスト", "確率": 0.40},
             {"レースID": "A", "馬ID": "a2", "区分": "2〜3番人気", "期間": "テスト", "確率": 0.45},
             {"レースID": "B", "馬ID": "b1", "区分": "1番人気", "期間": "テスト", "確率": 0.31},
             {"レースID": "B", "馬ID": "b2", "区分": "2〜3番人気", "期間": "テスト", "確率": 0.40}]
    return pd.DataFrame(rows).assign(**{"区切り": "2025年後半", ODDS_ONLY_COLUMN: 0.3})


def test_marks_only_the_top_share_and_keeps_one_per_race():
    flags = StrictDangerFlags(0.10).build(_rows()).set_index("horse_id")["is_danger"].to_dict()
    # A は1番人気を優先して1頭だけ、B は1番人気が線未満なので2〜3番人気
    assert flags == {"a1": True, "a2": False, "b1": False, "b2": True}


def test_share_must_be_between_zero_and_one():
    with pytest.raises(ValueError):
        StrictDangerFlags(1.0)
