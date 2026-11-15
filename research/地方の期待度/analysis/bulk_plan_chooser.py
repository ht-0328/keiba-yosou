"""本番の推奨買目の買い方（``RECOMMENDED_PLANS``）を、たくさんのレースの組の表にまとめて当てはめる。

本番の ``Recommender`` は1レースずつ選ぶので、頭数の線・組の形・荒れ具合の線・1レースの点数の上限を、ここではレースごとに引く。"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd

from 地方の推奨買目.combo_forms import FORM
from 地方の推奨買目.position_model import EV
from 地方の推奨買目.ticket_plan import TicketPlan

#: 荒れ具合の列（レースの中荒れ以上の確率）。
UPSET = "upset"


class BulkPlanChooser:
    """``choose(plan, table)`` は、組の表（``race_id``・``field_size``・``P``・``odds``（か ``odds_lo``・``odds_hi``）・``payout``、
    形を問う買い方は ``form``、荒れ具合の条件のある買い方は ``upset``）から、本番と同じ決まりで買う組を選ぶ。"""

    def choose(self, plan: TicketPlan, table: pd.DataFrame) -> pd.DataFrame:
        table = table[table["field_size"] >= plan.min_heads]
        if plan.upset_min > 0:
            table = table[table[UPSET].notna() & (table[UPSET] >= plan.upset_min)]
        if plan.form and FORM not in table.columns:
            raise ValueError(f"{plan.ticket} の買い方は組の形を問うので、表に {FORM} の列が要る")
        chosen = replace(plan, top_k=0).choose(table)
        if plan.top_k:
            chosen = chosen.sort_values(EV, ascending=False, kind="stable").groupby("race_id", sort=False).head(plan.top_k)
        return chosen.reset_index(drop=True)
