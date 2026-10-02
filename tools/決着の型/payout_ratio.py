"""馬単の払戻 ÷ 馬連の払戻 の分布（同じレースの、同じ2頭の組で比べる）。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from 決着の型.pattern_settlement import TOTAL_LABEL

COLUMNS: tuple[str, ...] = ("開催年", "決着", "レース数", "比の中央値", "比の平均", "比の下位4分の1", "比の上位4分の1", "1.5〜2.5倍に収まる割合")
#: 「約2倍」と見なす比の幅。
RATIO_BAND = (1.5, 2.5)
_ORDER_LABELS = {True: "人気上位が1着", False: "人気下位が1着"}
_ALL_LABEL = "全部"


class PayoutRatio:
    """馬単と馬連がそれぞれ1つの組だけ払い戻されたレース（同着を除く）で、馬単 ÷ 馬連 を数える。

    決着を「人気上位が1着」（1着馬の人気が2着馬より上）と「人気下位が1着」に分けても出す。
    馬単の比は、人気上位が勝つと 2倍を下回り、人気下位が勝つと 2倍を上回りやすい。
    """

    def ratios(self, races: pd.DataFrame, exacta: pd.DataFrame, quinella: pd.DataFrame) -> pd.DataFrame:
        """1行 = 1レース: ``year``・``favourite_won``・``ratio``。"""
        single_exacta = self._single(exacta, "exacta_yen")
        single_quinella = self._single(quinella, "quinella_yen")
        joined = races[["year", "pop_1st", "pop_2nd"]].join(single_exacta, how="inner").join(single_quinella, how="inner")
        joined = joined.dropna(subset=["pop_1st", "pop_2nd"])
        return pd.DataFrame({
            "year": joined["year"].astype(int), "favourite_won": joined["pop_1st"].lt(joined["pop_2nd"]),
            "ratio": joined["exacta_yen"] / joined["quinella_yen"],
        })

    def table(self, ratios: pd.DataFrame, condition: str) -> Table:
        rows = []
        for year, group in ratios.groupby("year", sort=True):
            rows.append(self._cells(str(year), _ALL_LABEL, group))
        for label in (_ALL_LABEL, *_ORDER_LABELS.values()):
            chosen = ratios if label == _ALL_LABEL else ratios[ratios["favourite_won"].eq(label == _ORDER_LABELS[True])]
            rows.append(self._cells(TOTAL_LABEL, label, chosen))
        table = Table(list(COLUMNS), rows, title=f"馬単の払戻 ÷ 馬連の払戻 — {condition}",
                      note="馬単・馬連がそれぞれ1つの組だけ払い戻されたレース（同着を除く）。人気は確定の単勝人気。")
        table.meta = {"races": int(len(ratios)), "condition": condition}
        return table

    @staticmethod
    def _single(payouts: pd.DataFrame, name: str) -> pd.DataFrame:
        counts = payouts.groupby("race_id")["yen"].agg(["count", "max"])
        return counts[counts["count"].eq(1)][["max"]].rename(columns={"max": name})

    @staticmethod
    def _cells(year_label: str, order_label: str, chosen: pd.DataFrame) -> list[str]:
        if chosen.empty:
            return [year_label, order_label, "0", *["—"] * (len(COLUMNS) - 3)]
        ratio = chosen["ratio"]
        low, high = RATIO_BAND
        within = ratio.between(low, high).mean()
        return [year_label, order_label, str(len(chosen)), f"{ratio.median():.2f}", f"{ratio.mean():.2f}",
                f"{ratio.quantile(0.25):.2f}", f"{ratio.quantile(0.75):.2f}", f"{within * 100:.1f}%"]
