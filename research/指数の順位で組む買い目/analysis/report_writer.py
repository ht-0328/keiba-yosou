"""成績の表を markdown に書く（reports 向けの実額つきと、docs 向けの割合・件数だけ）。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 共通 import render
from 共通.render import Table

from .baseline_summary import BASELINE_RULES
from .formation_catalog import FormationCatalog
from .period import CONFIRM, EXPLORE, PERIODS
from .period_table import PeriodTable
from .rank_table import RANKINGS
from .row_spec import RowSpec
from .summary_table import SummaryTable
from .yearly_table import YearlyTable

#: 書くファイルの名前。
FULL_NAME = "成績.md"
DOCS_NAME = "docs向けの表.md"
#: 要約の表に並べる期間（探索と確認）。
_SUMMARY_PERIODS = (EXPLORE, CONFIRM)
_NOTE = ("1点 100円。順位はレースの中で走った馬を確率の高い順に並べたもの（出走取消・除外は入れない）。頭数が足りずに存在しない順位の組は買わない。"
         "払戻は確定のもの。回収率の 90% の幅は開催日を単位にしたブートストラップ。集計金額を満たした的中の割合は、的中したレースのうち"
         "1レースの払戻（形の全部の点の合計）がサイトの集計金額以上だったものの割合。")
_BASELINE_NOTE = ("道具「印の成績」の買い目の CSV から、設計書「買うレースと買い目を決める」08 の 2 の形（単勝・複勝・ワイド・馬連・馬単・元の3連複・元の3連単）の、"
                  "トリガミとオッズ無しを除いた買い目をレースごとにまとめたもの。複勝はその CSV を書いた時点の決まり（期待値 1.25 以上）。")


class ReportWriter:
    """精算の表（``ResultStore.load_settled``）と比べる相手（``ResultStore.load_baselines``）から、
    時点 × 順位の決め方ごとの 形 × 期間の成績・要約（探索と確認を1行に）・年ごとの回収率・年ごとの的中率と、比べる相手の同じ表を markdown に書く。

    ``成績.md`` は投資・払戻の実額つき（Git 対象外の reports に置く）、``docs向けの表.md`` は実額を省いたもの（docs に貼る）。
    """

    def write(self, settled: pd.DataFrame, baselines: dict[str, pd.DataFrame], out_dir: Path) -> tuple[Path, Path]:
        full = self._tables(settled, baselines, with_yen=True)
        docs = self._tables(settled, baselines, with_yen=False)
        out_dir.mkdir(parents=True, exist_ok=True)
        full_path, docs_path = out_dir / FULL_NAME, out_dir / DOCS_NAME
        render.write(render.render(full, "markdown"), full_path, fmt="markdown")
        render.write(render.render(docs, "markdown"), docs_path, fmt="markdown")
        return full_path, docs_path

    def _tables(self, settled: pd.DataFrame, baselines: dict[str, pd.DataFrame], with_yen: bool) -> list[Table]:
        specs = FormationCatalog.row_specs()
        tables: list[Table] = []
        for timing in self._timings(settled):
            for ranking in RANKINGS:
                chosen = settled[(settled["timing"] == timing) & (settled["ranking"] == ranking)]
                if chosen.empty:
                    continue
                head = f"{timing}・{ranking}"
                span = f"{pd.to_datetime(chosen['race_date']).min():%Y-%m-%d} 〜 {pd.to_datetime(chosen['race_date']).max():%Y-%m-%d}"
                tables.append(PeriodTable(specs, PERIODS, with_yen).table(
                    chosen, f"{head}: 形 × 期間ごとの成績", f"レース {chosen['race_id'].nunique():,}（{span}）。{_NOTE}"))
                tables.append(SummaryTable(specs, _SUMMARY_PERIODS).table(chosen, f"{head}: 要約（探索と確認）", "上の表の探索と確認の回収率と的中率を1行に並べたもの。"))
                tables += YearlyTable(specs).tables(chosen, f"{head}:")
        for timing, baseline in baselines.items():
            if baseline.empty:
                continue
            present = set(baseline["formation"].astype(str))
            base_specs = [RowSpec(rule, ticket, (rule,)) for rule, ticket in BASELINE_RULES.items() if rule in present]
            base_specs.append(RowSpec("今の印の買い目の合計（7つの買い方）", "7券種", tuple(rule for rule in BASELINE_RULES if rule in present)))
            span = f"{pd.to_datetime(baseline['race_date']).min():%Y-%m-%d} 〜 {pd.to_datetime(baseline['race_date']).max():%Y-%m-%d}"
            head = f"比べる相手（{timing}）"
            tables.append(PeriodTable(base_specs, PERIODS, with_yen).table(
                baseline, f"{head}: 今の印の買い目の 買い方 × 期間ごとの成績", f"レース {baseline['race_id'].nunique():,}（{span}）。{_BASELINE_NOTE}"))
            tables.append(SummaryTable(base_specs, _SUMMARY_PERIODS).table(baseline, f"{head}: 要約（探索と確認）"))
            tables += YearlyTable(base_specs).tables(baseline, f"{head}:")
        return tables

    @staticmethod
    def _timings(settled: pd.DataFrame) -> list[str]:
        order = {"当日": 0, "前日": 1}
        return sorted(settled["timing"].unique().tolist(), key=lambda label: order.get(label, 9))
