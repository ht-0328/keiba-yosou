"""詳しく見る日の流れ: 最後の区切りまでの全部の行で人気薄の1着の予想を学び、その日の対象レースを今のモデルの予測の流れで予測し直して、
``FocusDayStudy`` の表を作る。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import duckdb
import numpy as np
import pandas as pd

from 共通.render import Table

from yosou.form_aptitude_materials import MaterialAttachers
from yosou.form_aptitude_win5_tickets.command.form_models_argument import DEFAULT_FORM_MODELS
from yosou.form_aptitude_win5_tickets.payout import PayoutEstimator
from yosou.form_aptitude_win5_tickets.repository import PayoutEstimatorRepository, Win5HistoryRepository
from yosou.form_aptitude_win5_tickets.repository.win5_columns import HORSE_NO, RACE_ID, WIN_ODDS
from yosou.shared.command.development_root_argument import DEFAULT_DEVELOPMENT_ROOT
from yosou.shared.feature import PredictionTiming
from yosou.shared.workflow import WIN_PROBABILITY, FormAptitudePrediction

from 既存モデルの改善.analysis.windows.test_window import TestWindow

from ..longshot_forecast.combined_win_share import CombinedWinShare
from ..longshot_forecast.focus_day_data import FocusDayData
from ..longshot_forecast.longshot_data import LongshotData
from ..longshot_forecast.longshot_variant import CURRENT_BASELINE, LONGSHOT_FROM, LongshotVariant
from ..longshot_forecast.longshot_window_trainer import LongshotWindowTrainer
from ..repository import Win5LegRepository, WinnerRepository
from .focus_day_study import FocusDayStudy
from .hedge_candidate import HedgeCandidate

#: 最後に学ぶときの検証の半年（学習の表の最後の日まで）。
_FINAL_WINDOW = TestWindow("最後", date(2026, 4, 13), date(2026, 10, 13), date(2026, 12, 31))
_EDGE = 1e-4
_PAYOUT_ROOT = DEFAULT_FORM_MODELS.parents[1] / "近走と適性からWIN5の買い目を決める"


@dataclass(frozen=True)
class FocusDayRunner:
    """``data`` は学習データ（当日の時点・作り方の行）、``type_features`` は型の材料、``handicap`` はハンデ戦のレースID。"""

    trainer: LongshotWindowTrainer
    variant: LongshotVariant
    data: LongshotData
    type_features: pd.DataFrame
    handicap: frozenset[str]

    def tables(self, con: duckdb.DuckDBPyConnection, race_date: str, candidates: Sequence[HedgeCandidate]) -> list[Table]:
        legs = Win5LegRepository(con).load(date.fromisoformat(race_date))
        race_ids = [str(rid) for rid in legs.loc[legs["race_date"] == race_date].sort_values("leg")["race_id"]]
        if len(race_ids) != 5:
            return [Table(["項目", "内容"], [["詳しく見る日", f"{race_date} の WIN5 の対象レースが元DB にそろっていない"]], title="詳しく見る日")]
        prediction = FormAptitudePrediction(DEFAULT_FORM_MODELS, lambda c: MaterialAttachers(c, DEFAULT_DEVELOPMENT_ROOT))
        focus, current = FocusDayData(prediction, self.type_features, list(self.data.features.columns), self.data.categorical).build(
            con, race_ids, PredictionTiming.RACE_DAY)
        members, train = self.trainer.fit(self.data, _FINAL_WINDOW, self.variant)
        focus = self._on_current(focus, current) if self.variant.baseline == CURRENT_BASELINE else focus
        longshots = focus.where(focus.popularity >= LONGSHOT_FROM)
        probability = np.mean(np.stack(list(self.trainer.probabilities(members, train, longshots, self.variant).values())), axis=0)
        new = self._combined(current, longshots, probability)
        winners = tuple(WinnerRepository(con).of(race_id) for race_id in race_ids)
        history = Win5HistoryRepository(con).read(date.fromisoformat(race_date))
        estimator = PayoutEstimator.from_dict(PayoutEstimatorRepository(_PAYOUT_ROOT).load())
        study = FocusDayStudy(self._legs(current, race_ids), self._legs(new, race_ids), winners)
        return study.tables(race_date, history, estimator, self.handicap, candidates)

    @staticmethod
    def _on_current(focus: LongshotData, current: pd.DataFrame) -> LongshotData:
        """出発点を、今のモデルのそろえた1着の確率のロジットに替える。"""
        share = current[WIN_PROBABILITY] / current.groupby(RACE_ID)[WIN_PROBABILITY].transform("sum")
        keyed = current.assign(share=share)[[RACE_ID, HORSE_NO, "share"]].astype({RACE_ID: str, HORSE_NO: int})
        merged = focus.ids[[RACE_ID, HORSE_NO]].astype({HORSE_NO: int}).merge(keyed, on=[RACE_ID, HORSE_NO], how="left")["share"]
        clipped = merged.clip(_EDGE, 1 - _EDGE).to_numpy()
        return LongshotData(focus.ids, focus.features, focus.label, pd.Series(np.log(clipped / (1 - clipped))), focus.popularity,
                            focus.market, focus.categorical)

    @staticmethod
    def _combined(current: pd.DataFrame, longshots: LongshotData, probability: np.ndarray) -> pd.DataFrame:
        prepared = current.rename(columns={RACE_ID: "race_id", HORSE_NO: "horse_no", WIN_PROBABILITY: "probability"}).assign(
            race_date="", horse_id="", fold="", period="", segment="")
        replaced = pd.DataFrame({"レースID": longshots.ids[RACE_ID].to_numpy(), "馬番": longshots.ids[HORSE_NO].astype(int).to_numpy(),
                                 "確率": probability, "人気": longshots.popularity.to_numpy()})
        combined = CombinedWinShare().combine(prepared[["race_id", "race_date", "horse_id", "horse_no", "probability", "fold", "period", "segment"]],
                                              replaced)
        odds = current[[RACE_ID, HORSE_NO, WIN_ODDS]].astype({RACE_ID: str, HORSE_NO: int})
        return combined.rename(columns={"確率": WIN_PROBABILITY})[[RACE_ID, HORSE_NO, WIN_PROBABILITY]].merge(odds, on=[RACE_ID, HORSE_NO])

    @staticmethod
    def _legs(table: pd.DataFrame, race_ids: Sequence[str]) -> list[pd.DataFrame]:
        typed = table.astype({RACE_ID: str})
        return [typed.loc[typed[RACE_ID] == race_id, [RACE_ID, HORSE_NO, WIN_ODDS, WIN_PROBABILITY]].reset_index(drop=True) for race_id in race_ids]
