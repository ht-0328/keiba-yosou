"""選んだ買い方と比べる相手の、期間ごとの成績と、採用の判定の表。"""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd

from 共通.render import Table

from yosou.form_aptitude_win5_tickets.settlement import STRATEGY

from 印の成績.win5_summary_cells import HEADERS, Win5SummaryCells

#: 選べる買い方が無かったときの判定。
NO_CHOICE = "選べる買い方なし（確認期間に進まない）"


class Win5ConfirmationReport:
    """設計書「近走と適性からWIN5の買い目を決める」16 の 5.・6.。選んだ買い方と比べる相手の、探索期間と確認期間の成績を並べた表と、
    確認期間で採用の基準に照らした判定の表。"""

    def __init__(self) -> None:
        self._cells = Win5SummaryCells()

    def tables(self, summaries: dict[str, pd.DataFrame], labels: Sequence[str], chosen: str | None,
               verdict: tuple[str, str] | None) -> list[Table]:
        """``summaries`` は期間の名前 → その期間の成績（``Win5StrategySummary``）。``labels`` は並べる買い方（選んだ買い方と比べる相手）。
        ``verdict`` は（判定, 理由）。選べる買い方が無ければ None。"""
        rows = []
        for period, summary in summaries.items():
            by_label = summary.set_index(STRATEGY)
            for label in labels:
                row = by_label.loc[label] if label in by_label.index else None
                rows.append([period, label, *self._cells.cells(row)])
        note = ("確定オッズで確かめた値。実際に買うとき（締め切り前のオッズ）より良く出ることがある。払戻には返還の代金を含む。"
                "比べる相手は毎回買う（キャリーオーバーの日だけの行は、その日だけ）。")
        compared = Table(["期間", "買い方", *HEADERS], rows, title="WIN5 の選んだ買い方と比べる相手", note=note)
        judged = Table(["選んだ買い方", "判定", "理由"], [self._verdict_row(chosen, verdict)], title="WIN5 の採用の判定（確認期間）",
                       note="基準（設計書 16 の 6.。結果を見る前に固定）: 確認期間で回収率と 90% の幅の下の端が 100% を超え、"
                            "回収率が比べる相手 (1) ルール集の 240点・(2) 人気だけ（同じ予算）を上回る。")
        return [compared, judged]

    def _verdict_row(self, chosen: str | None, verdict: tuple[str, str] | None) -> list[str]:
        if chosen is None or verdict is None:
            return ["―", NO_CHOICE, "探索期間で、買った日が 30日以上で回収率が 100% を超える買い方が無かった"]
        return [chosen, *verdict]
