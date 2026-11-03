"""来そうと見た穴馬の成績を、同じ人気の馬全体と比べる表。架空の値だけを使う。"""

from __future__ import annotations

import pandas as pd

from 危険な人気馬を見極める.analysis.calibrated_window_trainer import ODDS_ONLY_COLUMN
from 危険な人気馬を見極める.analysis.longshot_top_report import LongshotTopReport


def _evaluation() -> pd.DataFrame:
    """中穴の 7番人気が20頭。うち4頭（h0〜h3）が3着以内で、複勝 300円。人気馬の行（区分が空）も1つ混ぜる。"""
    rows = [{"レースID": f"r{i}", "馬ID": f"h{i}", "確定着順": 3 if i < 4 else 8, "確定の単勝人気": 7,
             "単勝の払戻": 0.0, "複勝の払戻": 300.0 if i < 4 else 0.0, "穴馬の区分": "中穴", "オッズから見た3着以内率": 0.2}
            for i in range(20)]
    rows.append({"レースID": "r0", "馬ID": "fav", "確定着順": 1, "確定の単勝人気": 1, "単勝の払戻": 200.0, "複勝の払戻": 110.0,
                 "穴馬の区分": None, "オッズから見た3着以内率": 0.7})
    return pd.DataFrame(rows)


def _predictions(with_odds_only: bool) -> pd.DataFrame:
    """3着以内に来た h0 だけを、いちばん来そうと見る予測。"""
    frame = pd.DataFrame({"レースID": [f"r{i}" for i in range(20)] + ["r0"], "馬ID": [f"h{i}" for i in range(20)] + ["fav"],
                          "確率": [0.9] + [0.1] * 19 + [0.9], "期間": "テスト"})
    return frame.assign(**{ODDS_ONLY_COLUMN: 0.1}) if with_odds_only else frame


def test_top_longshots_beat_the_same_popularity():
    table = LongshotTopReport().table(_evaluation(), {"新": _predictions(True), "全頭": _predictions(False)})
    middle = [row for row in table.rows if row[1] == "中穴" and row[2] == "上位5%"]
    # 上位5%（20頭の1頭 = h0）は 3着以内率 100%・複勝 300%。同じ人気の全体は 20% と 60%。人気馬の行は入らない
    for row in middle:
        assert row[3:8] == ["1", "100.0%", "20.0%", "+80.0", "0.0%"]
        assert row[9:] == ["300.0%", "60.0%"]
    # 大穴の行は無いので空の成績
    assert all(row[3] == "0" for row in table.rows if row[1] == "大穴")
