"""3連複の荒れ具合の決め方（TrioUpsetJudge）のテスト。値は架空。"""

from __future__ import annotations

import pandas as pd

from 今週の予想.trio_upset_judge import HUGE_LINE, SOLID_LINE, TrioUpsetJudge


def test_超荒れは確率の線で_固いは線に届かなければ中荒れ_ほかは確率がいちばん高いクラス() -> None:
    probabilities = pd.DataFrame({"固い": [0.6, SOLID_LINE - 0.05, 0.2, 0.2, 0.1], "中荒れ": [0.2, 0.3, 0.3, 0.4, 0.4],
                                  "大荒れ": [0.1, 0.1, 0.4, 0.4 - HUGE_LINE + 0.1, 0.3], "超荒れ": [0.1, 0.1, 0.1, HUGE_LINE, 0.2]},
                                 index=[10, 11, 12, 13, 14])
    judged = TrioUpsetJudge().of(probabilities)
    assert judged.to_dict() == {10: "固い", 11: "中荒れ", 12: "大荒れ", 13: "超荒れ", 14: "超荒れ"}
