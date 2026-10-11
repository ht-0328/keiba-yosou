"""対象のレースごとに、当日の傾き（その日の先に終わったレースと、前の日の同じ馬場のレースから）を出す。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import PredictionTiming

from . import names

#: 前の日（前日発売の時点で終わっている、同じ開催の前の開催日）のレースの重み。当日の先に終わったレースは 1。
PREVIOUS_DAY_WEIGHT = 0.5
#: 馬場状態が対象のレースと違う（レースの途中で雨などで変わった）当日のレースの重み。
OTHER_CONDITION_WEIGHT = 0.5


class DaySlopes:
    """対象のレース（``targets``。``RaceSlopes`` と同じ鍵と条件の列を持つ。まだ走っていなくてよい）ごとに、同じ馬場
    （``COURSE_KEY``）の終わったレースの傾きを重み付きで平均し、当日の傾きとレース数 n を出す。

    - 当日（``RACE_DAY``）: その日の先に終わったレース（レース番号が小さい）は 1、ただし馬場状態が対象と違えば 0.5。前の日のレースは 0.5
    - 前日（``DAY_BEFORE``）: 前の日（開催日の前日）の同じ馬場のレースだけ（0.5 ずつ）。その日のレースはまだ走っていない
    - 木曜: 数えない（n = 0。過去の傾きだけになる）

    ``finished`` は終わったレースの傾きの表（対象の日とその前の日のレースが入っていればよい。対象のレース自身は数えない）。
    """

    def of(self, targets: pd.DataFrame, finished: pd.DataFrame, timing: PredictionTiming) -> pd.DataFrame:
        """列は ``内の傾き``・``前の傾き``（当日の傾き。数えるレースが無ければ欠損値）・``レース数``。index は ``targets`` と同じ。"""
        empty = pd.DataFrame({names.INNER_SLOPE: float("nan"), names.FRONT_SLOPE: float("nan"), names.RACES: 0.0}, index=targets.index)
        if timing is PredictionTiming.THURSDAY or finished.empty:
            return empty
        candidates = self._candidates(targets, finished, timing)
        if candidates.empty:
            return empty
        return self._weighted_mean(candidates).reindex(targets.index).fillna({names.RACES: 0.0})

    def _candidates(self, targets: pd.DataFrame, finished: pd.DataFrame, timing: PredictionTiming) -> pd.DataFrame:
        """対象のレースごとに、数える終わったレースを並べた表（列 ``_target``・傾き2つ・``_weight``）。"""
        keys = list(names.COURSE_KEY)
        left = targets[[names.RACE_ID, names.RACE_DATE, names.RACE_NO, names.CONDITION_CODE, *keys]].rename(
            columns={names.RACE_ID: "_target", names.RACE_DATE: "_date", names.RACE_NO: "_race_no", names.CONDITION_CODE: "_condition"})
        left = left.assign(_row=targets.index)
        right = finished[[names.RACE_ID, names.RACE_DATE, names.RACE_NO, names.CONDITION_CODE, *keys, *names.SLOPES]]
        pairs = left.astype({key: str for key in keys}).merge(right.astype({key: str for key in keys}), on=keys, how="inner")
        pairs = pairs[pairs[names.RACE_ID] != pairs["_target"]]
        previous = pairs[names.RACE_DATE] == pairs["_date"] - pd.Timedelta(days=1)
        same_day = (pairs[names.RACE_DATE] == pairs["_date"]) & (pairs[names.RACE_NO].astype(float) < pairs["_race_no"].astype(float))
        if timing is PredictionTiming.DAY_BEFORE:
            same_day = same_day & False
        other_condition = pairs[names.CONDITION_CODE].astype(str) != pairs["_condition"].astype(str)
        weight = pd.Series(0.0, index=pairs.index)
        weight[previous] = PREVIOUS_DAY_WEIGHT
        weight[same_day] = 1.0
        weight[same_day & other_condition] = OTHER_CONDITION_WEIGHT
        chosen = pairs[weight > 0].assign(_weight=weight[weight > 0])
        return chosen[["_row", *names.SLOPES, "_weight"]]

    def _weighted_mean(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """対象の行ごとの、重み付きの平均と重みの合計（傾きの無いレースは、その傾きの平均に数えない）。"""
        result = {}
        for slope in names.SLOPES:
            has = candidates[slope].notna()
            weighted = (candidates[slope] * candidates["_weight"]).where(has, 0.0)
            weights = candidates["_weight"].where(has, 0.0)
            sums = pd.DataFrame({"_wx": weighted, "_w": weights, "_row": candidates["_row"]}).groupby("_row").sum()
            result[slope] = sums["_wx"] / sums["_w"].where(sums["_w"] > 0)
        races = candidates.groupby("_row")["_weight"].sum()
        return pd.DataFrame({**result, names.RACES: races})
