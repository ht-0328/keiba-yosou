"""組の期待値の買い方の成績を、期間ごとに数える（採用の判定）。"""

from __future__ import annotations

import pandas as pd

from 共通.bootstrap_interval import BootstrapInterval

#: 期間（名前, 最初の年, 最後の年）。手順5（docs/04 の 4）は 2019〜2020年がまだ見ていない年、2023〜2026年が線と重みを決めた年。
#: 手順6（docs/05 の 4）は 2016〜2018年がまだ見ていない年、2020〜2026年が線を決めた年。
PERIODS_STEP6: tuple[tuple[str, int, int], ...] = (
    ("2016〜2018年（まだ見ていない）", 2016, 2018), ("2019〜2022年", 2019, 2022), ("2023〜2026年", 2023, 2026),
    ("2016〜2026年（全体）", 2016, 2026),
)
PERIODS: tuple[tuple[str, int, int], ...] = (
    ("2019〜2020年（まだ見ていない）", 2019, 2020), ("2021〜2022年", 2021, 2022), ("2023〜2026年（決めた期間）", 2023, 2026),
    ("2019〜2026年（全体）", 2019, 2026),
)


class ComboPeriodReport:
    """道具「印の成績」の買い目の CSV（1行 = 1点。日本語の列）のうち、組の期待値の買い方の行から、買い方 × 期間ごとの
    買ったレース・点数・的中・回収率・開催日を単位にしたブートストラップの 90% の幅と、年ごとの回収率を出す。トリガミ・オッズ無しで外した点は数えない。
    採用の基準（docs/04 の 4）: まだ見ていない 2019〜2020年で 100% 超え、かつ全体の幅の下の端が 100% 超え。
    """

    def __init__(self, periods: tuple[tuple[str, int, int], ...] = PERIODS) -> None:
        self._periods = periods

    def tables(self, tickets: pd.DataFrame, labels: tuple[str, ...]) -> tuple[pd.DataFrame, pd.DataFrame]:
        bought = tickets[tickets["買い方"].isin(labels) & tickets["外した理由"].fillna("").eq("")].copy()
        bought["年"] = pd.to_datetime(bought["開催日"]).dt.year
        bought = bought[bought["年"] >= min(first for _, first, _ in self._periods)]
        periods = pd.DataFrame([self._row(label, name, bought[(bought["買い方"] == label) & bought["年"].between(first, last)])
                                for label in labels for name, first, last in self._periods],
                               columns=["買い方", "期間", "買ったレース", "点数", "的中", "回収率", "90%の幅"])
        yearly = bought.groupby(["買い方", "年"])["払戻（100円あたり）"].agg(["sum", "size"])
        yearly = (yearly["sum"] / yearly["size"]).round(1).unstack("年").reindex(list(labels))
        return periods, yearly

    def _row(self, label: str, name: str, chosen: pd.DataFrame) -> list:
        if chosen.empty:
            return [label, name, 0, 0, 0, "—", "—"]
        payout = chosen["払戻（100円あたり）"].astype(float)
        stake = pd.Series(100.0, index=chosen.index)
        low, high = BootstrapInterval().of(chosen["開催日"], stake, payout)
        return [label, name, chosen["レースID"].nunique(), len(chosen), int((payout > 0).sum()), f"{payout.sum() / stake.sum() * 100:.1f}%",
                f"{low * 100:.1f}%〜{high * 100:.1f}%"]
