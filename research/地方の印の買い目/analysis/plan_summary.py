"""買い方の成績: 選んだ点（``MarkPlan.choose`` の表）を、投資・払戻・回収率・最高の1点を除く回収率・的中・見込みとの比べにまとめる。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

SUMMARY_COLUMNS: tuple[str, ...] = ("買い方", "期間", "対象レース", "買ったレース", "点数", "1日の投資", "投資", "払戻", "回収率",
                                    "最高の1点を除く回収率", "的中レース", "的中率", "見込みの回収率", "勝った日の割合")


@dataclass(frozen=True)
class PlanSummary:
    """``row(label, period, chosen, races)`` は1行の辞書。``races`` は対象のレース数。数値の列（``recovery``・``without_best``）も返す。"""

    def row(self, label: str, period: str, chosen: pd.DataFrame, races: int) -> dict:
        invested = float(chosen["stake"].sum())
        returned = float(chosen["returned"].sum())
        best = float(chosen["returned"].max()) if len(chosen) else 0.0
        by_race = chosen.groupby("race_id")["returned"].sum()
        by_day = chosen.groupby("race_date").agg(stake=("stake", "sum"), returned=("returned", "sum"))
        expected = float((chosen["stake"] * chosen["ev"]).sum()) / invested if invested else float("nan")
        recovery = returned / invested if invested else float("nan")
        without_best = (returned - best) / invested if invested else float("nan")
        return {
            "買い方": label, "期間": period, "対象レース": races, "買ったレース": int(chosen["race_id"].nunique()), "点数": len(chosen),
            "1日の投資": f"{by_day['stake'].mean():,.0f}円" if len(by_day) else "—",
            "投資": f"{invested:,.0f}円", "払戻": f"{returned:,.0f}円", "回収率": _percent(recovery), "最高の1点を除く回収率": _percent(without_best),
            "的中レース": int((by_race > 0).sum()), "的中率": _percent((by_race > 0).mean()) if len(by_race) else "—",
            "見込みの回収率": _percent(expected), "勝った日の割合": _percent((by_day["returned"] > by_day["stake"]).mean()) if len(by_day) else "—",
            "recovery": recovery, "without_best": without_best,
        }


def _percent(value: float) -> str:
    return "—" if pd.isna(value) else f"{value:.1%}"
