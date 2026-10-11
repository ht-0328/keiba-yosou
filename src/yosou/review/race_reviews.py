"""終わったレースごとの回顧（表2）を作る。"""

from __future__ import annotations

import pandas as pd

from yosou.development_score import AdvantageRuns
from yosou.development_score import names as score_names
from yosou.track_bias import DaySlopes, RaceSlopes
from yosou.track_bias import names as bias_names

from . import names

#: 出力の列。
COLUMNS: tuple[str, ...] = (
    names.RACE_ID, names.RACE_DATE, names.FORECAST_PACE, names.FORECAST_HIGH, names.FORECAST_SLOW, names.RESULT_PACE,
    names.DAY_INNER_SLOPE, names.DAY_FRONT_SLOPE, names.CONDITION,
)


class RaceReviews:
    """``ReviewRunRepository`` の出走の表から、レースごとに結果のペース（``AdvantageRuns`` の ``ResultPace``）・終わった日の
    バイアスの傾き（``DaySlopes.of_finished_day``。内・前）・馬場状態コードを出す（設計書「買うレースと買い目を決める」08 の 3 の表2）。

    予想のペース（展開の予想③のハイ・スローの確率と、その多いほうの区分）は、予想したときに残した値（``forecast_paces``。
    ``race_id`` → ハイの確率・スローの確率）があれば入れ、無ければ欠損値。``after`` を渡すと、その日以降のレースだけ返す。
    """

    def __init__(self) -> None:
        self._advantage = AdvantageRuns()
        self._slopes = RaceSlopes()
        self._day = DaySlopes()

    def of(self, runs: pd.DataFrame, forecast_paces: pd.DataFrame | None = None, after: pd.Timestamp | None = None) -> pd.DataFrame:
        """1行 = 1レース（``COLUMNS``）。開催日・レースID の順。"""
        prepared = self._advantage.build(runs)
        slopes = self._slopes.of(runs)
        day = self._day.of_finished_day(slopes, slopes)
        races = prepared.drop_duplicates("race_id")[["race_id", "race_date", "condition_code", score_names.PACE]].reset_index(drop=True)
        by_race = pd.concat([slopes[[bias_names.RACE_ID]], day], axis=1).set_index(bias_names.RACE_ID)
        table = pd.DataFrame({
            names.RACE_ID: races["race_id"].astype(str), names.RACE_DATE: races["race_date"],
            names.FORECAST_PACE: None, names.FORECAST_HIGH: float("nan"), names.FORECAST_SLOW: float("nan"),
            names.RESULT_PACE: races[score_names.PACE],
            names.DAY_INNER_SLOPE: races["race_id"].astype(str).map(by_race[bias_names.INNER_SLOPE]).astype("float64"),
            names.DAY_FRONT_SLOPE: races["race_id"].astype(str).map(by_race[bias_names.FRONT_SLOPE]).astype("float64"),
            names.CONDITION: races["condition_code"].astype(str),
        })
        if forecast_paces is not None and not forecast_paces.empty:
            table = self._with_forecasts(table, forecast_paces)
        if after is not None:
            table = table[table[names.RACE_DATE] >= pd.Timestamp(after)]
        return table.sort_values([names.RACE_DATE, names.RACE_ID], kind="stable").reset_index(drop=True)

    def _with_forecasts(self, table: pd.DataFrame, forecast_paces: pd.DataFrame) -> pd.DataFrame:
        keyed = forecast_paces.astype({names.RACE_ID: str}).drop_duplicates(names.RACE_ID).set_index(names.RACE_ID)
        high = table[names.RACE_ID].map(keyed[names.FORECAST_HIGH]).astype("float64")
        slow = table[names.RACE_ID].map(keyed[names.FORECAST_SLOW]).astype("float64")
        even = 1 - high - slow
        # 予想の無いレースは空のまま（全部が欠損値の行で idxmax を呼ぶと pandas がエラーにするので、予想のある行だけで選ぶ）
        known = high.notna()
        label = pd.Series(None, index=table.index, dtype=object)
        if known.any():
            shares = pd.DataFrame({score_names.HIGH: high, score_names.EVEN: even, score_names.SLOW: slow})
            label[known] = shares[known].idxmax(axis=1)
        return table.assign(**{names.FORECAST_PACE: label, names.FORECAST_HIGH: high, names.FORECAST_SLOW: slow})
