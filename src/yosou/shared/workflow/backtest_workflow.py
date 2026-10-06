"""テスト期間の確かめの流れを進める。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
import pandas as pd

from ..dataset import (
    HORSE_ID,
    HORSE_NO,
    RACE_DATE,
    RACE_ID,
    TOP3,
    FinishPowerFreeData,
    PeriodSplitter,
    PoolFreeData,
    PoolFreeRows,
    TrainingData,
    TrainingPeriod,
    WinTargetData,
)
from ..dataset.column_names import FIELD_SIZE
from ..evaluation import BacktestReport, ModelEvaluator
from ..evaluation.model_evaluator import ENSEMBLE_NAME
from ..feature import POOL_SUPPORT_NAMES, PredictionTiming
from ..feature.odds import TOP3_RATE, WIN_RATE
from ..ml_model import MEMBER_TYPES, EnsembleModel, Member
from ..repository import ModelRepository

#: 市場の確率の行の名前（前日・当日。オッズから見た3着以内率・勝率をそのまま確率としたもの）と、
#: オッズの無い時点の基準の行の名前（3 ÷ 頭数、1 ÷ 頭数）。
MARKET_NAME = "市場の確率"
FIELD_SHARE_NAME = "頭数から見た割合"
#: 予測の表（道具「印の成績」が読む形）の列。
PREDICTION_COLUMNS: tuple[str, ...] = ("レースID", "開催日", "馬ID", "馬番", "確率", "区切り", "期間", "区分")
_FOLD, _PERIOD, _SEGMENT = "テスト期間", "テスト", "全体"
#: 確率を 0・1 に張り付かせない幅。
_EPSILON = 1e-6
#: 目的変数ごとの、市場の確率の列と、3着以内（1着）に入る頭数。
_MARKET_COLUMNS: dict[str, tuple[str, int]] = {TOP3: (TOP3_RATE, 3)}


class BacktestWorkflow:
    """テスト期間の確かめの流れ（地方の設計書 05 の図4・16 の 4）。

    学習データ（テスト期間を含む）からテスト期間の行だけを残し、時点ごとに保存したモデル（3着以内・1着）で予測し直し、
    当たり具合（モデル2つ・平均）と、市場の確率（オッズの無い時点は頭数から見た割合）の当たり具合を同じ指標で測る。
    予測の表は、道具「印の成績」が読む形で ``predictions_root`` に書く（``<時点>.pkl``・``<時点>-1着.pkl``）。

    ``models_root`` は3着以内のモデルの置き場所。1着のモデルは ``<models_root>/<win_folder>/``、券種オッズなしは
    ``<models_root>/<pool_free_folder>/``（その1着は ``<models_root>/<pool_free_folder>/<win_folder>/``。``train`` の置き方と同じ）。
    当日に券種のオッズが無いレースの行は、券種オッズなしのモデルで予測する（``PoolFreeRows``。06 の図3）。
    """

    def __init__(self, models_root: Path, timings: Sequence[PredictionTiming], predictions_root: Path,
                 pool_free_folder: str | None = None, win_folder: str | None = None,
                 member_types: Sequence[type[Member]] = MEMBER_TYPES) -> None:
        self._models_root = Path(models_root)
        self._timings = tuple(timings)
        self._predictions_root = Path(predictions_root)
        self._pool_free_folder = pool_free_folder
        self._win_folder = win_folder
        self._member_types = tuple(member_types)
        self._evaluator = ModelEvaluator()
        self._pool_free_rows = PoolFreeRows()

    def run(self, data: TrainingData, period: TrainingPeriod) -> BacktestReport:
        """``data`` は ``period`` で作った学習データ（テスト期間を含む）。"""
        test = PeriodSplitter(period).split(data).test
        report = BacktestReport(period, test)
        pool_free_root = self._models_root / str(self._pool_free_folder)
        targets = {TOP3: (FinishPowerFreeData().training(test), self._models_root, pool_free_root)}
        if self._win_folder is not None:
            win = WinTargetData().training(test)
            targets[win.label_name] = (win, self._models_root / self._win_folder, pool_free_root / self._win_folder)
        for label, (target, root, free_root) in targets.items():
            report.evaluations[label] = []
            report.prediction_paths[label] = {}
            for timing in self._timings:
                probabilities = self._predict(target, timing, root, free_root)
                timed = target.for_timing(timing)
                report.evaluations[label] += self._evaluator.evaluate_probabilities(timing, timed, probabilities)
                report.evaluations[label] += self._market_evaluation(label, timing, timed)
                report.prediction_paths[label][timing] = self._write(label, timing, target, probabilities)
        return report

    def _predict(self, target: TrainingData, timing: PredictionTiming, root: Path, pool_free_root: Path) -> dict[str, np.ndarray]:
        """時点のモデルで、行ごとの確率（モデルごとと平均）。N を使う時点（当日）では、券種のオッズの無いレースの行を券種オッズなしのモデルで出す。"""
        uses_pools = self._pool_free_folder is not None and bool(set(POOL_SUPPORT_NAMES) & set(target.catalog.columns_for(timing)))
        pool_free = self._pool_free_rows.of(target) if uses_pools else pd.Series(False, index=target.ids.index)
        parts: list[pd.DataFrame] = []
        if (~pool_free).any():
            parts.append(self._predict_rows(target.where(~pool_free), timing, root))
        if pool_free.any():
            free = PoolFreeData().training(target.where(pool_free))
            parts.append(self._predict_rows(free, timing, pool_free_root))
        joined = pd.concat(parts).loc[target.ids.index]
        return {name: joined[name].to_numpy() for name in joined.columns}

    def _predict_rows(self, data: TrainingData, timing: PredictionTiming, root: Path) -> pd.DataFrame:
        """``root`` の時点のモデルで、``data`` の行の確率（列はモデルの名前と平均。index は行の index）。"""
        timed = data.for_timing(timing)
        ensemble = EnsembleModel(ModelRepository(root, self._member_types).load(timing))
        members = ensemble.predict_members(timed)
        return pd.DataFrame({**members, ENSEMBLE_NAME: ensemble.combine(members)}, index=timed.ids.index)

    def _market_evaluation(self, label: str, timing: PredictionTiming, timed: TrainingData):
        """市場の確率（オッズの無い時点は頭数から見た割合）の当たり具合の行。"""
        column, places = _MARKET_COLUMNS.get(label, (WIN_RATE, 1))
        share = places / pd.to_numeric(timed.evaluation[FIELD_SIZE], errors="coerce")
        if timing is PredictionTiming.THURSDAY:
            probability, name = share, FIELD_SHARE_NAME
        else:
            probability, name = pd.to_numeric(timed.evaluation[column], errors="coerce").fillna(share), MARKET_NAME
        clipped = probability.fillna(0.5).clip(_EPSILON, 1 - _EPSILON).to_numpy()
        return self._evaluator.evaluate_probabilities(timing, timed, {name: clipped})

    def _write(self, label: str, timing: PredictionTiming, target: TrainingData,
               probabilities: dict[str, np.ndarray]) -> Path:
        """予測の表を書く。列は ``PREDICTION_COLUMNS`` と、モデルごとの確率（モデルの名前のまま）。"""
        ids = target.ids
        table = pd.DataFrame({
            PREDICTION_COLUMNS[0]: ids[RACE_ID].astype(str).to_numpy(), PREDICTION_COLUMNS[1]: ids[RACE_DATE].to_numpy(),
            PREDICTION_COLUMNS[2]: ids[HORSE_ID].astype(str).to_numpy(), PREDICTION_COLUMNS[3]: ids[HORSE_NO].to_numpy(),
            PREDICTION_COLUMNS[4]: probabilities[ENSEMBLE_NAME], PREDICTION_COLUMNS[5]: _FOLD,
            PREDICTION_COLUMNS[6]: _PERIOD, PREDICTION_COLUMNS[7]: _SEGMENT,
            **{name: values for name, values in probabilities.items() if name != ENSEMBLE_NAME},
        })
        self._predictions_root.mkdir(parents=True, exist_ok=True)
        suffix = "" if label == TOP3 else f"-{label}"
        path = self._predictions_root / f"{timing.value}{suffix}.pkl"
        table.to_pickle(path)
        return path
