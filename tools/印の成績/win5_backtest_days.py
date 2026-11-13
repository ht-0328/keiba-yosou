"""過去の WIN5 の日ごとに、区切りごとの予測から5レースの確率の表を作る。"""

from __future__ import annotations

import pandas as pd

from yosou.form_aptitude_win5_tickets.leg import RaceWinShare
from yosou.form_aptitude_win5_tickets.repository import LEG_COUNT
from yosou.form_aptitude_win5_tickets.repository.win5_columns import (
    CARRY,
    HORSE_NO,
    JUMP,
    LEG,
    POST_TIME,
    RACE_DATE,
    RACE_ID,
    SATURDAY,
    WIN_ODDS,
)
from yosou.shared.feature import PredictionTiming
from yosou.shared.feature.odds import MarketWinProbability
from yosou.shared.workflow import WIN_PROBABILITY

from 印の成績.win5_backtest_day import Win5BacktestDay
from 印の成績.win5_fold_predictions import Win5FoldPredictions
from 印の成績.win5_leg_timing import Win5LegTiming
from 印の成績.win5_periods import Win5Periods

#: レースごとに使った確率の名前。
ODDS_ONLY = "オッズだけ"
#: 確かめに使えなかった日の理由。
NO_FOLD = "区切りごとの予測の期間の外"
MISSING_LEGS = "対象レースの出走馬がそろわない"
NO_PREDICTION = "区切りごとの予測が無い平地のレースがある"
NO_PROBABILITY = "1着の確率と単勝オッズのそろった馬がいないレースがある"
#: 確かめに使えなかった日の表の列。
SKIPPED_COLUMNS = ("開催日", "期間", "理由")


class Win5BacktestDays:
    """過去の WIN5 の日（2019年から）ごとに、5レースの確率の表（``RaceWinShare`` の結果）を作る（設計書「近走と適性からWIN5の買い目を決める」07・15 の 3）。

    - 平地のレース: 1レース目の発走から 60分以上あとに発走するレースは前日、それより前は当日の区切りごとの予測（``Win5LegTiming``）。
    - 障害のレース: 今のモデルは障害を予想しないので、オッズから見た勝率をそのまま1着の確率にする。
    - 区切りごとの予測が無い平地のレースが1つでもある日（予測のある期間の外の日を含む）は、その日の期待値を出せないので確かめから除き、
      除いた日と理由を別の表で返す（比べる相手も同じ日だけで数える）。
    """

    def __init__(self) -> None:
        self._timing = Win5LegTiming()
        self._share = RaceWinShare()
        self._market = MarketWinProbability()
        self._periods = Win5Periods()

    def of(self, history: pd.DataFrame, runners: pd.DataFrame,
           predictions: Win5FoldPredictions) -> tuple[list[Win5BacktestDay], pd.DataFrame]:
        """（確かめに使う日, 除いた日の表）。``history`` は ``Win5HistoryRepository``、``runners`` は ``Win5LegRunnerHistoryRepository`` の表。"""
        wanted = set(runners[RACE_ID])
        by_timing = {
            PredictionTiming.RACE_DAY: self._by_race(predictions.race_day, wanted),
            PredictionTiming.DAY_BEFORE: self._by_race(predictions.day_before, wanted),
        }
        runners_by_day = dict(tuple(runners.groupby(RACE_DATE, sort=False)))
        days, skipped = [], []
        for _, first in history.drop_duplicates(RACE_DATE).iterrows():
            race_date = str(first[RACE_DATE])
            period = self._periods.label_of(race_date)
            if period is None:
                continue
            result = self._day(race_date, first, runners_by_day.get(race_date), predictions, by_timing)
            if isinstance(result, str):
                skipped.append({"開催日": race_date, "期間": period, "理由": result})
            else:
                days.append(result)
        return days, pd.DataFrame(skipped, columns=list(SKIPPED_COLUMNS))

    def _day(self, race_date: str, first: pd.Series, runners: pd.DataFrame | None, predictions: Win5FoldPredictions,
             by_timing: dict[PredictionTiming, dict[str, pd.DataFrame]]) -> Win5BacktestDay | str:
        """その日の値か、使えない理由。"""
        fold = predictions.fold_of(race_date)
        if fold is None:
            return NO_FOLD
        if runners is None or runners[LEG].nunique() != LEG_COUNT:
            return MISSING_LEGS
        legs = [group for _, group in runners.groupby(LEG, sort=True)]
        timings = self._timing.of([str(leg[POST_TIME].iloc[0]) if pd.notna(leg[POST_TIME].iloc[0]) else None for leg in legs])
        tables, sources = [], []
        for leg, timing in zip(legs, timings, strict=True):
            if bool(leg[JUMP].iloc[0]):
                probability, source = self._market.of(leg[RACE_ID], leg[WIN_ODDS]), ODDS_ONLY
            else:
                probability, source = self._predicted(leg, by_timing[timing]), timing.label
                if probability is None:
                    return NO_PREDICTION
            try:
                tables.append(self._share.of(leg[[RACE_ID, HORSE_NO, WIN_ODDS]].assign(**{WIN_PROBABILITY: probability})))
            except LookupError:
                return NO_PROBABILITY
            sources.append(source)
        return Win5BacktestDay(race_date, fold, bool(first[SATURDAY]), int(first[CARRY]), tuple(tables), tuple(sources))

    def _predicted(self, leg: pd.DataFrame, by_race: dict[str, pd.DataFrame]) -> pd.Series | None:
        """出走馬ごとの区切りごとの予測の1着の確率（予測に無い馬は欠損値）。そのレースの予測が無ければ None。"""
        predicted = by_race.get(str(leg[RACE_ID].iloc[0]))
        if predicted is None:
            return None
        return leg[HORSE_NO].astype(int).map(predicted.set_index("horse_no")["probability"])

    def _by_race(self, tested: pd.DataFrame, wanted: set[str]) -> dict[str, pd.DataFrame]:
        """レースID → そのレースの予測の行（対象レースだけ）。"""
        rows = tested.loc[tested["race_id"].isin(wanted)]
        return {str(race_id): group for race_id, group in rows.groupby("race_id", sort=False)}
