"""採用した組の期待値の買い方の、運用の目安（何レース・何点・何円・いちばん深い落ち込み）を出す。"""

from __future__ import annotations

import pandas as pd


class ComboOperationReport:
    """道具「印の成績」の買い目の CSV のうち、実際に買う買い方（``weights``: 買い方の名前 → 1点の重み。例 馬連 1・馬単 2）の行から、
    運用の目安を文にする（1点の重みが 1 のとき 100円で数える）。

    出すもの: 買ったレースの数と1開催日あたり、1レースの点数の分け方、1日の投資、回収率、いちばん深い落ち込みと、
    それを財布の 15%（止まりの線 70% までの半分）に収める財布の額、いちばん長い連敗（当たらなかったレースが続いた数）、年ごとの表。
    """

    def lines(self, tickets: pd.DataFrame, weights: dict[str, float], days: int) -> list[str]:
        bought = tickets[tickets["買い方"].isin(tuple(weights)) & tickets["外した理由"].fillna("").eq("")].copy()
        bought["金額"] = bought["買い方"].map(weights) * 100.0
        bought["払戻"] = bought["払戻（100円あたり）"].astype(float) * bought["金額"] / 100.0
        bought = bought.sort_values(["開催日", "レースID"], kind="stable")
        per_race = bought.groupby("レースID").size()
        shares = per_race.value_counts(normalize=True).sort_index()
        daily = bought.groupby("開催日")["金額"].sum()
        profit = (bought["払戻"] - bought["金額"]).cumsum()
        drawdown = float((profit.cummax().clip(lower=0) - profit).max())
        return [
            f"- 買うレース: {per_race.size:,}（開催日 {days} 日に平均 {per_race.size / days:.1f} レース。買った日の最大 "
            f"{bought.groupby('開催日')['レースID'].nunique().max()} レース）",
            "- 1レースの点数: " + "・".join(f"{points}点 {share * 100:.1f}%" for points, share in shares.head(6).items())
            + f"（平均 {per_race.mean():.2f} 点・最大 {per_race.max()} 点）",
            f"- 1日の投資: 平均 {daily.sum() / days:,.0f}円・最大 {daily.max():,.0f}円",
            f"- 回収率: {bought['払戻'].sum() / bought['金額'].sum() * 100:.1f}%",
            f"- いちばん深い落ち込み: {drawdown:,.0f}円（財布の 15% に収める財布の額 {drawdown / 0.15:,.0f}円）",
            f"- いちばん長い連敗: {self._longest_miss(bought)} レース",
        ]

    def yearly(self, tickets: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
        bought = tickets[tickets["買い方"].isin(tuple(weights)) & tickets["外した理由"].fillna("").eq("")].copy()
        bought["金額"] = bought["買い方"].map(weights) * 100.0
        bought["払戻"] = bought["払戻（100円あたり）"].astype(float) * bought["金額"] / 100.0
        table = bought.groupby(pd.to_datetime(bought["開催日"]).dt.year).agg(
            レース=("レースID", "nunique"), 点数=("レースID", "size"), 投資=("金額", "sum"), 払戻=("払戻", "sum"))
        table["回収率"] = (table["払戻"] / table["投資"] * 100).round(1)
        table["損益"] = table["払戻"] - table["投資"]
        return table

    def _longest_miss(self, bought: pd.DataFrame) -> int:
        paid = bought.groupby("レースID", sort=False)["払戻"].sum().to_numpy()
        longest = current = 0
        for value in paid:
            current = current + 1 if value == 0 else 0
            longest = max(longest, current)
        return longest
