"""学習のあとに、時点ごと・人気帯ごとの危険度の線を検証期間で決めて保存する。"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import chain, product
from pathlib import Path

import pandas as pd

from 共通.render import Table

from yosou.shared.evaluation import TrainingReport
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import MEMBER_TYPES, EnsembleModel
from yosou.shared.repository import ModelRepository
from yosou.shared.workflow import ModelSegments

from ..danger import DangerThreshold
from ..dataset import FAVORITE_BAND
from ..repository import DangerThresholdRepository

#: 途中の表の列の名前。
_TIMING, _DANGER, _LOST = "時点", "危険度", "4着以下"


class DangerThresholdStep:
    """学習したモデルで検証データを予測し、危険度（予想 − オッズから見た4着以下の確率）と実際の4着以下から、
    時点ごと・人気帯ごとの線（``DangerThreshold``）を決めて、モデルの置き場所に保存する（既存モデルの修正計画の 1）。

    テストデータは使わない。保存した線の表を返す。
    """

    def run(self, reports: Sequence[tuple[str, TrainingReport]], segments: ModelSegments, models_root: Path,
            timings: Sequence[PredictionTiming]) -> Table:
        frames = [self._predicted(label, report, segments, models_root, timing)
                  for (label, report), timing in product(reports, timings)]
        valid = pd.concat(frames, ignore_index=True)
        chooser = DangerThreshold()
        lines = valid.groupby([_TIMING, FAVORITE_BAND]).apply(lambda group: chooser.choose(group[_DANGER], group[_LOST]))
        bands = list(valid[FAVORITE_BAND].unique())
        thresholds = {timing: self._lines_of(lines, timing, bands) for timing in timings}
        path = DangerThresholdRepository(models_root).save(thresholds)
        rows = list(chain.from_iterable(self._rows_of(timing, values) for timing, values in thresholds.items()))
        return Table(["時点", "人気帯", "危険度の線"], rows, title="危険の判定の線（検証データで決めた値）",
                     note=f"保存した場所: {path}。危険度 = 4着以下になる確率 − オッズから見た4着以下の確率。空欄は線を決められなかった人気帯。")

    def _lines_of(self, lines: pd.Series, timing: PredictionTiming, bands: list[str]) -> dict[str, float]:
        """1つの時点の、人気帯 → 線。決められなかった人気帯は NaN。"""
        return {band: float(lines.get((timing.value, band), float("nan"))) for band in bands}

    def _rows_of(self, timing: PredictionTiming, values: dict[str, float]) -> list[list[object]]:
        return [[timing.label, band, value] for band, value in values.items()]

    def _predicted(self, label: str, report: TrainingReport, segments: ModelSegments, models_root: Path,
                   timing: PredictionTiming) -> pd.DataFrame:
        """1つの区分・1つの時点の、検証データの危険度と実際の4着以下。"""
        valid = report.split.valid.for_timing(timing)
        models = ModelRepository(segments.root_of(models_root, label), MEMBER_TYPES).load(timing)
        probability = EnsembleModel(models).predict_proba(valid)
        danger = probability - valid.baseline.probabilities().to_numpy()
        return pd.DataFrame({_TIMING: timing.value, FAVORITE_BAND: valid.evaluation[FAVORITE_BAND].to_numpy(),
                             _DANGER: danger, _LOST: valid.label.to_numpy()})
