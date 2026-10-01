"""1レースの能力指数を、表（``render.Table``）にする。"""

from __future__ import annotations

import pandas as pd

from .. import card, render
from .ability_index import ABILITY, APTITUDE_COLUMNS, BASE, RUNS_USED
from .race_ability import RANK, THIS_RUN, RaceAbilityReport
from .speed_figure import FIGURE

#: 1頭ごとに並べる近走の数。
RECENT_RUNS = 5


class AbilityTables:
    """``RaceAbility`` の結果を、CLI と検索画面で同じ表にする。"""

    def ranking(self, report: RaceAbilityReport) -> render.Table:
        entries = report.entries
        columns = ["順位", "馬番", "馬名", "能力指数", "基礎の速さ", *APTITUDE_COLUMNS.values(), "使った走の数"]
        values = [RANK, "horse_no", "horse_name", ABILITY, BASE, *APTITUDE_COLUMNS.values(), RUNS_USED]
        if report.finished:
            columns += ["この走の指数", "着順"]
            values += [THIS_RUN, "finish"]
        rows = [[_cell(row[name]) for name in values] for _, row in entries.iterrows()]
        return render.Table(columns, rows, title=f"能力指数 {card.header_title(report.header)}", note=_note(report))

    def history(self, report: RaceAbilityReport) -> render.Table:
        names = report.entries.set_index("horse_id")["horse_name"]
        numbers = report.entries.set_index("horse_id")["horse_no"]
        recent = report.history.groupby("horse_id", sort=False).head(RECENT_RUNS)
        recent = recent.assign(_order=recent["horse_id"].map({h: i for i, h in enumerate(report.entries["horse_id"])}))
        recent = recent.sort_values(["_order", "race_date"], ascending=[True, False])
        rows = [[_cell(numbers[r["horse_id"]]), names[r["horse_id"]], r["race_date"].strftime("%Y-%m-%d"), r["venue"],
                 r["surface"], int(r["distance_m"]), r["condition"], r["class_name"], _cell(r["finish"]), _cell(r[FIGURE])]
                for r in recent.to_dict("records")]
        return render.Table(["馬番", "馬名", "開催日", "競馬場", "芝ダ", "距離", "馬場", "クラス", "着順", "スピード指数"], rows,
                            title=f"各馬の近{RECENT_RUNS}走のスピード指数（能力指数の順）")


def _cell(value):
    if value is None or (isinstance(value, float) and pd.isna(value)) or value is pd.NA:
        return None
    if isinstance(value, float):
        return round(value, 1)
    return int(value) if hasattr(value, "__int__") and not isinstance(value, str) else value


def _note(report: RaceAbilityReport) -> str:
    return ("能力指数 = 近走のスピード指数を、新しい走ほど・今回の条件に近い走ほど重く見た平均（80 が1勝クラスの古馬のふつうの走）。"
            "適性 = その条件の近さで重み付けした平均 − 基礎の速さ。着順・人気は使っていない。"
            "初めての芝ダの馬は、父と母の父の産駒の、初めてのその芝ダの走から馬場の適性を補う。"
            "2年以内に中央の平地の走が無い馬（新馬など）は空欄。")
