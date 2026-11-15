"""印の買い目の研究の流れ: 印の組の表で、買い方の候補ごとに年ごとの成績を出し、採用の基準に照らして Markdown に書く。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from 共通.render import Table

from 地方の万馬券.analysis.case_report import CaseReport

from .mark_plan import MarkPlan
from .mark_table_builder import LEAVE_ONE_OUT
from .plan_catalog import plan_catalog
from .plan_summary import SUMMARY_COLUMNS, PlanSummary

REPORT_NAME = "印の買い目の成績"
_ALL_YEARS = "全部の年"


@dataclass(frozen=True)
class MarkStudy:
    """``table`` は印の組の表（``MarkTableBuilder``）。採用の基準: 各年の回収率が 100% を超え、各年の最高の1点を除いても 100% 以上。"""

    table: pd.DataFrame
    plans: tuple[MarkPlan, ...] = field(default_factory=plan_catalog)
    #: 当てはめ方（報告の名前と説明に使う）。
    protocol: str = LEAVE_ONE_OUT

    def rows(self) -> list[dict]:
        summary = PlanSummary()
        years = sorted(self.table["year"].unique())
        rows = []
        for plan in self.plans:
            chosen = plan.choose(self.table)
            for year in years:
                races = int(self.table.loc[(self.table["year"] == year) & (self.table["field_size"] >= plan.min_heads), "race_id"].nunique())
                rows.append(summary.row(plan.label, f"{year}年", chosen[chosen["year"] == year], races))
            rows.append(summary.row(plan.label, _ALL_YEARS, chosen, int(self.table.loc[self.table["field_size"] >= plan.min_heads, "race_id"].nunique())))
            print(f"{plan.label}: {rows[-1]['回収率']}", flush=True)
        return rows

    def write(self, out_dir: Path) -> Path:
        rows = self.rows()
        years = [f"{year}年" for year in sorted(self.table["year"].unique())]
        tables = [self._year_table(rows, years),
                  Table.from_records(rows, SUMMARY_COLUMNS, title="2. 買い方ごと・年ごとの成績",
                                     note="確定オッズ・確定払戻。期待値は 組の確率（各年を残りの年で当てはめた条件つきロジット）× 確定オッズ。"
                                          "点ごとは1点 100円、レースごとは1レース 5,000円を、どれが当たっても払った額の 1.1倍以上戻るように配った額（100円単位）。")]
        intro = ("対象: 2024年1月からの地方の確定レース（5頭以上。全頭の予想の当日の予測があるもの）。印は道具「印の成績」と同じ決め方（◎○▲△☆注。消は無い）。"
                 "採用の基準: 各年の回収率が 100% を超え、各年の最高の1点を除いても 100% 以上。"
                 f"組の確率の当てはめ方は「{self.protocol}」（{'各年を残りの年で当てはめた' if self.protocol == LEAVE_ONE_OUT else 'その年より前の年だけで当てはめた'}未見の値）。")
        name = REPORT_NAME if self.protocol == LEAVE_ONE_OUT else f"{REPORT_NAME}-{self.protocol}"
        return CaseReport(out_dir).write(name, f"地方の印の買い目: {name}", intro, tables)

    @staticmethod
    def _year_table(rows: list[dict], years: list[str]) -> Table:
        by_plan: dict[str, dict[str, dict]] = {}
        for row in rows:
            by_plan.setdefault(row["買い方"], {})[row["期間"]] = row
        records = []
        for plan, periods in by_plan.items():
            yearly = [periods.get(year) for year in years]
            passed = all(row and row["recovery"] > 1.0 and row["without_best"] >= 1.0 for row in yearly)
            records.append({"買い方": plan, **{year: f"{row['回収率']}（{row['点数']:,}点）" if row else "—" for year, row in zip(years, yearly, strict=True)},
                            "最高の1点を除く（年ごと）": " / ".join(row["最高の1点を除く回収率"] if row else "—" for row in yearly),
                            "全部の年": periods[_ALL_YEARS]["回収率"], "1日の投資": periods[_ALL_YEARS]["1日の投資"], "基準": "満たす" if passed else ""})
        return Table.from_records(records, ("買い方", *years, "最高の1点を除く（年ごと）", "全部の年", "1日の投資", "基準"),
                                  title="1. 買い方ごとの年ごとの回収率（括弧は点数）")
