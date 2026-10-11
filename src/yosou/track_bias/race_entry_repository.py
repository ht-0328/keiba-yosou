"""これから走る1レースの、鍵と条件と出走馬（馬番・頭数）を読む。"""

from __future__ import annotations

import duckdb
import pandas as pd

from 共通 import codes, keys

from . import names
from .race_slopes import meeting_day_of


class RaceEntryRepository:
    """レース詳細（``ra``）と馬毎レース情報（``se``）から、1レースの鍵と条件（競馬場コード・芝ダ・トラックコード・開催の何日目・馬場状態・
    レース番号・開催日）と、出走馬（馬ID・馬番・頭数）を読む。

    これから走るレース（成績が無く、事実表に出ない）にも使えるように、事実表ではなく ``ra``・``se`` のいちばん新しい行を読む。
    馬場状態は、芝ならば芝の、ダートならダートの馬場状態コード（未発表の 0 は欠損値）。頭数は出走頭数（無ければ登録頭数）。
    出走取消・除外の馬は入れない。レースが無ければ ``LookupError``、障害なら ``ValueError``。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def read(self, race_id: str) -> pd.DataFrame:
        """1行 = 1頭。列は ``race_id``・``race_date``・``venue_code``・``surface``・``track_code``・``meeting_day``・``condition_code``・``race_no``・
        ``horse_id``・``horse_no``・``field_size``。"""
        cond, params = keys.rid_condition(race_id)
        race = self._con.execute(
            f"""SELECT "競馬場コード", "トラックコード", "芝馬場状態コード", "ダート馬場状態コード", "レース番号", "出走頭数", "登録頭数",
                       "開催年" || "開催月日"
                FROM ra WHERE {cond} {keys.latest_qualify(keys.RACE_KEY)}""", params,
        ).fetchone()
        if race is None:
            raise LookupError(f"レースが見つかりません: {race_id}")
        venue_code, track_code, turf_condition, dirt_condition, race_no, field_size, registered, day = race
        surface = codes.surface_of(track_code)
        if surface not in ("芝", "ダート"):
            raise ValueError(f"平地のレースではありません: {race_id}（トラックコード {track_code}）")
        horses = self._con.execute(
            f"""SELECT {keys.q(keys.HORSE_KEY)}, "馬番" FROM se WHERE {cond} AND {keys.q('データ区分')} NOT IN ('0', '9')
                AND "異常区分コード" NOT IN ('1', '2', '3') {keys.latest_qualify((*keys.RACE_KEY, keys.HORSE_KEY))}
                ORDER BY "馬番" """, params,
        ).df()
        condition = turf_condition if surface == "芝" else dirt_condition
        size = int(field_size) if field_size and int(field_size) > 0 else (int(registered) if registered else len(horses))
        return pd.DataFrame({
            names.RACE_ID: race_id, names.RACE_DATE: pd.Timestamp(f"{day[:4]}-{day[4:6]}-{day[6:8]}"),
            names.VENUE_CODE: str(venue_code), names.SURFACE: surface, names.TRACK_CODE: str(track_code),
            names.MEETING_DAY: meeting_day_of(pd.Series([race_id] * len(horses))).to_numpy(),
            names.CONDITION_CODE: (str(condition) if condition and str(condition) != "0" else None), names.RACE_NO: int(race_no),
            "horse_id": horses[keys.HORSE_KEY].astype(str).to_numpy(), "horse_no": pd.to_numeric(horses["馬番"], errors="coerce").to_numpy(),
            "field_size": size,
        })
