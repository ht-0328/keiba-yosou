"""抑えを採用するかを決める（利用者の決まり。結果を見る前に決めたもの）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 印の成績.win5_strategy_summary import RECOVERY

from .hedge_summary import BIG

ADOPTED = "採用"
NOT_ADOPTED = "採用しない"
#: 「回収率を大きく下げない」の線（本線＋抑えの回収率が、本線だけの回収率のこの割合以上）。
KEEP_RATIO = 0.8


@dataclass(frozen=True)
class HedgeAdoptionJudge:
    """探索期間（2019〜2024年）と確認期間（2025年〜）の両方で、次の2つを満たせば採用。

    1. 本線＋抑えの 100万円以上の的中が、本線だけより多い。
    2. 本線＋抑えの回収率が、本線だけの回収率の 8割以上（回収率を大きく下げない）。
    """

    def judge(self, with_hedge: dict[str, pd.Series], main: dict[str, pd.Series]) -> tuple[str, list[str]]:
        """``with_hedge``・``main`` は 期間の名前 → その期間の成績の1行。（判定, 期間ごとの理由の文）。"""
        reasons, passed = [], []
        for period, row in with_hedge.items():
            more = int(row[BIG]) > int(main[period][BIG])
            kept = float(row[RECOVERY]) >= KEEP_RATIO * float(main[period][RECOVERY])
            passed.append(more and kept)
            reasons.append(f"{period}: 100万円以上の的中 {int(row[BIG])}回（本線だけ {int(main[period][BIG])}回）・回収率 {float(row[RECOVERY]):.1%}"
                           f"（本線だけ {float(main[period][RECOVERY]):.1%}。その 8割以上か: {'はい' if kept else 'いいえ'}）")
        return (ADOPTED if all(passed) else NOT_ADOPTED), reasons
