"""買い方の候補を組の表に当てはめ、年ごとの回収率（各年を残りの年で当てはめた未見）、90% の幅、最高の1点を除く回収率、
前の年だけで当てはめた回収率を表にし、採用の基準を満たすかを印で示す。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from 共通.render import Table
from 地方の推奨買目.position_model import EV, PROBABILITY

from ..case_report import CaseReport
from ..positions.ticket_summary import TicketSummary
from .rule import QuinellaTrioRule
from .ticket_tables_builder import EV_FORWARD, P_FORWARD

#: 採用の基準。
MIN_YEAR_PAYBACK = 1.0          # 各年の回収率
MIN_RANGE_LOW = 0.95            # 全部の年の 90% の幅の下
MIN_WITHOUT_BEST = 1.0          # 全部の年で最高の1点を除いた回収率
MIN_FORWARD = 1.0               # 前の年だけで当てはめた各年の回収率
_YEN = 100
COLUMNS: tuple[str, ...] = ("券種", "買い方", "2024年", "2025年", "2026年", "合計", "90%の幅", "最高の1点を除く", "前の年 2025", "前の年 2026",
                            "1日の点数", "的中率", "判定")


@dataclass(frozen=True)
class RuleResult:
    rule: QuinellaTrioRule
    row: dict
    passed: bool


class RuleStudy:
    """``tables`` は券種 → 組の表。``upsets`` は券種 → 荒れ具合の予測（``race_id``・列）。無ければ荒れ具合の条件は効かない。"""

    def __init__(self, tables: dict[str, pd.DataFrame], upsets: dict[str, pd.DataFrame] | None = None) -> None:
        self._tables = {ticket: self._with_upset(table, (upsets or {}).get(ticket)) for ticket, table in tables.items()}
        self._summary = TicketSummary()

    def evaluate(self, rules: Sequence[QuinellaTrioRule]) -> list[RuleResult]:
        return [self._evaluate(rule) for rule in rules]

    def write(self, out_dir, name: str, heading: str, intro: str, results: Sequence[RuleResult]) -> None:
        rows = [result.row for result in results]
        passed = sum(1 for result in results if result.passed)
        table = Table.from_records(rows, COLUMNS, title="買い方ごとの成績",
                                  note=f"候補 {len(rows)} 件のうち基準を満たしたのは {passed} 件。回収率は各年を残りの年で当てはめた未見の成績。"
                                       f"基準: 各年 {MIN_YEAR_PAYBACK:.0%} 超、90% の幅の下 {MIN_RANGE_LOW:.0%} 以上、最高の1点を除いても {MIN_WITHOUT_BEST:.0%} 以上、"
                                       f"前の年だけで当てはめた 2025・2026年も {MIN_FORWARD:.0%} 超。")
        CaseReport(out_dir).write(name, heading, intro, [table])

    def _evaluate(self, rule: QuinellaTrioRule) -> RuleResult:
        table = self._tables[rule.ticket]
        chosen = rule.choose(table)
        races = table.groupby("race_id")[["race_date"]].first().reset_index()
        years = sorted(table["year"].unique())
        by_year = {year: self._payback(chosen[chosen["year"] == year]) for year in years}
        picked = chosen.drop(columns=["race_date"])   # 成績の部品が開催日を自分で付けるので、組の表の開催日は渡さない
        total = self._summary.row(rule.ticket, rule.label, "全部", picked, races[races["race_id"].isin(chosen["race_id"])] if len(chosen) else races.iloc[0:0])
        forward = {year: self._forward(rule, table[table["year"] == year]) for year in years if year > years[0]}
        hit_rate = total["的中率"]
        row = {
            "券種": rule.ticket, "買い方": rule.label,
            **{f"{year}年": f"{by_year[year]:.1%}（{len(chosen[chosen['year'] == year]):,}点）" for year in years},
            "合計": total["回収率"], "90%の幅": total["回収率の90%の幅"], "最高の1点を除く": total["最高の1点を除く回収率"],
            **{f"前の年 {year}": f"{forward[year]:.1%}" for year in forward},
            "1日の点数": f"{len(chosen) / max(table['race_date'].nunique(), 1):.1f}", "的中率": hit_rate,
        }
        passed = self._passes(by_year, total, forward)
        row["判定"] = "採用候補" if passed else ""
        return RuleResult(rule, row, passed)

    def _forward(self, rule: QuinellaTrioRule, table: pd.DataFrame) -> float:
        """前の年だけで当てはめた確率・期待値で選んだときの回収率。"""
        swapped = table.assign(**{PROBABILITY: table[P_FORWARD], EV: table[EV_FORWARD]}).dropna(subset=[PROBABILITY])
        return self._payback(rule.choose(swapped))

    def _passes(self, by_year: dict, total: dict, forward: dict) -> bool:
        if not by_year or any(value <= MIN_YEAR_PAYBACK for value in by_year.values()):
            return False
        low = self._percent(total["回収率の90%の幅"].split("〜")[0]) if "〜" in total["回収率の90%の幅"] else 0.0
        without_best = self._percent(total["最高の1点を除く回収率"])
        return low >= MIN_RANGE_LOW and without_best >= MIN_WITHOUT_BEST and all(value > MIN_FORWARD for value in forward.values())

    @staticmethod
    def _payback(chosen: pd.DataFrame) -> float:
        return float(chosen["payout"].sum() / (len(chosen) * _YEN)) if len(chosen) else 0.0

    @staticmethod
    def _percent(text: str) -> float:
        try:
            return float(text.strip().rstrip("%")) / 100.0
        except ValueError:
            return 0.0

    @staticmethod
    def _with_upset(table: pd.DataFrame, upset: pd.DataFrame | None) -> pd.DataFrame:
        if upset is None:
            return table
        columns = [column for column in upset.columns if column.endswith("の確率")]
        keyed = upset.assign(race_id=upset["race_id"].astype("int64"))[["race_id", *columns]].drop_duplicates("race_id")
        return table.merge(keyed, on="race_id", how="left")
