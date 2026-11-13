"""抑えの買い目の成績（的中率・回収率）を、本線（今の印の 3連複・3連単）と、本線＋抑えと並べる表。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from ..tables.cells import percent
from .evaluation_frame import CONFIRM, EXPLORE

_NOTE = ("1点 100円で数える（本線は道具「印の成績」の単位どおり）。的中率 = 1点でも当たったレース ÷ 買ったレース。回収率 = 払戻 ÷ 投資。"
         "本線は 3連複（◎−○▲☆−○▲△☆）と 3連単（◎→○▲☆→○▲△☆）の元の買い目。本線＋抑えの的中率は、本線を買ったレースのうちどちらかが当たった割合。")


@dataclass(frozen=True)
class HedgeTable:
    """``hedges`` は（作り方の名前 → 払戻を付けた抑えの買い目）、``main`` は払戻を付けた本線の買い目（race_id・period・unit・payout）。"""

    def build(self, hedges: dict[str, pd.DataFrame], main: pd.DataFrame, title: str) -> Table:
        rows = []
        for period in (EXPLORE, CONFIRM):
            base = main.loc[main["period"] == period]
            rows.append(["本線（今の印の 3連複・3連単）", period, *self._cells(base, base["unit"])])
            for name, tickets in hedges.items():
                part = tickets.loc[tickets["period"] == period].assign(unit=1.0)
                rows.append([f"抑え {name}", period, *self._cells(part, part["unit"])])
                both = pd.concat([base[["race_id", "unit", "payout"]], part[["race_id", "unit", "payout"]]])
                rows.append([f"本線＋抑え {name}", period, *self._cells(both, both["unit"])])
        columns = ["買い方", "期間", "買ったレース", "点数", "当たったレース", "的中率", "投資（円）", "払戻（円）", "回収率"]
        return Table(columns, rows, title=title, note=_NOTE)

    @staticmethod
    def _cells(tickets: pd.DataFrame, unit: pd.Series) -> list[object]:
        if tickets.empty:
            return [0, 0, 0, "", 0, 0, ""]
        stake = float((unit * 100).sum())
        paid = float((tickets["payout"] * unit).sum())
        hit_races = tickets.loc[tickets["payout"] > 0, "race_id"].nunique()
        races = tickets["race_id"].nunique()
        return [races, len(tickets), hit_races, percent(hit_races, races), int(stake), int(paid), percent(paid, stake)]
