"""裏を足すかの比べ: 今の印の買い目（単勝・馬単・3連単。レースごと・見込み 1.0 以上）と、裏の当たる確率が線以上のレースだけ馬単の裏を足した形を、
年ごとの回収率・最高の1点を除いた回収率・1日の儲け・的中率で比べる。"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from 共通.render import Table

from 地方の万馬券.analysis.case_report import CaseReport

from .mark_plan import PER_RACE, MarkPlan
from .mark_table_builder import LEAVE_ONE_OUT
from .plan_catalog import LOCAL_RULES
from .reverse_combos import REVERSE_RULE
from .reverse_probabilities import REVERSE_PROBABILITY, ReverseProbabilities

REPORT_NAME = "裏を買うかの成績"
#: 比べる裏の確率の線。
LINES: tuple[float, ...] = (0.20, 0.25, 0.30, 0.35, 0.40)
_COLUMNS: tuple[str, ...] = ("形", "年", "買ったレース", "裏を足したレース", "投資", "払戻", "回収率", "最高の1点を除く回収率", "的中率", "1日の儲け", "今のままとの差（1日の儲け）")


@dataclass(frozen=True)
class ReverseStudy:
    """``table`` は印の組の表（``MarkTableBuilder``。馬単の裏の行つき）、``marked`` は印の全頭の表（``MarkedTable``）。"""

    table: pd.DataFrame
    marked: pd.DataFrame
    protocol: str = LEAVE_ONE_OUT
    lines: tuple[float, ...] = field(default=LINES)

    def write(self, out_dir: Path) -> Path:
        probabilities = ReverseProbabilities().of(self.marked, self.protocol)
        years = sorted(self.table["year"].unique())
        probabilities = probabilities[probabilities["year"].isin(years)]
        days = self.table.groupby("year")["race_date"].nunique()
        base = MarkPlan("今のまま", LOCAL_RULES, PER_RACE).choose(self.table)
        rows = self._rows("今のまま（単勝・馬単・3連単）", base, years, days, base)
        for line in self.lines:
            chosen_races = set(probabilities.loc[probabilities[REVERSE_PROBABILITY] >= line, "race_id"])
            table = self.table[(self.table["rule"] != REVERSE_RULE) | self.table["race_id"].isin(chosen_races)]
            plan = MarkPlan(f"裏 {line:.2f} 以上", (*LOCAL_RULES, REVERSE_RULE), PER_RACE)
            rows += self._rows(f"裏の確率 {line:.2f} 以上 → 馬単の裏を足す", plan.choose(table), years, days, base)
            print(f"線 {line:.2f}: 済み", flush=True)
        tables = [Table.from_records(ReverseProbabilities.quality(probabilities), ("年", "レース", "裏が当たった割合", "予想の平均", "ログ損失", "AUC"),
                                     title="1. 裏の当たる確率のモデルの当たり具合（学びに使わなかった年）"),
                  Table.from_records(rows, _COLUMNS, title="2. 今のままと、裏を足した形の年ごとの成績",
                                     note="1レース 5,000円を、どの組が当たっても払った額の 1.1倍以上戻るように配り、見込みの回収率 1.0 以上のレースだけ買う。"
                                          "1日の儲けは、その年の開催日1日あたりの（払戻 − 投資）。確定オッズ・確定払戻。")]
        intro = (f"裏の当たる確率のモデルと組の確率の当てはめ方は「{self.protocol}」。採用の基準: どの年も、回収率と1日の儲けが今のままを上回り、"
                 "最高の1点を除いた回収率も 100% 以上。")
        name = REPORT_NAME if self.protocol == LEAVE_ONE_OUT else f"{REPORT_NAME}-{self.protocol}"
        return CaseReport(out_dir).write(name, f"地方の印の買い目: {name}", intro, tables)

    @staticmethod
    def _rows(label: str, chosen: pd.DataFrame, years: list[int], days: pd.Series, base: pd.DataFrame) -> list[dict]:
        rows = []
        for year in years:
            part = chosen[chosen["year"] == year]
            base_part = base[base["year"] == year]
            stake, returned = float(part["stake"].sum()), float(part["returned"].sum())
            profit = (returned - stake) / days[year]
            base_profit = (float(base_part["returned"].sum()) - float(base_part["stake"].sum())) / days[year]
            by_race = part.groupby("race_id")["returned"].sum()
            rows.append({"形": label, "年": f"{year}年", "買ったレース": int(part["race_id"].nunique()),
                         "裏を足したレース": int(part.loc[part["rule"] == REVERSE_RULE, "race_id"].nunique()),
                         "投資": f"{stake:,.0f}円", "払戻": f"{returned:,.0f}円", "回収率": f"{returned / stake:.1%}",
                         "最高の1点を除く回収率": f"{(returned - part['returned'].max()) / stake:.1%}",
                         "的中率": f"{(by_race > 0).mean():.1%}", "1日の儲け": f"{profit:+,.0f}円",
                         "今のままとの差（1日の儲け）": f"{profit - base_profit:+,.0f}円"})
        return rows
