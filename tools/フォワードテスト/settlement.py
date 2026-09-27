"""記録した買い目を、レースの結果で精算する。"""

from __future__ import annotations

from datetime import datetime

import duckdb
import numpy as np
import pandas as pd

from フォワードテスト.ledger import REFUNDED, SETTLED, Ledger
from フォワードテスト.repository import PlaceResultRepository


class Settlement:
    """まだ精算していない買い目のうち、結果が出たレースのものに、払戻と精算の状態を書く。

    払戻（円）は、100円あたりの複勝の払戻 × 賭け金 ÷ 100（外れは 0）。
    出走取消・発走除外とレース中止は返還（払戻 = 賭け金）。
    """

    def __init__(self, ledger: Ledger) -> None:
        self._ledger = ledger

    def settle(self, con: duckdb.DuckDBPyConnection, now: datetime) -> int:
        """精算した買い目の数を返す。"""
        buys = self._ledger.buys()
        waiting = (buys["精算"] == "").to_numpy()
        if not waiting.any():
            return 0
        results = PlaceResultRepository(con).read(sorted(set(buys.loc[waiting, "race_id"])))
        results = results.assign(馬番=results["horse_no"].astype(str)).drop(columns="horse_no")
        joined = buys[["race_id", "馬番"]].merge(results, on=["race_id", "馬番"], how="left")
        refund = joined["refund"].fillna(False).astype(bool).to_numpy()
        done = waiting & (joined["has_result"].fillna(False).astype(bool).to_numpy() | refund)
        stake = pd.to_numeric(buys["賭け金"]).to_numpy()
        payout = np.where(refund, stake, joined["place_yen"].fillna(0).to_numpy() * stake / 100)
        buys.loc[done, "払戻"] = [str(int(value)) for value in payout[done]]
        buys.loc[done, "精算"] = [REFUNDED if value else SETTLED for value in refund[done]]
        buys.loc[done, "精算時刻"] = now.strftime("%Y-%m-%d %H:%M")
        self._ledger.replace_buys(buys)
        return int(done.sum())
