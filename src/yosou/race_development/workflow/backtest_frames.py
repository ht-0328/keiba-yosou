"""年ごとの確かめで、学習データと予測から、買い目と当たり具合の元になる表を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.dataset import HORSE_ID, HORSE_NO, RACE_DATE, RACE_ID, VENUE
from yosou.shared.feature import FIELD_SIZE
from yosou.shared.dataset.column_names import FINISH, POPULARITY, WIN_ODDS

from ..betting import column_names as bet
from ..dataset import label_names as names
from ..evaluation import RECENT_CLOSING, RECENT_CORNER4, TOP3_PROBABILITY, YEAR
from ..evaluation import unlabeled_race_table as unlabeled
from ..evaluation.stage_baselines import LEAD_CANDIDATES, LEAD_RATE, PREVIOUS_POSITION, STYLE
from ..feature import LEADER_PROBABILITY, WIN_PROBABILITY, GroupForecast
from ..ml_model import OrderProbability
from .group_fitter import ORDER_LAMBDA
from .kind_datasets import KindDatasets


class BacktestFrames:
    """学習データ（``KindDatasets``）と3つの組の予測から、年ごとの確かめに使う表を作る。

    - ``betting``: 買い目を作る1年ぶんの表（1行 = 1頭。``YearBetting`` の列）。
    - ``horses``・``races``: 当たり具合を測る表（1行 = 1頭・1レース。目的変数と予測と近走の特徴量）。
    - ``unlabeled``: 正解を作らなかったレースを数える表（1行 = 1レース。``UnlabeledRaceTable`` の列）。
    """

    def __init__(self, datasets: KindDatasets) -> None:
        self._datasets = datasets
        self._order = OrderProbability()

    def betting(self, year: int, early: GroupForecast, finish: GroupForecast,
                win_column: str = WIN_PROBABILITY) -> pd.DataFrame:
        """``win_column`` は、印と買い目に使う1着の確率の列（既定は ⑦。オッズを足したモデルと比べるときに変える）。"""
        horses = self._year_rows(self._datasets.horses.ids, year)
        evaluation = self._datasets.horses.evaluation.loc[horses.index]
        predicted = finish.horse_rows(horses)
        table = pd.DataFrame({
            bet.RACE_ID: horses[RACE_ID].astype(str),
            bet.HORSE_NO: pd.to_numeric(horses[HORSE_NO], errors="coerce"),
            bet.WIN_PROBABILITY: predicted[win_column],
            bet.WIN_ODDS: evaluation[WIN_ODDS],
            bet.LEADER_PROBABILITY: early.horse_rows(horses)[LEADER_PROBABILITY],
            ORDER_LAMBDA: predicted[ORDER_LAMBDA],
        })
        return table[table[bet.WIN_PROBABILITY].notna() & table[bet.HORSE_NO].notna()].reset_index(drop=True)

    def horses(self, years: list[int], early: GroupForecast, late: GroupForecast, finish: GroupForecast) -> pd.DataFrame:
        data = self._datasets.horses
        ids = data.ids[pd.to_datetime(data.ids[RACE_DATE]).dt.year.isin(years)]
        frame = pd.concat([
            ids[[RACE_ID, HORSE_ID]].rename(columns={RACE_ID: "race_id"}),
            data.evaluation.loc[ids.index, [WIN_ODDS, POPULARITY]].rename(columns={WIN_ODDS: "win_odds", POPULARITY: "popularity"}),
            data.targets.loc[ids.index].drop(columns=[FINISH], errors="ignore"),
            data.features.loc[ids.index, [RECENT_CORNER4, RECENT_CLOSING, LEAD_RATE, STYLE, PREVIOUS_POSITION]],
            early.horse_rows(ids), late.horse_rows(ids), finish.horse_rows(ids),
        ], axis=1)
        frame[FINISH] = data.evaluation.loc[ids.index, FINISH]
        frame[YEAR] = pd.to_datetime(ids[RACE_DATE]).dt.year.astype(str)
        frame[TOP3_PROBABILITY] = self._top3(frame)
        return frame.reset_index(drop=True)

    def races(self, years: list[int], early: GroupForecast, late: GroupForecast) -> pd.DataFrame:
        data = self._datasets.races
        ids = data.ids[pd.to_datetime(data.ids[RACE_DATE]).dt.year.isin(years)]
        frame = pd.concat([
            ids[[RACE_ID]].rename(columns={RACE_ID: "race_id"}), data.targets.loc[ids.index],
            data.features.loc[ids.index, [LEAD_CANDIDATES]], early.race_rows(ids), late.race_rows(ids),
        ], axis=1)
        frame[YEAR] = pd.to_datetime(ids[RACE_DATE]).dt.year.astype(str)
        return frame.reset_index(drop=True)

    def unlabeled(self) -> pd.DataFrame:
        """学習データの全部のレースの、正解を作らなかった理由を数えるための列。"""
        data = self._datasets.races
        evaluation = data.evaluation
        return pd.DataFrame({
            "race_id": data.ids[RACE_ID].astype(str),
            unlabeled.YEAR: pd.to_datetime(data.ids[RACE_DATE]).dt.year.astype(str),
            unlabeled.VENUE: data.ids[VENUE].astype(str),
            unlabeled.FIELD_SIZE: data.features[FIELD_SIZE],
            unlabeled.PACE_NAME: data.targets[names.PACE_CLASS].map(dict(enumerate(names.PACE_CLASS_NAMES))),
            names.TRACK_CODE: evaluation[names.TRACK_CODE],
            names.FIRST_CORNER_NO: evaluation[names.FIRST_CORNER_NO],
            names.CORNER_LAPS_OVER_ONE: evaluation[names.CORNER_LAPS_OVER_ONE],
            names.FIRST_CORNER_LEADER_NO: evaluation[names.FIRST_CORNER_LEADER_NO],
            names.FIRST_HALF_TIME: evaluation[names.FIRST_HALF_TIME],
            names.SECOND_HALF_TIME: evaluation[names.SECOND_HALF_TIME],
            unlabeled.FIRST_STAGE: evaluation[unlabeled.FIRST_STAGE],
            unlabeled.SECOND_STAGE: evaluation[unlabeled.SECOND_STAGE],
        })

    def _year_rows(self, ids: pd.DataFrame, year: int) -> pd.DataFrame:
        return ids[pd.to_datetime(ids[RACE_DATE]).dt.year == year]

    def _top3(self, frame: pd.DataFrame) -> np.ndarray:
        """各馬の3着以内の確率（Harville の式。その年の λ を使う）。1着の確率が無い馬は欠損値。"""
        top3 = np.full(len(frame), np.nan)
        usable = frame[WIN_PROBABILITY].notna().to_numpy()
        win, lam = frame[WIN_PROBABILITY].to_numpy(), frame[ORDER_LAMBDA].to_numpy()
        races = frame["race_id"].where(usable)
        for rows in races.groupby(races).indices.values():
            top3[rows] = self._order.places(win[rows], float(lam[rows[0]]))[:, 2]
        return top3
