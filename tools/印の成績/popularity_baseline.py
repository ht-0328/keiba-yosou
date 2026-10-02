"""比べる基準: 選んだ馬と同じ人気の馬全体の成績。"""

from __future__ import annotations

import pandas as pd

from 印の成績.perf_rows import perf_row_of

#: 率の名前（``PerfRow.rates`` の鍵のうち、出走数を除くもの）。
RATE_NAMES: tuple[str, ...] = ("勝率", "連対率", "複勝率", "馬券外率", "単勝回収率", "複勝回収率")


class PopularityBaseline:
    """選んだ馬の人気の内訳（何番人気が何割か）で、同じ人気の馬全体の成績を重み付けして平均する。

    「人気どおりに同じ頭数を買ったら」の成績になる。印の馬の成績がこれを上回れば、印に人気以上の意味がある。
    例: 選んだ馬が 1番人気 6割・2番人気 4割なら、1番人気全体の複勝率 × 0.6 + 2番人気全体の複勝率 × 0.4。
    ``everyone`` は比べる母集団（全頭。列 popularity・finish・win_payout・place_payout）。
    """

    def __init__(self, everyone: pd.DataFrame) -> None:
        self._by_popularity = {
            popularity: perf_row_of(group).rates() for popularity, group in everyone.groupby("popularity") if len(group)
        }

    def rates(self, chosen: pd.DataFrame) -> dict[str, float]:
        """率の名前 → 値（0〜1）。選んだ馬がいなければ空。"""
        weights = chosen["popularity"].value_counts(normalize=True)
        weights = weights[weights.index.isin(list(self._by_popularity))]
        if weights.empty:
            return {}
        weights = weights / weights.sum()
        return {name: sum(self._by_popularity[popularity][name] * weight for popularity, weight in weights.items())
                for name in RATE_NAMES}

