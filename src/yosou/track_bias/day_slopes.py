"""対象のレースごとに、当日の傾き（その日の先に終わったレースと、前の日の同じ馬場のレースから）を出す。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.feature import PredictionTiming

from . import names

#: 前の日（前日発売の時点で終わっている、同じ開催の前の開催日）のレースの重み。当日の先に終わったレースは 1。
PREVIOUS_DAY_WEIGHT = 0.5
#: 馬場状態が対象のレースと違う（レースの途中で雨などで変わった）当日のレースの重み。
OTHER_CONDITION_WEIGHT = 0.5
#: 対象の行・重みの作業用の列。
_TARGET, _ROW, _DATE, _RACE_NO, _CONDITION, _WEIGHT = "_target", "_row", "_date", "_race_no", "_condition", "_weight"


class DaySlopes:
    """対象のレース（``targets``。``RaceSlopes`` と同じ鍵と条件の列を持つ。まだ走っていなくてよい）ごとに、同じ馬場
    （``COURSE_KEY``）の終わったレースの傾きを重み付きで平均し、当日の傾きとレース数 n を出す。

    - 当日（``RACE_DAY``）: その日の先に終わったレース（レース番号が小さい）は 1、ただし馬場状態が対象と違えば 0.5。前の日のレースは 0.5
    - 前日（``DAY_BEFORE``）: 前の日（開催日の前日）の同じ馬場のレースだけ（0.5 ずつ）。その日のレースはまだ走っていない
    - 木曜: 数えない（n = 0。過去の傾きだけになる）
    - 終わった日（``of_finished_day``）: その日のほかの全部のレース（先も後も。馬場状態が違えば 0.5）と前の日のレース（0.5）。
      回顧で「結果の位置で出したバイアス」を数えるときの傾き

    ``finished`` は終わったレースの傾きの表（対象の日とその前の日のレースが入っていればよい。対象のレース自身は数えない）。
    同じ馬場 × 同じ日（と前の日）だけを突き合わせるので、全レースを対象にしても重くならない。
    """

    def of(self, targets: pd.DataFrame, finished: pd.DataFrame, timing: PredictionTiming) -> pd.DataFrame:
        """列は ``内の傾き``・``前の傾き``（当日の傾き。数えるレースが無ければ欠損値）・``レース数``。index は ``targets`` と同じ。"""
        if timing is PredictionTiming.THURSDAY:
            return self._empty(targets)
        return self._of(targets, finished, same_day=timing is PredictionTiming.RACE_DAY, whole_day=False)

    def of_finished_day(self, targets: pd.DataFrame, finished: pd.DataFrame) -> pd.DataFrame:
        """終わった日の傾き（その日のほかの全部のレースと前の日のレースから）。列と index は ``of`` と同じ。"""
        return self._of(targets, finished, same_day=True, whole_day=True)

    def _of(self, targets: pd.DataFrame, finished: pd.DataFrame, same_day: bool, whole_day: bool) -> pd.DataFrame:
        if finished.empty or targets.empty:
            return self._empty(targets)
        candidates = self._candidates(targets, finished, same_day, whole_day)
        if candidates.empty:
            return self._empty(targets)
        return self._weighted_mean(candidates).reindex(targets.index).fillna({names.RACES: 0.0})

    def _empty(self, targets: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({names.INNER_SLOPE: float("nan"), names.FRONT_SLOPE: float("nan"), names.RACES: 0.0}, index=targets.index)

    def _candidates(self, targets: pd.DataFrame, finished: pd.DataFrame, same_day: bool, whole_day: bool) -> pd.DataFrame:
        """対象のレースごとに、数える終わったレースを並べた表（列 ``_row``・傾き2つ・``_weight``）。"""
        keys = list(names.COURSE_KEY)
        left = targets[[names.RACE_ID, names.RACE_DATE, names.RACE_NO, names.CONDITION_CODE, *keys]].rename(
            columns={names.RACE_ID: _TARGET, names.RACE_DATE: _DATE, names.RACE_NO: _RACE_NO, names.CONDITION_CODE: _CONDITION})
        left = left.assign(**{_ROW: targets.index}).astype({key: str for key in keys})
        right = finished[[names.RACE_ID, names.RACE_DATE, names.RACE_NO, names.CONDITION_CODE, *keys, *names.SLOPES]].astype({key: str for key in keys})
        parts = [self._previous_day(left, right, keys)]
        if same_day:
            parts.append(self._same_day(left, right, keys, whole_day))
        chosen = pd.concat(parts)
        return chosen[chosen[_WEIGHT] > 0][[_ROW, *names.SLOPES, _WEIGHT]]

    def _previous_day(self, left: pd.DataFrame, right: pd.DataFrame, keys: list[str]) -> pd.DataFrame:
        """前の日の同じ馬場のレース（0.5）。"""
        shifted = left.assign(**{_DATE: left[_DATE] - pd.Timedelta(days=1)})
        pairs = shifted.merge(right, left_on=[*keys, _DATE], right_on=[*keys, names.RACE_DATE], how="inner")
        return pairs.assign(**{_WEIGHT: PREVIOUS_DAY_WEIGHT})

    def _same_day(self, left: pd.DataFrame, right: pd.DataFrame, keys: list[str], whole_day: bool) -> pd.DataFrame:
        """その日の同じ馬場のレース（先に終わったものだけ、または自分以外の全部）。馬場状態が違えば 0.5。"""
        pairs = left.merge(right, left_on=[*keys, _DATE], right_on=[*keys, names.RACE_DATE], how="inner")
        pairs = pairs[pairs[names.RACE_ID] != pairs[_TARGET]]
        if not whole_day:
            pairs = pairs[pairs[names.RACE_NO].astype(float) < pairs[_RACE_NO].astype(float)]
        other_condition = pairs[names.CONDITION_CODE].astype(str) != pairs[_CONDITION].astype(str)
        return pairs.assign(**{_WEIGHT: other_condition.map({True: OTHER_CONDITION_WEIGHT, False: 1.0}).astype(float)})

    def _weighted_mean(self, candidates: pd.DataFrame) -> pd.DataFrame:
        """対象の行ごとの、重み付きの平均と重みの合計（傾きの無いレースは、その傾きの平均に数えない）。"""
        result = {}
        for slope in names.SLOPES:
            has = candidates[slope].notna()
            weighted = (candidates[slope] * candidates[_WEIGHT]).where(has, 0.0)
            weights = candidates[_WEIGHT].where(has, 0.0)
            sums = pd.DataFrame({"_wx": weighted, "_w": weights, _ROW: candidates[_ROW]}).groupby(_ROW).sum()
            result[slope] = sums["_wx"] / sums["_w"].where(sums["_w"] > 0)
        races = candidates.groupby(_ROW)[_WEIGHT].sum()
        return pd.DataFrame({**result, names.RACES: races})
