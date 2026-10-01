"""契約: 正解を作らなかったレースには、直線・コーナーを5回以上通る・通過順位の記録なし・先頭が決まらない（①②）と、
タイムの記録なし・基準なし（③⑥）の順で、最初に当てはまった理由が1つ付き、切り口ごとの割合になる。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..dataset import label_names as names
from ..evaluation import UnlabeledRaceTable
from ..evaluation import unlabeled_race_table as unlabeled


def races() -> pd.DataFrame:
    """5レース: 作れた・直線・5回以上・記録なし・先頭が決まらない（基準なし）。"""
    return pd.DataFrame({
        "race_id": ["r1", "r2", "r3", "r4", "r5"],
        unlabeled.YEAR: ["2024", "2024", "2025", "2025", "2025"],
        unlabeled.VENUE: ["東京", "新潟", "中山", "東京", "東京"],
        unlabeled.FIELD_SIZE: [16, 18, 12, 8, 10],
        unlabeled.PACE_NAME: ["平均", "ハイ", "スロー", "平均", np.nan],
        names.TRACK_CODE: ["11", "10", "18", "23", "24"],
        names.FIRST_CORNER_NO: [3.0, np.nan, 1.0, np.nan, 1.0],
        names.CORNER_LAPS_OVER_ONE: [False, False, True, False, False],
        names.FIRST_CORNER_LEADER_NO: [5.0, np.nan, np.nan, np.nan, np.nan],
        names.FIRST_HALF_TIME: [35.0, 33.0, 36.0, 36.5, 36.0],
        names.SECOND_HALF_TIME: [34.0, 33.5, 35.0, np.nan, 37.0],
        unlabeled.FIRST_STAGE: ["同じクラス", "同じクラス", "クラスをまとめた", "同じクラス", "なし"],
        unlabeled.SECOND_STAGE: ["同じクラス", "同じクラス", "同じクラス", "同じクラス", "なし"],
    })


def test_each_race_gets_the_first_matching_reason() -> None:
    table = UnlabeledRaceTable().table(races())
    whole = table[table[unlabeled.ASPECT] == "全体"].iloc[0]
    assert whole[unlabeled.RACES] == 5
    for reason in unlabeled.LEADER_REASONS:
        assert np.isclose(whole[f"①② {reason}"], 0.2)
    assert np.isclose(whole["③ 基準なし"], 0.2)
    assert np.isclose(whole["⑥ タイムの記録なし"], 0.2)
    assert np.isclose(whole["⑥ 基準なし"], 0.2)


def test_shares_are_split_by_field_size_venue_pace_and_year() -> None:
    table = UnlabeledRaceTable().table(races()).set_index([unlabeled.ASPECT, unlabeled.VALUE])
    assert table.loc[("頭数", "〜10頭"), unlabeled.RACES] == 2
    assert np.isclose(table.loc[("競馬場", "東京"), "①② 通過順位の記録なし"], 1 / 3)
    assert table.loc[("ペースの区分", "区分なし"), unlabeled.RACES] == 1
    assert np.isclose(table.loc[("年", "2024"), "①② 直線"], 0.5)


def test_examples_list_races_whose_leader_was_not_decided() -> None:
    assert UnlabeledRaceTable().examples(races()) == ["r5"]
