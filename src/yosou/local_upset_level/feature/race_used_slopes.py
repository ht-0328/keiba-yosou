"""これから走る1レースの使う傾き（U のレースの値）を出す。"""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
import pandas as pd

from yosou.shared.feature import PredictionTiming
from yosou.track_bias import BiasRunRepository, DaySlopes, RaceEntryRepository, RaceSlopes, UsedSlopes, names

from ..repository import PriorSlopeYearStore
from .used_slope_features import USED_FRONT, USED_INNER


class RaceUsedSlopes:
    """これから走る（か終わった）1レースの、使う内の傾き・使う前の傾きを、``UsedSlopeFeatures`` に渡す表（1行。index はレースID）にする。

    学習データ（``race_slopes_table``。``LocalBiasHistory`` の年ごとのリーク防止）と同じ決めごとで出す（設計書 11 の 9）。

    - 当日の傾き: そのレースの開催日とその前の日の終わったレース（速報 0B15 で取り込んだ当日の成績を含む）の傾き（``RaceSlopes``）を、
      ``DaySlopes`` で時点に合わせて数える（当日は先に終わった同じ競馬場のレース、前日は前の日のレース、出馬表は数えない）。
      2日ぶんの出走だけ読むので速い。
    - 過去の傾きの表: そのレースの年の1月1日より前のレースだけで作ったもの（``PriorSlopeYearStore`` が年ごとにとっておく）。
    - 使う傾き: 2つを ``UsedSlopes`` でレース数で混ぜたもの。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection, store: PriorSlopeYearStore) -> None:
        self._con = con
        self._store = store

    def of(self, race_id: str, timing: PredictionTiming) -> pd.DataFrame:
        """列は ``当日の使う内の傾き``・``当日の使う前の傾き``。レースが無ければ ``LookupError``。"""
        target = RaceEntryRepository(self._con).read(race_id).iloc[[0]].reset_index(drop=True)
        race_day = pd.Timestamp(target[names.RACE_DATE].iloc[0]).date()
        prior = self._store.load(self._con, date(race_day.year, 1, 1))
        runs = BiasRunRepository(self._con).read(race_day - timedelta(days=1))
        finished = RaceSlopes().of(runs) if not runs.empty else pd.DataFrame()
        day = DaySlopes().of(target, finished, timing)
        used = UsedSlopes().of(day, prior.lookup(target))
        return pd.DataFrame({USED_INNER: used[names.USED_INNER].to_numpy(), USED_FRONT: used[names.USED_FRONT].to_numpy()},
                            index=pd.Index([race_id]))
