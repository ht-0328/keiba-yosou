"""精算した買い目を、買い方 × 券種 × 年ごとにまとめる。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.betting import TicketType

from .column_names import HIT, PAYOUT, RACE_ID, RULE, STAKE, TICKET_TYPE, YEAR

#: 全部の年を合わせた行の、年の列の値。
TOTAL_YEAR = "合計"
#: まとめの表の列（設計書 16 の 7. の表2）。
SUMMARY_RULE = "買い方"
SUMMARY_TICKET_TYPE = "券種"
SUMMARY_YEAR = "年"
BET_RACES = "買ったレース"
POINTS = "点数"
STAKE_TOTAL = "賭け金（円）"
PAYOUT_TOTAL = "払戻（円）"
HIT_RATE = "的中率"
RETURN_RATE = "回収率"
RETURN_RATE_WITHOUT_MAX = "最大の払戻を除いた回収率"
SUMMARY_COLUMNS: tuple[str, ...] = (
    SUMMARY_RULE, SUMMARY_TICKET_TYPE, SUMMARY_YEAR, BET_RACES, POINTS, STAKE_TOTAL, PAYOUT_TOTAL,
    HIT_RATE, RETURN_RATE, RETURN_RATE_WITHOUT_MAX,
)

_HIT_RACE = "hit_race"
_MAX_PAYOUT = "max_payout"
_GROUP = [RULE, TICKET_TYPE, YEAR]


class ReturnSummary:
    """精算した買い目を、買い方 × 券種 × 年（と、全部の年の合計）ごとにまとめる（設計書 16 の 7. の表2）。

    - 買ったレース: 1点以上買ったレースの数。点数・賭け金・払戻は合計。
    - 的中率: 1点でも当たったレース ÷ 買ったレース。回収率: 払戻 ÷ 賭け金。
    - 最大の払戻を除いた回収率: その集まりで、払戻がいちばん大きかった1レースの払戻を除いた回収率
      （1回の大きな払戻だけで 100% を超えていないかを見る）。
    """

    def table(self, settled: pd.DataFrame) -> pd.DataFrame:
        """``settled`` は ``TicketSettler.settle`` の戻り値に列 ``year``（開催年）を足した表。

        戻り値は列 ``買い方``・``券種``（単勝 など）・``年``（``2020`` のような文字列と ``合計``）・``買ったレース``・``点数``・
        ``賭け金（円）``・``払戻（円）``・``的中率``・``回収率``・``最大の払戻を除いた回収率`` の表。
        並びは買い方（出てきた順）→ 券種（単勝〜3連単）→ 年（古い順、最後に合計）。
        """
        races = self._per_race(settled)
        by_year = self._summarize(races)
        total = self._summarize(races.assign(**{YEAR: TOTAL_YEAR}))
        summary = pd.concat([by_year, total], ignore_index=True)
        return self._ordered(summary, list(dict.fromkeys(settled[RULE])))

    def _per_race(self, settled: pd.DataFrame) -> pd.DataFrame:
        """1行 = 買い方 × 券種 × 年 × レース にまとめる（点数・賭け金・払戻・当たったか）。"""
        rows = settled.assign(**{YEAR: settled[YEAR].astype(str)})
        return rows.groupby([*_GROUP, RACE_ID], as_index=False).agg(
            **{POINTS: (STAKE, "size"), STAKE_TOTAL: (STAKE, "sum"), PAYOUT_TOTAL: (PAYOUT, "sum"), _HIT_RACE: (HIT, "any")},
        )

    def _summarize(self, races: pd.DataFrame) -> pd.DataFrame:
        """レースごとの行を、買い方 × 券種 × 年 ごとにまとめて率を出す。"""
        grouped = races.groupby(_GROUP, as_index=False).agg(
            **{BET_RACES: (RACE_ID, "size"), POINTS: (POINTS, "sum"), STAKE_TOTAL: (STAKE_TOTAL, "sum"),
               PAYOUT_TOTAL: (PAYOUT_TOTAL, "sum"), _HIT_RACE: (_HIT_RACE, "sum"), _MAX_PAYOUT: (PAYOUT_TOTAL, "max")},
        )
        grouped[HIT_RATE] = grouped[_HIT_RACE] / grouped[BET_RACES]
        grouped[RETURN_RATE] = grouped[PAYOUT_TOTAL] / grouped[STAKE_TOTAL]
        grouped[RETURN_RATE_WITHOUT_MAX] = (grouped[PAYOUT_TOTAL] - grouped[_MAX_PAYOUT]) / grouped[STAKE_TOTAL]
        return grouped

    def _ordered(self, summary: pd.DataFrame, rules: list[str]) -> pd.DataFrame:
        """買い方 → 券種 → 年 の順に並べ、見出しを日本語にする。"""
        type_order = {ticket_type.key: position for position, ticket_type in enumerate(TicketType)}
        labels = {ticket_type.key: ticket_type.label for ticket_type in TicketType}
        ordered = summary.assign(
            _rule=summary[RULE].map({rule: position for position, rule in enumerate(rules)}),
            _type=summary[TICKET_TYPE].map(type_order),
            _total=summary[YEAR] == TOTAL_YEAR,
        ).sort_values(["_rule", "_type", "_total", YEAR])
        renamed = ordered.assign(**{TICKET_TYPE: ordered[TICKET_TYPE].map(labels)}).rename(
            columns={RULE: SUMMARY_RULE, TICKET_TYPE: SUMMARY_TICKET_TYPE, YEAR: SUMMARY_YEAR},
        )
        return renamed[list(SUMMARY_COLUMNS)].reset_index(drop=True)
