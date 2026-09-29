"""作り方1つを、7つの区切りで学習して予測する。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from 既存モデルの改善.analysis.windows import WINDOWS

from .experiment import Experiment
from .feature import RaceRelativeColumns, SalePriceFeatures
from .model import CatBoostWindowModel, LightGBMWindowModel, WalkForward
from .source import AbilityTableSource, FormTableSource


class ExperimentRunner:
    """表を読み（同じ表は1回だけ）、作り方どおりに材料をそろえて、7つの区切りの予測を返す。

    ``tables`` は研究「既存モデルの改善」の表の置き場所、``ability_cache`` は研究「馬の力と展開でオッズに勝つ」の
    中間データの置き場所、``sales`` はセリの価格の中間データ（``extract_sales.py`` が作る）。
    """

    def __init__(self, tables: Path, ability_cache: Path, sales: Path) -> None:
        self._sources = {"form": FormTableSource(tables), "ability": AbilityTableSource(ability_cache)}
        self._sales = sales
        self._frames: dict[str, pd.DataFrame] = {}

    def run(self, experiment: Experiment) -> tuple[pd.DataFrame, dict[str, list[int]]]:
        """（予測の表, モデルごとの区切りごとの木の数）。2つのモデルなら ``score`` は確率の平均。"""
        frame = self._frame(experiment.source).copy()
        if experiment.first_day is not None:
            frame = frame[frame["開催日"] >= experiment.first_day].reset_index(drop=True)
        columns = self._columns(experiment, frame)
        results = {name: WalkForward(self._model(name, experiment), WINDOWS).run(frame, columns) for name in experiment.models}
        predictions = next(iter(results.values()))[0].copy()
        predictions["score"] = sum(prediction["score"] for prediction, _ in results.values()) / len(results)
        return predictions, {name: trees for name, (_, trees) in results.items()}

    def _frame(self, source: str) -> pd.DataFrame:
        if source not in self._frames:
            self._frames[source] = self._sources[source].read()
        return self._frames[source]

    def _columns(self, experiment: Experiment, frame: pd.DataFrame) -> list[str]:
        source = self._sources[experiment.source]
        columns = list(dict.fromkeys(column for name in experiment.sets for column in source.columns(name)))
        for group in experiment.without:
            columns = source.without(columns, group)
        if experiment.sales:
            columns += SalePriceFeatures().add(frame, pd.read_parquet(self._sales))
        if experiment.relative:
            columns += RaceRelativeColumns().add(frame, columns)
        return columns

    @staticmethod
    def _model(name: str, experiment: Experiment):
        if name == "catboost":
            return CatBoostWindowModel()
        return LightGBMWindowModel(experiment.params)
