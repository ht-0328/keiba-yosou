"""3連単のオッズから、馬ごとの「3連単から見た勝率」を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from yosou.shared.repository import POOLS, FirstHorsePoolRepository

from 印の成績.filter_columns import POOL_WIN

#: 読むレースIDを入れる一時表。
_WANTED = "mark_stats_pool_races"
#: 3連単から見た勝率の決まり（``POOLS`` の先頭。当日のモデルの材料 N と同じ計算）。
_TRIFECTA_WIN = POOLS[0]


class PoolWinReader:
    """``race_ids`` のレースの3連単の確定オッズ（無ければ最新の断面）から、馬ごとの「3連単から見た勝率」を読む
    （予想のパッケージの ``FirstHorsePoolRepository``。1/オッズ をレース内で合計 1 にそろえ、その馬が1着の買い目ぶん足す）。

    売上のいちばん大きい3連単のプールの見立てを、単勝オッズから見た勝率と比べるのに使う（研究「回収率100超の施策」の施策 1-A）。
    3連単の買い目の表は1億行を超えるので、対象のレースの開催年（レースID の先頭4桁）の行だけ読む。
    列は race_id・horse_no・``pool_win``。3連単の発売の無いレースの馬は行が無い。
    """

    def read(self, con: duckdb.DuckDBPyConnection, race_ids: pd.Series) -> pd.DataFrame:
        wanted = race_ids.astype(str).drop_duplicates()
        con.register("mark_stats_pool_race_ids", pd.DataFrame({"race_id": wanted}))
        con.execute(f"CREATE OR REPLACE TEMP TABLE {_WANTED} AS SELECT * FROM mark_stats_pool_race_ids")
        pools = FirstHorsePoolRepository(con).read(_TRIFECTA_WIN, _WANTED, years=sorted(set(wanted.str[:4])))
        table = pools.rename(columns={_TRIFECTA_WIN.column: POOL_WIN}).dropna(subset=["horse_no"])
        return table.astype({"race_id": str, "horse_no": int})[["race_id", "horse_no", POOL_WIN]]
