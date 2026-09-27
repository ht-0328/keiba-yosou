"""3連単の人気薄の組の買われすぎを直す倍率を、年ごとに用意する。"""

from __future__ import annotations

import copy
from pathlib import Path

import pandas as pd

from 回収率100超.analysis.tickets import OddsBandCalibrator

#: 3連単のオッズの帯。
BANDS: tuple[float, ...] = (0, 10, 30, 100, 300, 1000, 3000, 10000, 1e9)
#: 帯ごとの見込みの当たりが少ないときに倍率を 1 に寄せる強さ。3連単は帯ごとの当たりが多いので小さくてよい。
SHRINK = 20.0


class TrifectaCorrections:
    """3連単のオッズの逆数をレースで合計 1 にそろえた確率が、オッズの帯ごとにどれだけ当たったかを年ごとに数える。

    ``for_year(year)`` は、その年より前の年（``first_year`` から）の実績だけで作った倍率を返す。
    モデルの予測は使わないので、予測の無い 2016・2017年も数えられる。
    例: 3,000〜10,000倍の帯で、見込み 100回・実際 60回なら、その帯の組の確率を 0.6倍ほどにする。
    """

    def __init__(self, tickets_dir: Path, first_year: int, last_year: int) -> None:
        payouts = pd.read_parquet(tickets_dir / "trifecta_payout.parquet")
        running = OddsBandCalibrator(BANDS, shrink=SHRINK)
        self._by_year: dict[int, OddsBandCalibrator] = {}
        for year in range(first_year, last_year + 1):
            self._by_year[year] = copy.deepcopy(running)
            self._add_year(running, pd.read_parquet(tickets_dir / f"trifecta_{year}.parquet"), payouts)

    def for_year(self, year: int) -> OddsBandCalibrator:
        return self._by_year[year]

    def _add_year(self, running: OddsBandCalibrator, odds: pd.DataFrame, payouts: pd.DataFrame) -> None:
        inverse = 1.0 / odds["odds"].to_numpy(dtype=float)
        probability = inverse / pd.Series(inverse).groupby(odds["rid"].to_numpy()).transform("sum").to_numpy()
        hit = odds.merge(payouts, on=["rid", "h1", "h2", "h3"], how="left")["payout"].notna()
        running.add(odds["odds"].to_numpy(dtype=float), probability, hit.to_numpy(dtype=float))
