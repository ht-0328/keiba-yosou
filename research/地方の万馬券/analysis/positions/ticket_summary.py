"""買い目の成績: 選んだ組（確率・払戻つき）を期間ごとに、投資・払戻・回収率（と開催日のブートストラップの 90% の幅）・的中・落ち込みにまとめる。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .position_model import PROBABILITY

_YEN_PER_POINT = 100
_MAN, _JUMAN = 10_000, 100_000
_BOOTSTRAP_DRAWS = 1000
_SEED = 7
SUMMARY_COLUMNS: tuple[str, ...] = ("券種", "買い方", "期間", "対象レース", "買ったレース", "点数", "1日の投資", "投資", "払戻", "回収率", "回収率の90%の幅",
                                    "最高の1点を除く回収率", "的中", "的中レース", "的中率", "的中の実際÷見込み", "万馬券の的中", "10万馬券の的中", "最高配当",
                                    "勝った日の割合", "最大の落ち込み")


@dataclass(frozen=True)
class TicketSummary:
    """``row(ticket, plan, period, chosen, races)`` は1行の辞書。``chosen`` は ``race_id``・``P``・``payout``、``races`` は対象レース（``race_id``・``race_date``）。"""

    def row(self, ticket: str, plan: str, period: str, chosen: pd.DataFrame, races: pd.DataFrame) -> dict:
        points = len(chosen)
        invested = points * _YEN_PER_POINT
        returned = int(chosen["payout"].sum()) if points else 0
        best = int(chosen["payout"].max()) if points else 0
        hits = int((chosen["payout"] > 0).sum()) if points else 0
        expected = float(chosen[PROBABILITY].sum()) if points else 0.0
        by_race = chosen.groupby("race_id")["payout"].sum() if points else pd.Series(dtype=float)
        by_day = self._by_day(chosen, races)
        low, high = self._bootstrap_range(by_day)
        return {
            "券種": ticket, "買い方": plan, "期間": period, "対象レース": int(races["race_id"].nunique()), "買ったレース": int(chosen["race_id"].nunique()) if points else 0,
            "点数": points, "1日の投資": f"{by_day['invest'].mean():,.0f}円" if len(by_day) else "—",
            "投資": f"{invested:,}円", "払戻": f"{returned:,}円", "回収率": f"{returned / invested:.1%}" if invested else "—",
            "回収率の90%の幅": f"{low:.0%}〜{high:.0%}" if invested else "—",
            "最高の1点を除く回収率": f"{(returned - best) / invested:.1%}" if invested else "—",
            "的中": hits, "的中レース": int((by_race > 0).sum()) if points else 0, "的中率": f"{(by_race > 0).mean():.1%}" if points else "—",
            "的中の実際÷見込み": f"{hits / expected:.2f}" if expected > 0 else "—",
            "万馬券の的中": int((chosen["payout"] >= _MAN).sum()) if points else 0, "10万馬券の的中": int((chosen["payout"] >= _JUMAN).sum()) if points else 0,
            "最高配当": f"{best:,}円" if points else "—",
            "勝った日の割合": f"{(by_day['profit'] > 0).mean():.0%}" if len(by_day) else "—",
            "最大の落ち込み": f"{self._max_drawdown(by_day):+,.0f}円" if len(by_day) else "—",
        }

    def monthly(self, chosen: pd.DataFrame, races: pd.DataFrame) -> pd.DataFrame:
        """月ごとの点数・的中・回収率・損益（``race_date`` は ``races`` から）。"""
        table = chosen.merge(races[["race_id", "race_date"]], on="race_id", how="left")
        month = pd.to_datetime(table["race_date"]).dt.to_period("M").astype(str)
        g = table.groupby(month).agg(点数=("payout", "size"), 的中=("payout", lambda s: int((s > 0).sum())), 払戻=("payout", "sum"))
        g["投資"] = g["点数"] * _YEN_PER_POINT
        g["回収率"] = g["払戻"] / g["投資"]
        g["損益"] = g["払戻"] - g["投資"]
        return g.reset_index().rename(columns={"race_date": "月"})

    def _by_day(self, chosen: pd.DataFrame, races: pd.DataFrame) -> pd.DataFrame:
        if chosen.empty:
            return pd.DataFrame(columns=["points", "payout", "invest", "profit"])
        table = chosen.merge(races[["race_id", "race_date"]], on="race_id", how="left")
        by_day = table.groupby("race_date").agg(points=("payout", "size"), payout=("payout", "sum")).sort_index()
        by_day["invest"] = by_day["points"] * _YEN_PER_POINT
        by_day["profit"] = by_day["payout"] - by_day["invest"]
        return by_day

    def _bootstrap_range(self, by_day: pd.DataFrame) -> tuple[float, float]:
        if by_day.empty:
            return float("nan"), float("nan")
        rng = np.random.default_rng(_SEED)
        picks = rng.integers(0, len(by_day), size=(_BOOTSTRAP_DRAWS, len(by_day)))
        invested = by_day["invest"].to_numpy()[picks].sum(axis=1)
        returned = by_day["payout"].to_numpy()[picks].sum(axis=1)
        ratio = returned / np.clip(invested, 1, None)
        return float(np.percentile(ratio, 5)), float(np.percentile(ratio, 95))

    def _max_drawdown(self, by_day: pd.DataFrame) -> float:
        cumulative = by_day["profit"].cumsum()
        return float((cumulative - cumulative.cummax()).min())
