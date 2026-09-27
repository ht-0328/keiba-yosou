"""逃げたい馬の数え方を、何通りか並べる（1行 = 1レース）。"""

from __future__ import annotations

import pandas as pd

from .early_run_history import LEAD_RATE, LEAD_RATE_SAME_SURFACE, LED_RECENTLY, RUNS_BEFORE

#: 先頭率が高い（逃げたい）とみなす線と、数えるのに要る過去走の数。
RATE_LINE, MIN_RUNS = 0.4, 3
#: 比べる数え方の名前と中身。
COUNTS: dict[str, str] = {
    "推定脚質が逃げ": "直近3走の脚質の真ん中が逃げの馬の数（手順1の数え方）",
    "近3走で逃げた": "近3走で1回でも逃げた馬の数",
    "先頭率0.4以上": "近5走の先頭率が 0.4 以上の馬の数",
    "同じ芝ダの先頭率0.4以上": "今回と同じ芝ダの近5走の先頭率が 0.4 以上の馬の数",
    "同じ芝ダの先頭率0.4以上・3走以上": "上に加えて、過去走が3走以上ある馬の数",
    "先頭率の合計": "近5走の先頭率を、出走馬全員で足した値",
    "同じ芝ダの先頭率の合計": "今回と同じ芝ダの近5走の先頭率を、出走馬全員で足した値",
}


class LeaderCountTable:
    """``EarlyRunHistory`` を通した出走の表から、レースごとに逃げたい馬を ``COUNTS`` の数え方で数える。

    例: 先頭率が 0.6・0.4・0.2 の3頭と、0 の 13頭のレースなら、「先頭率0.4以上」は 2頭、「先頭率の合計」は 1.2。
    """

    def build(self, runners: pd.DataFrame) -> pd.DataFrame:
        rate = runners[LEAD_RATE]
        same = runners[LEAD_RATE_SAME_SURFACE]
        flags = pd.DataFrame({
            "推定脚質が逃げ": runners["style_before"] == "逃げ",
            "近3走で逃げた": runners[LED_RECENTLY] >= 1,
            "先頭率0.4以上": rate >= RATE_LINE,
            "同じ芝ダの先頭率0.4以上": same >= RATE_LINE,
            "同じ芝ダの先頭率0.4以上・3走以上": (same >= RATE_LINE) & (runners[RUNS_BEFORE] >= MIN_RUNS),
            "先頭率の合計": rate.fillna(0.0),
            "同じ芝ダの先頭率の合計": same.fillna(0.0),
        }).astype(float)
        return flags.groupby(runners["race_id"]).sum().reset_index()
