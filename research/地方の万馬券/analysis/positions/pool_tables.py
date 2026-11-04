"""票の表: 1つの期間（年）の、馬の表・対の表・組の表（全頭の予想の確率と、各券種の票から見た市場の見立てつき）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

#: 馬の表の列。``p1``・``p3`` は全頭の予想①の 1着・3着以内の確率（``_lgb``・``_cat`` はモデルごと）、``s`` は単勝の支持率、
#: ``m_a`` は 3連単の票で a が1着の割合、``m_ax`` は馬単の票で a が1着の割合、``m1t`` は 3連複の票で a を含む割合、``px`` は複勝オッズの逆数。
HORSE_COLUMNS: tuple[str, ...] = ("race_id", "race_date", "horse_no", "popularity", "win_odds", "finish",
                                   "p1", "p1_lgb", "p1_cat", "p3", "p3_lgb", "p3_cat", "s", "m_a", "m_ax", "m1t", "px")
#: 対の表（a が1着のとき b が2着）の列。``m2`` は 3連単の票の条件つきの割合、``m2x`` は馬単 a→b の票、``m2t`` は 3連複の票で a・b を含む割合。
PAIR_COLUMNS: tuple[str, ...] = ("race_id", "first", "second", "m2", "m2x", "m2t")
#: 組の表（3連単の全部の組）の列。``m`` は 3連単の票の割合、``m3`` は a・b のあとの条件つきの割合、``m3t`` は 3連複 {a, b, c} の票、
#: ``key_ab`` は (レース, a, b) の鍵、``odds``・``payout`` は 3連単の確定オッズと払戻（外れは 0）。
COMBO_COLUMNS: tuple[str, ...] = ("race_id", "first", "second", "third", "odds", "payout", "m", "m3", "m3t", "key_ab")


@dataclass(frozen=True)
class PoolTables:
    """``horses``・``pairs``・``combos`` の3つの表。``PoolTablesBuilder`` が作る。"""

    horses: pd.DataFrame
    pairs: pd.DataFrame
    combos: pd.DataFrame

    @property
    def race_ids(self) -> pd.Series:
        return self.horses["race_id"].drop_duplicates()
