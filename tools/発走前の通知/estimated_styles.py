"""出走馬ごとの推定脚質（そのレースより前の直近3走の脚質の中央）。事実表の ``style_before`` と同じ決まり。"""

from __future__ import annotations

import math

import pandas as pd

from 共通.codes import STYLE_NAMES

#: 推定に使う直近の走の数。
RUNS = 3
#: コーナーの順位から脚質を決める線（頭数に対する割合。事実表と同じ）。先頭が逃げ、前から 35% までが先行、70% までが差し、残りが追込。
FRONT_SHARE, MIDDLE_SHARE = 0.35, 0.70


class EstimatedStyles:
    """1走の脚質は、レース後の判定（中央）。判定が無い走は、``from_corners`` のとき（地方）だけ、最初に回ったコーナーの順位と頭数から作る。
    直近3走の脚質の番号（1 逃げ〜4 追込）の中央を取る。2走なら前寄り、1走ならその脚質、過去走が無い馬は入れない。
    例: 直近3走が 先行・差し・逃げ なら 先行。"""

    def __init__(self, from_corners: bool = False) -> None:
        self._from_corners = from_corners

    def of(self, past: pd.DataFrame) -> dict[int, str]:
        """``past`` は ``PastStyleRepository`` の表（馬番ごとに新しい走から）。馬番 → 脚質の名前。"""
        styles: dict[int, str] = {}
        for horse_no, runs in past.groupby("horse_no", sort=False):
            numbers = [number for number in (self._number(run) for _, run in runs.iterrows()) if number is not None][:RUNS]
            if numbers:
                styles[int(horse_no)] = STYLE_NAMES[str(self._middle(numbers))]
        return styles

    def _number(self, run: pd.Series) -> int | None:
        code = str(run["style_code"] or "").strip()
        if code in STYLE_NAMES:
            return int(code)
        if not self._from_corners or pd.isna(run["corner"]) or pd.isna(run["field_size"]) or run["field_size"] <= 0:
            return None
        rank, field = int(run["corner"]), int(run["field_size"])
        if rank == 1:
            return 1
        if rank <= math.ceil(field * FRONT_SHARE):
            return 2
        return 3 if rank <= math.ceil(field * MIDDLE_SHARE) else 4

    @staticmethod
    def _middle(numbers: list[int]) -> int:
        """3つなら中央、2つなら前寄り（小さいほう）、1つならそれ。"""
        if len(numbers) >= 3:
            return sorted(numbers)[1]
        return min(numbers)
