"""当たる確率が、オッズの帯ごとにずれていないかを確かめる表。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from ..comparison.table_formatter import TableFormatter
from .candidate_columns import ODDS, PROBABILITY, RAW_PROBABILITY, TICKET
from .payout_table import PAYOUT

#: オッズの帯。
_ODDS_BANDS = [0, 2, 5, 10, 30, 100, 300, 1000, 10_000, 1e9]


class CalibrationTable:
    """期待値のカットの前の全部の買い目の候補で、券種 × オッズの帯ごとに、予想した当たる確率の平均と、
    実際に当たった割合を並べる。

    「実際 ÷ 予想」が 1 より小さい帯は、当たる確率を見積もりすぎている（期待値が見かけだけ高くなる）。
    例: 1000倍以上の帯で予想 0.2%・実際 0.03% なら、比は 0.15 で、その帯の買い目は期待値を信じられない。
    """

    def table(self, candidates: pd.DataFrame) -> Table:
        band = pd.cut(candidates[ODDS], _ODDS_BANDS, right=False)
        summary = candidates.assign(当たり=candidates[PAYOUT] > 0).groupby([TICKET, band], observed=True).agg(
            点数=(PROBABILITY, "size"), 補正前の予想の平均=(RAW_PROBABILITY, "mean"), 予想の確率の平均=(PROBABILITY, "mean"),
            実際に当たった割合=("当たり", "mean"))
        summary["補正前: 実際 ÷ 予想"] = summary["実際に当たった割合"] / summary["補正前の予想の平均"]
        summary["補正後: 実際 ÷ 予想"] = summary["実際に当たった割合"] / summary["予想の確率の平均"]
        frame = summary.reset_index()
        frame[ODDS] = [f"{interval.left:g}〜{interval.right:g}倍" for interval in frame[ODDS]]
        return TableFormatter().table(
            frame.rename(columns={ODDS: "オッズの帯"}),
            "確率のずれ: 券種 × オッズの帯ごとの、予想した当たる確率と実際に当たった割合（テスト期間・期待値のカットの前の全部の候補）",
            note="「実際 ÷ 予想」が 1 より小さいと、当たる確率を見積もりすぎている。補正後は、検証期間で決めた比で直したあとの値"
                 "（テスト期間の結果は補正に使っていないので、補正後が 1 に近ければ、補正が未知の期間でも効いている）。複勝・ワイドのオッズは最低オッズ。")
