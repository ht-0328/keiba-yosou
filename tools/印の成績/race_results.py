"""予測したレースの結果（着順・確定オッズ・人気・払戻・確定の複勝オッズ）を元DB から読む。"""

from __future__ import annotations

from types import SimpleNamespace

import duckdb
import pandas as pd

from 共通 import facts

from yosou.shared.repository import PlaceOddsRepository

#: 読んだレースIDを入れる一時表（``PlaceOddsRepository`` に渡す範囲）。
_WANTED = "mark_stats_races"

#: ``PlaceOddsRepository.read`` に渡す、読むレースの範囲（``relation`` だけを使う）。
_SCOPE = SimpleNamespace(relation=_WANTED)


class RaceResults:
    """``race_ids`` のレースに出走した馬の結果を読む。

    列は race_id・horse_id・horse_no・finish（着順。付かなければ欠損値）・win_odds（確定の単勝オッズ）・popularity（確定の単勝人気）・
    win_payout・place_payout（100円あたりの払戻。当たらなければ 0）・field_size・place_odds_low・place_odds_high（確定の複勝オッズ）。
    出走取消・除外は入れない。
    """

    def read(self, con: duckdb.DuckDBPyConnection, race_ids: pd.Series) -> pd.DataFrame:
        table = facts.ensure_facts(con)
        con.register("mark_stats_race_ids", pd.DataFrame({"race_id": race_ids.astype(str).drop_duplicates()}))
        con.execute(f"CREATE OR REPLACE TEMP TABLE {_WANTED} AS SELECT * FROM mark_stats_race_ids")
        runs = con.execute(f"""
            SELECT f.race_id, f.horse_id, f.horse_no, f.finish, f.win_odds, f.popularity, f.win_payout, f.place_payout, f.field_size
            FROM {table} AS f JOIN {_WANTED} USING (race_id)
            WHERE f.ran
        """).df().astype({"race_id": str, "horse_id": str})
        place = PlaceOddsRepository(con).read(_SCOPE).astype({"race_id": str})
        return runs.merge(place, on=["race_id", "horse_no"], how="left")
