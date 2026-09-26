"""レースごとの前半・後半タイムの基準を付ける・引く。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .pace_baseline import FIRST_HALF_BASELINE, SECOND_HALF_BASELINE, PaceBaseline

#: 前半タイムの測る区間の列（500・550・600m。設計書 10 の 4）。
MEASURED_METERS = "測る区間"
#: 距離が 200m で割り切れないときに、余りの距離に足す長さ（m）と、割り切れるときの区間（m）。
_FURLONG, _TWO_FURLONGS, _THREE_FURLONGS = 200, 400, 600
#: 基準を付けるのに要るレースの列。
_RACE_COLUMNS: tuple[str, ...] = ("race_id", "race_date", "venue_code", "track_code", "distance_m", "class_order")


class RaceBaselineLookup:
    """レースの表に、前半タイムと後半タイムの基準と、前半タイムの測る区間を付ける（設計書 10 の 4.・5.・9.）。

    学習では、``PaceRecordSource`` が読んだレースの記録に付ける（``attach``）。予測では、予測するレースが記録に無い
    （まだ成績が無い）ので、記録とそのレースの条件を合わせてから付け直す（``of``）。どちらも同じ ``PaceBaseline`` を使う。
    """

    def __init__(self) -> None:
        self._first_half = PaceBaseline("first3f", FIRST_HALF_BASELINE)
        self._second_half = PaceBaseline("last3f_race", SECOND_HALF_BASELINE)

    def attach(self, races: pd.DataFrame) -> pd.DataFrame:
        """``races``（1行 = 1レース）に、前半・後半の基準の4列ずつと、測る区間を足して返す。"""
        with_baselines = self._second_half.attach(self._first_half.attach(races))
        remainder = pd.to_numeric(races["distance_m"], errors="coerce") % _FURLONG
        measured = np.where(remainder == 0, _THREE_FURLONGS, remainder + _TWO_FURLONGS)
        return with_baselines.assign(**{MEASURED_METERS: measured})

    def of(self, race_results: pd.DataFrame, races: pd.DataFrame) -> pd.DataFrame:
        """``races``（対象のレース。index はレースID、列に ``_RACE_COLUMNS``）の基準の表（index はレースID）。

        ``race_results``（``attach`` 済みのレースの記録）にあるレースは、その値をそのまま使う。無いレース（予測するレース）は、
        記録にそのレースの条件の行を足してから付け直す。
        """
        known = race_results.set_index("race_id", drop=False)
        missing = races.loc[~races.index.isin(known.index), list(_RACE_COLUMNS)]
        if missing.empty:
            return known.reindex(races.index)
        history = known[[column for column in known.columns if column in (*_RACE_COLUMNS, "first3f", "last3f_race")]]
        combined = pd.concat([history, missing.assign(first3f=np.nan, last3f_race=np.nan)], ignore_index=True)
        recomputed = self.attach(combined).drop_duplicates("race_id", keep="last").set_index("race_id", drop=False)
        return pd.concat([known, recomputed.loc[missing.index]]).reindex(races.index)
