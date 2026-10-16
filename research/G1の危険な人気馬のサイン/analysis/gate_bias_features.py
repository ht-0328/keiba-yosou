"""枠の有利・不利の材料（開催の先の日の傾向と、コースの過去の傾向）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .sign_columns import COURSE_GATE_EDGE, MEETING_GATE_EDGE

#: 率を出すのに要る、帯ごとの頭数の下限（これより少なければ NaN）。
_MIN_MEETING_RUNNERS = 20
_MIN_COURSE_RUNNERS = 60
#: 枠の帯（馬番 ÷ 頭数で3つに分ける）。
INNER, MIDDLE, OUTER = "内", "中", "外"
_BANDS = (INNER, MIDDLE, OUTER)


class GateBiasFeatures:
    """1行 = 1頭の出走の表から、枠の有利さの2列を返す（同じ index。値が大きいほど自分の枠に有利）。

    - 開催の先の日の、自分の枠の側の有利さ: 同じ年・競馬場・開催回・芝ダの、前の日までのレースで、外の帯の3着以内率 − 内の帯の3着以内率。
      自分が外の帯ならその値、内の帯なら符号を逆にした値、中の帯なら 0。当日の先のレースは使わない（前日にも分かる値にする）。
    - コースの過去の、自分の枠の帯の有利さ: 同じ競馬場・トラック・距離の、前の年までのレースで、自分の帯の3着以内率 − 全体の3着以内率。

    馬番と頭数は前日（出馬表）から分かる。
    """

    def compute(self, runs: pd.DataFrame) -> pd.DataFrame:
        band = self.band(runs["horse_no"], runs["field_size"])
        placed = runs["finish"].le(3).astype(int)
        out = pd.DataFrame(index=runs.index)
        out[MEETING_GATE_EDGE] = self._meeting_edge(runs, band, placed)
        out[COURSE_GATE_EDGE] = self._course_edge(runs, band, placed)
        return out

    def band(self, horse_no: pd.Series, field_size: pd.Series) -> pd.Series:
        """馬番の帯（内・中・外）。"""
        share = horse_no / field_size
        return pd.Series(np.select([share <= 1 / 3, share > 2 / 3], [INNER, OUTER], MIDDLE), index=horse_no.index)

    def _meeting_edge(self, runs: pd.DataFrame, band: pd.Series, placed: pd.Series) -> pd.Series:
        rid = runs["race_id"].astype(str)
        meeting = rid.str[:4] + rid.str[8:12] + runs["surface"].astype(str)
        frame = pd.DataFrame({"meeting": meeting, "day": runs["race_date"], "band": band, "placed": placed})
        daily = self._by_band(frame.groupby(["meeting", "day", "band"])["placed"])
        before = daily.groupby(level="meeting").cumsum() - daily
        rate = {side: before[("sum", side)] / before[("count", side)].where(before[("count", side)] >= _MIN_MEETING_RUNNERS)
                for side in (INNER, OUTER)}
        edge = (rate[OUTER] - rate[INNER]).rename("edge").reset_index()
        merged = frame.reset_index().merge(edge, on=["meeting", "day"], how="left").set_index("index")["edge"]
        side = band.map({OUTER: 1.0, INNER: -1.0, MIDDLE: 0.0})
        return (merged * side).reindex(runs.index)

    def _by_band(self, grouped) -> pd.DataFrame:
        """帯ごとの3着以内の数（sum）と頭数（count）の表。出走の無い帯も 0 の列で持つ。"""
        table = grouped.agg(["sum", "count"]).unstack("band", fill_value=0)
        columns = pd.MultiIndex.from_product([["sum", "count"], _BANDS])
        return table.reindex(columns=columns, fill_value=0).sort_index()

    def _course_edge(self, runs: pd.DataFrame, band: pd.Series, placed: pd.Series) -> pd.Series:
        course = runs["venue_code"].astype(str) + "-" + runs["track_code"].astype(str) + "-" + runs["distance_m"].astype(str)
        year = runs["race_date"].dt.year
        frame = pd.DataFrame({"course": course, "year": year, "band": band, "placed": placed})
        yearly = self._by_band(frame.groupby(["course", "year", "band"])["placed"])
        before = yearly.groupby(level="course").cumsum() - yearly
        total_sum = sum(before[("sum", side)] for side in _BANDS)
        total_count = sum(before[("count", side)] for side in _BANDS)
        overall = total_sum / total_count.where(total_count > 0)
        edges = {side: before[("sum", side)] / before[("count", side)].where(before[("count", side)] >= _MIN_COURSE_RUNNERS) - overall
                 for side in _BANDS}
        table = pd.DataFrame(edges).stack(future_stack=True).rename("edge").reset_index()
        table.columns = ["course", "year", "band", "edge"]
        merged = frame.reset_index().merge(table, on=["course", "year", "band"], how="left").set_index("index")["edge"]
        return merged.reindex(runs.index)
