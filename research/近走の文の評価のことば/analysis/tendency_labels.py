"""苦手の傾向を、線の候補ごとに各走の「その走までの成績」から付ける。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 近走の文.loss_reason import HEAVY_GOINGS


@dataclass(frozen=True)
class TendencyLine:
    """線の候補。両側それぞれ ``min_each`` 走以上あり、3着以内率の差が ``gap`` 以上なら「苦手」とみなす。"""

    min_each: int
    gap: float

    @property
    def label(self) -> str:
        return f"両側 {self.min_each} 走以上・差 {self.gap:.2f} 以上"


#: 比べる線の候補（今の本番の線は 3走・0.50）。
LINES: tuple[TendencyLine, ...] = (TendencyLine(3, 0.5), TendencyLine(2, 0.5), TendencyLine(3, 0.34), TendencyLine(2, 0.34))
#: 条件の種類。
HEAVY, SURFACE, DISTANCE = "重い馬場が苦手（今回も重・不良）", "芝ダが苦手（今回も同じ芝ダ）", "距離が苦手（今回も同じ距離）"
KINDS: tuple[str, ...] = (HEAVY, SURFACE, DISTANCE)


class TendencyLabels:
    """馬ごと・日付順に並んだ走の表に、「その走より前の成績」で苦手と分かる条件に今回も当たるか、の真偽の列を足す。

    こちらの側（重・不良／同じ芝ダ／同じ距離）と相手の側（良・稍重／ほかの芝ダ／ほかの距離）の、その走より前の出走数と3着以内の数を
    累積で数え、線 ``TendencyLine`` で苦手かを決める。列の名前は ``f"{種類}｜{線}"``。
    """

    def of(self, frame: pd.DataFrame) -> pd.DataFrame:
        heavy = frame["condition"].isin(HEAVY_GOINGS)
        sides = {HEAVY: heavy, SURFACE: frame["surface"], DISTANCE: frame["distance_m"]}
        total_runs, total_placed = self._before(frame, [frame["horse_id"]])
        labels = pd.DataFrame(index=frame.index)
        for kind, key in sides.items():
            same_runs, same_placed = self._before(frame, [frame["horse_id"], key])
            other_runs, other_placed = total_runs - same_runs, total_placed - same_placed
            same_rate = same_placed / same_runs.where(same_runs > 0)
            other_rate = other_placed / other_runs.where(other_runs > 0)
            for line in LINES:
                weak = (same_runs >= line.min_each) & (other_runs >= line.min_each) & ((other_rate - same_rate) >= line.gap)
                labels[f"{kind}｜{line.label}"] = (weak & heavy).fillna(False) if kind == HEAVY else weak.fillna(False)
        return labels.astype(bool)

    def _before(self, frame: pd.DataFrame, keys: list[pd.Series]) -> tuple[pd.Series, pd.Series]:
        """鍵ごとの、その行より前の出走数と3着以内の数。"""
        grouped = frame.groupby(keys, sort=False)
        runs = grouped.cumcount().astype(float)
        placed = grouped["placed"].cumsum() - frame["placed"]
        return runs, placed
