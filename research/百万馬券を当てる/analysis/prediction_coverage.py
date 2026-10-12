"""第2段: 荒れたレースで、予想の上位の馬が実際に1〜3着に来たかを数える（docs/01 の 5.3）。"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from yosou.upset_premise.betting import RaceHorses

from .obi_rules import LONGSHOT_FROM_POPULARITY

#: 数える上位の頭数（乙の2着の欄 = 5頭、3着の欄・甲の組を作る馬 = 8頭、乙の1着の欄 = 3頭）。
TOP5, TOP8, FIRST3 = 5, 8, 3


class PredictionCoverage:
    """レースごとの予想（``horses``）と確定着順・確定の人気から、上位の馬の当たり方と、上位に人気薄がどれだけいるかを1行にまとめる。

    - 上位5頭のうち3着以内に来た頭数の平均。
    - 1〜3着の3頭が全部、上位8頭に入っていたレースの割合（甲・乙で3連単を当てられる形だったか）。
    - 勝ち馬が1着の確率の上位3頭に入っていたレースの割合（乙の1着の欄）。
    - 上位8頭・1着の上位3頭のうち、人気薄（6番人気以下）の割合（人気薄を選べているか）。
    """

    def row(self, horses: Mapping[str, RaceHorses], finishes: Mapping[str, Mapping[int, int]],
            popularity: Mapping[str, Mapping[int, int]]) -> dict[str, object]:
        races = [race_id for race_id in horses if race_id in finishes and race_id in popularity]
        measures = np.array([self._race(horses[race_id], finishes[race_id], popularity[race_id]) for race_id in races])
        if len(measures) == 0:
            return {"レース": 0}
        means = measures.mean(axis=0)
        return {
            "レース": len(races), "上位5頭のうち3着以内の平均頭数": round(means[0], 3),
            "1〜3着が全部上位8頭": round(means[1], 3), "勝ち馬が1着の上位3頭": round(means[2], 3),
            "上位8頭の人気薄の割合": round(means[3], 3), "1着の上位3頭の人気薄の割合": round(means[4], 3),
        }

    def _race(self, horses: RaceHorses, finishes: Mapping[int, int], popularity: Mapping[int, int]) -> list[float]:
        placed = {horse for horse, finish in finishes.items() if 1 <= finish <= 3}
        winners = {horse for horse, finish in finishes.items() if finish == 1}
        top5, top8, first3 = horses.by_top3(TOP5), horses.by_top3(TOP8), horses.by_win(FIRST3)
        return [
            float(len(placed & set(top5))), float(placed <= set(top8)), float(bool(winners & set(first3))),
            _longshot_share(top8, popularity), _longshot_share(first3, popularity),
        ]


def _longshot_share(picked: list[int], popularity: Mapping[int, int]) -> float:
    known = [popularity[horse] for horse in picked if horse in popularity]
    return float(np.mean([rank >= LONGSHOT_FROM_POPULARITY for rank in known])) if known else float("nan")
