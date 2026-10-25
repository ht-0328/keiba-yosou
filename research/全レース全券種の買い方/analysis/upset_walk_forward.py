"""荒れ具合の予想（当日）を、区切りごとに学び直して過去のレースの配当率を出す。"""

from __future__ import annotations

import sys
import time
from collections.abc import Sequence
from datetime import date

import numpy as np
import pandas as pd

from yosou.shared.dataset import TrainingData
from yosou.shared.dataset.column_names import RACE_DATE, RACE_ID
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import CLASS_MEMBER_TYPES, EnsembleModel
from yosou.shared.setting import HyperparameterSettings
from yosou.upset_level.dataset import BetType, UpsetLevel
from yosou.upset_level.workflow import BET, UPSET_OR_MORE

from .half_year_folds import Fold

#: 結果の表の列（券種ごとの行）。
FOLD, PAYOUT_RATE = "fold", "payout_rate"
COLUMNS: tuple[str, ...] = ("race_id", "race_date", FOLD, BET, *UpsetLevel.labels(), UPSET_OR_MORE)


class UpsetWalkForward:
    """荒れ具合の予想（``yosou.upset_level``。当日のモデル）を、半年の区切りごとに「学習の始まりから直前の半年の前まで学び、直前の半年で早期終了し、
    その区切りを予測」して、過去のレースの券種ごとの荒れ具合の確率を出す（docs/01 の手順2）。

    本番の荒れ具合のモデルは最新のデータまで学んでいるので、過去のレースにそのまま当てると答えを見た予測になる。区切りごとに学び直すと、
    道具「印の成績」の7つの区切りの予測と同じく、学習に使っていない期間の予測になる。
    学習データ（``TrainingData``。``race_dataset_builder(con).build_training_data(...)`` で学習の始まりから DB の最後まで）は1回だけ作り、
    区切りごとに開催日で分ける。モデルは券種ごとに LightGBM と CatBoost（本番と同じ初期値）で、保存はしない。
    結果は1行 = 1レース × 1券種（``COLUMNS``）。``payout_rates()`` で、レースごとの配当率（4券種の中荒れ以上の確率の平均）にする。
    """

    def __init__(self, settings: HyperparameterSettings, train_first_day: date = date(2012, 1, 1),
                 timing: PredictionTiming = PredictionTiming.RACE_DAY, bets: Sequence[BetType] = tuple(BetType)) -> None:
        self._settings = settings
        self._train_first_day = train_first_day
        self._timing = timing
        self._bets = tuple(bets)

    def run(self, data: TrainingData, folds: Sequence[Fold]) -> pd.DataFrame:
        frames = [self._fold(data, fold) for fold in folds]
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=list(COLUMNS))

    def _fold(self, data: TrainingData, fold: Fold) -> pd.DataFrame:
        train = data.between(self._train_first_day, fold.valid_first_day)
        valid = data.between(fold.valid_first_day, fold.first_day)
        test = data.between(fold.first_day, fold.next_first_day)
        if len(test) == 0:
            print(f"  {fold.name}: レースが無いので飛ばします", file=sys.stderr, flush=True)
            return pd.DataFrame(columns=list(COLUMNS))
        rows = []
        for bet in self._bets:
            started = time.monotonic()
            probabilities = self._predict(train, valid, test, bet)
            rows.append(pd.DataFrame({
                "race_id": test.ids[RACE_ID].astype(str).to_numpy(), "race_date": pd.to_datetime(test.ids[RACE_DATE]).to_numpy(),
                FOLD: fold.name, BET: bet.label,
                **{level.label: probabilities[:, level.value] for level in UpsetLevel},
                UPSET_OR_MORE: probabilities[:, UpsetLevel.MID.value:].sum(axis=1),
            }))
            print(f"  {fold.name} {bet.label}: 学習 {len(train):,}・検証 {len(valid):,}・予測 {len(test):,} レース（{time.monotonic() - started:.0f}秒）",
                  file=sys.stderr, flush=True)
        return pd.concat(rows, ignore_index=True)

    def _predict(self, train: TrainingData, valid: TrainingData, test: TrainingData, bet: BetType) -> np.ndarray:
        labels = UpsetLevel.class_labels()
        labeled = [part.with_label(bet.column_name, labels).for_timing(self._timing) for part in (train, valid)]
        members = [model_type.from_settings(self._settings).fit(*labeled) for model_type in CLASS_MEMBER_TYPES]
        return EnsembleModel(members).predict_proba(test.with_label(bet.column_name, labels).for_timing(self._timing))

    @staticmethod
    def payout_rates(predictions: pd.DataFrame) -> pd.DataFrame:
        """レースごとの配当率（4券種の中荒れ以上の確率の平均）と、券種ごとの中荒れ以上の確率の列。列は race_id・race_date・fold・<券種>・payout_rate。"""
        wide = predictions.pivot_table(index=["race_id", "race_date", FOLD], columns=BET, values=UPSET_OR_MORE, aggfunc="first")
        wide.columns = [str(column) for column in wide.columns]
        wide[PAYOUT_RATE] = wide[[bet.label for bet in BetType if bet.label in wide.columns]].mean(axis=1)
        return wide.reset_index()
