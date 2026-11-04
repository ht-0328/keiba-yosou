"""荒れやすいレースの条件の表: レースの条件ごと・期間ごとに、万馬券（1万円以上）と 10万馬券の割合を全体と比べる。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd

from 共通.render import Table

COLUMNS: tuple[str, ...] = ("条件", "値", "期間", "レース数", "万馬券率", "全体の万馬券率", "10万馬券率", "全体の10万馬券率", "10万馬券の倍率")
_MAN, _JUMAN = 10_000, 100_000


@dataclass(frozen=True)
class RaceTheoryTable:
    """``races``（1行 = 1レース。条件の列と ``trifecta_payout``・``race_date``）から、条件の値ごとの荒れやすさを期間ごとに出す。"""

    split: date

    def build(self, races: pd.DataFrame, conditions: tuple[str, ...], *, title: str) -> Table:
        day = pd.to_datetime(races["race_date"])
        periods = {"前半": races[day < pd.Timestamp(self.split)], "後半": races[day >= pd.Timestamp(self.split)]}
        rows = []
        for condition in conditions:
            for label, rows_in in periods.items():
                rows.extend(self._rows(condition, self._period_label(rows_in, label), rows_in))
        return Table.from_records(rows, COLUMNS, title=title,
                                  note="万馬券率 = 3連単の払戻が 1万円以上のレースの割合、10万馬券率 = 10万円以上の割合。倍率 = その条件の 10万馬券率 ÷ 期間全体の 10万馬券率。")

    def _period_label(self, rows: pd.DataFrame, fallback: str) -> str:
        if rows.empty:
            return fallback
        years = pd.to_datetime(rows["race_date"]).dt.year
        return f"{years.min()}〜{years.max()}"

    def _rows(self, condition: str, label: str, rows: pd.DataFrame) -> list[dict]:
        if rows.empty:
            return []
        man_all = (rows["trifecta_payout"] >= _MAN).mean()
        juman_all = (rows["trifecta_payout"] >= _JUMAN).mean()
        out = []
        for value, group in rows.groupby(rows[condition].astype("string"), observed=True):
            juman = (group["trifecta_payout"] >= _JUMAN).mean()
            out.append({"条件": condition, "値": value, "期間": label, "レース数": len(group),
                        "万馬券率": f"{(group['trifecta_payout'] >= _MAN).mean():.1%}", "全体の万馬券率": f"{man_all:.1%}",
                        "10万馬券率": f"{juman:.1%}", "全体の10万馬券率": f"{juman_all:.1%}",
                        "10万馬券の倍率": round(juman / juman_all, 2) if juman_all else float("nan")})
        return out
