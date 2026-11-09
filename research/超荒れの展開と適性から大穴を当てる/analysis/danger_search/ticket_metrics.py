"""買い目から、券種ごと・消を使う買い方・全部の合計の的中率と回収率を、期間ごと・年ごとに数える。"""

from __future__ import annotations

import pandas as pd

from 今週の予想.mark_tickets import RULE
from 今週の予想.ticket_rules import UPSET_TRIO_LABELS

from 印の成績.ticket_payouts import PAYOUT

#: 期間の名前（探索 = 2019〜2024年、確認 = 2025年から）。研究 docs/04 の表と同じ分け方。
EXPLORE, CONFIRM = "探索（2019〜2024年）", "確認（2025年から）"
CONFIRM_FROM = pd.Timestamp("2025-01-01")
#: 表に並べる券種。
TICKET_TYPES: tuple[str, ...] = ("単勝", "複勝", "枠連", "馬連", "馬単", "ワイド", "3連複", "3連単")
#: 消を使う買い方（買い方の名前に「消」を含む、消を除いて組む 3連複の全部。docs/04 の 5.2 の表と同じ数え方）、
#: そのうち実際に買う3つ（中荒れ・大荒れ・超荒れ。固いの行は比べる行）、全部の合計（買い目の表の全部の行）。
DANGER_RULES, DANGER_BOUGHT, TOTAL = "消を使う買い方", "消を使う買い方（実際に買う3つ）", "全部の合計"
GROUPS: tuple[str, ...] = (*TICKET_TYPES, DANGER_RULES, DANGER_BOUGHT, TOTAL)
#: 結果の列。
COLUMNS: tuple[str, ...] = ("group", "span", "races", "hits", "stake", "paid", "hit_rate", "return_rate")


class TicketMetrics:
    """買う買い目（1行 = 1点。列 ``race_id``・``race_date``・``rule``・``ticket_type``・``stake_units``・``payout``）から、
    組（``GROUPS``）× 区切り（探索・確認・年）ごとの買ったレース数・当たったレース数・投資・払戻・的中率・回収率を数える。

    1点 100円 × 単位で数える（単位は買い目の表のまま）。的中率 = 1点でも当たったレース ÷ 買ったレース。研究 docs/04 の 5.2 の表と同じ数え方。
    """

    def of(self, tickets: pd.DataFrame) -> pd.DataFrame:
        dates = pd.to_datetime(tickets["race_date"])
        table = tickets.assign(_period=(dates >= CONFIRM_FROM).map({True: CONFIRM, False: EXPLORE}), _year=dates.dt.year.astype(str),
                               _stake=tickets["stake_units"].astype(float) * 100.0,
                               _paid=tickets["stake_units"].astype(float) * tickets[PAYOUT].astype(float))
        rows = []
        for group in GROUPS:
            part = table[self._mask(table, group)]
            for span_column in ("_period", "_year"):
                for span, rows_of in part.groupby(span_column, sort=True):
                    rows.append(self._row(group, str(span), rows_of))
        return pd.DataFrame(rows, columns=list(COLUMNS))

    @staticmethod
    def _mask(table: pd.DataFrame, group: str) -> pd.Series:
        if group == TOTAL:
            return pd.Series(True, index=table.index)
        if group == DANGER_RULES:
            return table[RULE].str.contains("消", regex=False)
        if group == DANGER_BOUGHT:
            return table[RULE].isin(UPSET_TRIO_LABELS)
        return table["ticket_type"] == group

    @staticmethod
    def _row(group: str, span: str, part: pd.DataFrame) -> list:
        races = part["race_id"].nunique()
        hits = part.loc[part[PAYOUT] > 0, "race_id"].nunique()
        stake, paid = float(part["_stake"].sum()), float(part["_paid"].sum())
        return [group, span, races, hits, stake, paid, hits / races if races else float("nan"), paid / stake if stake else float("nan")]
