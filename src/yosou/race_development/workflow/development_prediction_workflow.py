"""1レースの予測の流れを進める。"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from 共通 import db

from yosou.shared.betting import TicketType
from yosou.shared.dataset import HORSE_NAME, HORSE_NO, RACE_DATE, OddsInput, PredictionData
from yosou.shared.dataset.column_names import WIN_ODDS
from yosou.shared.feature import PredictionTiming

from ..betting import MarkAssigner, MarkTicketRule
from ..betting import column_names as bet
from ..feature import (
    BACK_PROBABILITY,
    TOP3_PROBABILITY,
    UPSET_BETS,
    big_upset_probability,
    CLOSING_PREDICTION,
    CORNER4_PREDICTION,
    EVEN_PROBABILITY,
    FIRST_HALF_QUANTILES,
    FRONT_PROBABILITY,
    HIGH_PROBABILITY,
    LEADER_PROBABILITY,
    MIDDLE_PROBABILITY,
    SECOND_HALF_QUANTILES,
    SLOW_PROBABILITY,
    WIN_PROBABILITY,
    GroupForecast,
    PriorForecasts,
)
from ..ml_model import OrderProbability
from ..repository import PredictionArchiveRepository
from ..tendency import TendencyForecaster, TendencyModelStore
from .development_forecast import DevelopmentForecast
from .forecast_group import ForecastGroup
from .group_predictor import GroupPredictor
from .kind_model_store import KindModelStore
from .race_inputs import RaceInputs


class DevelopmentPredictionWorkflow:
    """1レースを、その時点のモデルで傾向（既存の予想）→ 前半 → 後半 → 着順の順に予測し、印と印どおりの買い目まで出して残す
    （設計書 05 の図2）。

    ほかのクラスを順に呼ぶだけで、自分では計算しない。元DB を開くのは、予測用データを作る段だけ。
    """

    def __init__(self, models_root: Path, archive_root: Path, db_path: Path | None) -> None:
        self._store = KindModelStore(models_root)
        self._tendency = TendencyForecaster(TendencyModelStore(models_root))
        self._archive = PredictionArchiveRepository(archive_root)
        self._db_path = db_path
        self._groups = GroupPredictor(self._store)
        self._order = OrderProbability()

    def run(self, race_id: str, timing: PredictionTiming, given_odds: OddsInput | None = None) -> DevelopmentForecast:
        """``given_odds`` は利用者が ``--odds`` で渡した単勝オッズ（省略すると、締め切り前のオッズか元DB の単勝オッズ）。

        人気は、オッズの小さい順に決める（人気馬・穴馬の予想が、行を選ぶのに使う）。
        前日・当日の既存の予想は、オッズから見た確率を出発点にするので、オッズが決められなければ ``ValueError``。
        """
        with db.open_db(self._db_path) as con:
            inputs = RaceInputs.read(con, race_id, timing, given_odds)
        horses, races = inputs.horses, inputs.races
        priors = PriorForecasts(self._tendency.predict(inputs.tendency))
        priors = priors.with_early(self._groups.predict(ForecastGroup.EARLY, horses, races, priors, timing))
        priors = priors.with_late(self._groups.predict(ForecastGroup.LATE, horses, races, priors, timing))
        finish = self._groups.predict(ForecastGroup.FINISH, horses, races, priors, timing)
        forecast = self._forecast(race_id, timing, horses, races, priors, finish)
        self._archive.save(str(horses.ids[RACE_DATE].iloc[0])[:10], race_id, timing.value, datetime.now(), {
            "horse_features": horses.features, "race_features": races.features,
            "horses": forecast.horses, "race": forecast.race, "tickets": forecast.tickets,
        })
        return forecast

    def _forecast(self, race_id: str, timing: PredictionTiming, horses: PredictionData, races: PredictionData,
                  priors: PriorForecasts, finish: GroupForecast) -> DevelopmentForecast:
        """予測をまとめて、1頭ごとの表・レースの1行・印どおりの買い目にする。"""
        ids, early, late, tendency = horses.ids, priors.early, priors.late, priors.tendency
        win = finish.horse_rows(ids)[WIN_PROBABILITY].to_numpy()
        places = self._order.places(win, self._store.load_lambda(timing))
        early_horses, late_horses = early.horse_rows(ids), late.horse_rows(ids)
        marked = MarkAssigner().assign(pd.DataFrame({
            bet.HORSE_NO: pd.to_numeric(ids[HORSE_NO], errors="coerce"), bet.WIN_PROBABILITY: win,
            bet.WIN_ODDS: self._win_odds(horses), bet.LEADER_PROBABILITY: early_horses[LEADER_PROBABILITY],
        }, index=ids.index))
        table = pd.DataFrame({
            "馬番": ids[HORSE_NO], "馬名": ids[HORSE_NAME], "印": marked[bet.MARK],
            "1着の確率": places[:, 0], "2着以内の確率": places[:, 1], "3着以内の確率": places[:, 2],
            "先頭の確率": early_horses[LEADER_PROBABILITY], "先団の確率": early_horses[FRONT_PROBABILITY],
            "中団の確率": early_horses[MIDDLE_PROBABILITY], "後方の確率": early_horses[BACK_PROBABILITY],
            "4コーナーの位置の予測": late_horses[CORNER4_PREDICTION], "上がりの速さの予測": late_horses[CLOSING_PREDICTION],
            "既存の予想の3着以内の確率": tendency.horse_rows(ids)[TOP3_PROBABILITY],
        }, index=ids.index).sort_values("1着の確率", ascending=False).reset_index(drop=True)
        return DevelopmentForecast(race_id, timing, table, self._race_row(races, priors),
                                   self._tickets(race_id, marked))

    def _race_row(self, races: PredictionData, priors: PriorForecasts) -> pd.DataFrame:
        """既存の予想の荒れ具合（大荒れ以上の確率）、ハイ・平均・スローの確率と、前半・後半タイムの秒数（基準 + 予測した差）。"""
        first, second = priors.early.race_rows(races.ids), priors.late.race_rows(races.ids)
        upsets = priors.tendency.race_rows(races.ids)
        first_base = pd.to_numeric(races.features["前半タイムの基準"], errors="coerce").to_numpy()
        second_base = pd.to_numeric(races.features["後半タイムの基準"], errors="coerce").to_numpy()
        low, middle, high = (first[column].to_numpy() + first_base for column in FIRST_HALF_QUANTILES)
        late_low, late_middle, late_high = (second[column].to_numpy() + second_base for column in SECOND_HALF_QUANTILES)
        return pd.DataFrame({
            **{f"大荒れ以上の確率（{label}）": upsets[big_upset_probability(key)].to_numpy() for key, label in UPSET_BETS.items()},
            "ハイの確率": first[HIGH_PROBABILITY].to_numpy(), "平均の確率": first[EVEN_PROBABILITY].to_numpy(),
            "スローの確率": first[SLOW_PROBABILITY].to_numpy(),
            "前半タイム（秒）": middle, "前半タイムの 80% の幅": [f"{a:.1f}〜{b:.1f}" for a, b in zip(low, high)],
            "後半タイム（秒）": late_middle, "後半タイムの 80% の幅": [f"{a:.1f}〜{b:.1f}" for a, b in zip(late_low, late_high)],
        })

    def _tickets(self, race_id: str, marked: pd.DataFrame) -> pd.DataFrame:
        """券種ごとの、印どおりの買い目。馬番の決まっていない時点（木曜）は出さない。"""
        if marked[bet.HORSE_NO].isna().any():
            return pd.DataFrame(columns=["券種", "組番", "金額（円）"])
        rule = MarkTicketRule()
        tickets = pd.concat([rule.tickets(race_id, marked, ticket_type) for ticket_type in TicketType], ignore_index=True)
        labels = {ticket_type.key: ticket_type.label for ticket_type in TicketType}
        return pd.DataFrame({"券種": tickets[bet.TICKET_TYPE].map(labels), "組番": tickets[bet.COMBO],
                             "金額（円）": tickets[bet.STAKE]})

    def _win_odds(self, horses: PredictionData) -> np.ndarray:
        """その時点の単勝オッズ（前日・当日。木曜は欠損値）。"""
        if horses.market is None or WIN_ODDS not in horses.market.columns:
            return np.full(len(horses), np.nan)
        return pd.to_numeric(horses.market[WIN_ODDS], errors="coerce").to_numpy()
