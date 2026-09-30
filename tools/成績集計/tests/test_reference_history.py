"""前走の決め方の契約: 同じ馬が1つ前に出走したレース。取消・除外のレースは前走に数えない（基準のページの約束）。"""

from __future__ import annotations

import pandas as pd

from 成績集計.reference_history import ReferenceHistory
from 成績集計.reference_runs import ReferenceRuns


def _runner(rid: str, day: str, abnormal: str, finish: int, popularity: int) -> dict:
    return {"rid": rid, "race_day": day, "horse_id": "H1", "abnormal": abnormal, "finish": finish, "popularity": popularity,
            "horse_no": 1, "frame_no": 1}


def test_a_scratched_race_is_not_the_previous_race():
    runners = pd.DataFrame([
        _runner("R1", "20240106", "0", 2, 3),   # 出走して2着
        _runner("R2", "20240113", "1", 0, 0),   # 出走取消（前走に数えない）
        _runner("R3", "20240120", "0", 1, 1),
    ])
    runs = ReferenceRuns()._started(runners)
    latest = ReferenceHistory().add(runs).set_index("rid").loc["R3"]
    assert latest["prev_finish"] == 2 and latest["prev_popularity"] == 3 and latest["interval_days"] == 14
