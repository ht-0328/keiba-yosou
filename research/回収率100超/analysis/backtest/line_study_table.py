"""線ごとの前半・後半の成績の表。"""

from __future__ import annotations

import pandas as pd

from .place_line_choice import PlaceLineStudy


class LineStudyTable:
    """``PlaceLineChoice`` の結果（線ごとの前半・後半の成績と、決まりを満たすか）を、人が読む表にする。

    ``backtest.py`` の「2. 線の選び方」と、確率の出どころを替えた比べ（``probability_source``）で同じ表を書く。
    """

    def build(self, study: PlaceLineStudy) -> pd.DataFrame:
        rows = [{"線": result.line, "前半の回収率": round(result.early.rate, 1),
                 "前半の1年あたりの買い目": round(result.early_yearly_bets),
                 "決まりを満たす": "○" if result.qualifies else "",
                 "後半の買い目": result.late.bets, "後半の回収率": round(result.late.rate, 1),
                 "後半の90%の下限": round(result.late.low, 1), "後半の90%の上限": round(result.late.high, 1)}
                for result in study.lines]
        return pd.DataFrame(rows)
