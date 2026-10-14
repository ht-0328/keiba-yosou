"""1レースの競馬場コードと芝ダを読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import codes, keys

from .. import names


class RaceCourseRepository:
    """レース詳細（``ra``）から、1レースの競馬場コードと芝ダ（トラックコードから）を、1行の表にして読む。

    これから走るレース（成績が無く、事実表に出ない）にも使えるように、事実表ではなく ``ra`` を読む。
    レースが無ければ ``LookupError``、障害なら ``ValueError``（表 G は平地だけで作る）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, race_id: str) -> pd.DataFrame:
        """列は ``race_id``・``競馬場コード``・``芝ダ``。"""
        cond, params = keys.rid_condition(race_id)
        row = self._con.execute(
            f"""SELECT "競馬場コード", "トラックコード" FROM ra WHERE {cond} {keys.latest_qualify(keys.RACE_KEY)}""", params,
        ).fetchone()
        if row is None:
            raise LookupError(f"レースが見つかりません: {race_id}")
        venue_code, track_code = row
        surface = codes.surface_of(track_code)
        if surface not in ("芝", "ダート"):
            raise ValueError(f"平地のレースではありません: {race_id}（トラックコード {track_code}）")
        return pd.DataFrame({"race_id": [race_id], names.VENUE_CODE: [venue_code], names.SURFACE: [surface]})
