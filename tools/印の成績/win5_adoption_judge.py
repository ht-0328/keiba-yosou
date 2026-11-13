"""確認期間の成績を、採用の基準に照らす。"""

from __future__ import annotations

import math

import pandas as pd

from 印の成績.win5_strategy_summary import LOW, RECOVERY

#: 回収率と 90% の幅の下の端が超えるべき値。
BREAK_EVEN = 1.0
#: 判定の言葉。
ADOPTED = "採用（基準を満たした）"
BY_CHANCE = "届いたが偶然と区別できない"
NOT_REACHED = "届かなかった"


class Win5AdoptionJudge:
    """設計書「近走と適性からWIN5の買い目を決める」16 の 6. の採用の基準（結果を見る前に固定したもの）。

    確認期間で、選んだ買い方の回収率が 100% を超え、90% の幅の下の端も 100% を超え、かつ回収率が比べる相手 (1)（ルール集の 240点）と
    (2)（人気だけ。同じ予算）を上回れば採用。回収率は 100% を超えたが幅の下の端が届かなければ「届いたが偶然と区別できない」、
    ほか（回収率が 100% 以下、または比べる相手を上回らない）は「届かなかった」。
    """

    def judge(self, chosen: pd.Series, rule: pd.Series, popularity: pd.Series) -> tuple[str, str]:
        """（判定, 理由の文）。どれも ``Win5StrategySummary`` の1行。"""
        recovery, low = float(chosen[RECOVERY]), float(chosen[LOW])
        beats = recovery > float(rule[RECOVERY]) and recovery > float(popularity[RECOVERY])
        reasons = [
            f"回収率 {recovery:.1%}（100% を{'超えた' if recovery > BREAK_EVEN else '超えない'}）",
            f"90% の幅の下の端 {self._percent(low)}（100% を{'超えた' if low > BREAK_EVEN else '超えない'}）",
            f"比べる相手 (1) {float(rule[RECOVERY]):.1%}・(2) {float(popularity[RECOVERY]):.1%} を{'上回った' if beats else '上回らない'}",
        ]
        if recovery > BREAK_EVEN and low > BREAK_EVEN and beats:
            verdict = ADOPTED
        elif recovery > BREAK_EVEN and not low > BREAK_EVEN:
            verdict = BY_CHANCE
        else:
            verdict = NOT_REACHED
        return verdict, "。".join(reasons)

    def _percent(self, value: float) -> str:
        return "―" if math.isnan(value) else f"{value:.1%}"
