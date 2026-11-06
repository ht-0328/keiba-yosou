"""train の報告のうち、「荒れるレースだけ買う」使い方の線引きの材料の表。"""

from __future__ import annotations

from collections.abc import Mapping

from 共通.render import Table

from yosou.shared.command.cell_format import rounded
from yosou.shared.evaluation import TrainingReport
from yosou.shared.feature import PredictionTiming
from yosou.shared.ml_model import EnsembleModel
from yosou.shared.repository import ModelRepository
from yosou.upset_level.dataset import BetType
from yosou.upset_level.evaluation import UpsetThresholdSummary
from yosou.upset_level.evaluation.upset_threshold_summary import COLUMNS

from ..workflow import TIMING_LABELS

#: 推奨買目の 3連複が使う、3連複の中荒れ以上の確率の線（設計書「買うレースと買い目を決める」10）。表の注に出す。
TRIO_LINE = 0.6


class UpsetThresholdTable:
    """検証データで、時点ごとに「中荒れ以上の確率」のしきい値ごとのレース数・実際に中荒れ以上だった割合・中荒れ以上のうち選んだ割合を並べる
    （中央の ``UpsetThresholdSummary`` を時点ごとに回して1つの表にする）。

    推奨買目の 3連複は 3連複の中荒れ以上の確率 0.6 以上のレースだけ買うので、学び直したときに、その線で選ばれるレースの割合と
    実際に荒れた割合が前と大きく変わっていないかを、この表で見る。
    """

    def __init__(self, bet: BetType, report: TrainingReport, repository: ModelRepository,
                 timing_labels: Mapping[PredictionTiming, str] = TIMING_LABELS) -> None:
        self._bet = bet
        self._report = report
        self._repository = repository
        self._timing_labels = dict(timing_labels)

    def table(self) -> Table:
        rows: list[list[object]] = []
        for timing in self._report.model_folders:
            ensemble = EnsembleModel(self._repository.load(timing))
            summary = UpsetThresholdSummary().summarize(ensemble, self._report.split.valid.for_timing(timing))
            rows += [[self._timing_labels.get(timing, timing.label), *(rounded(value) if isinstance(value, float) else value for value in row)]
                     for row in summary.itertuples(index=False)]
        return Table(
            ["時点", *COLUMNS], rows,
            title=f"{self._bet.label}: 「荒れるレースだけ買う」使い方の線引き（検証データ）",
            note=f"中荒れ以上の確率がしきい値以上のレースを選んだときの、レース数と実際に中荒れ以上だった割合。"
                 f"推奨買目の 3連複は、3連複の中荒れ以上の確率 {TRIO_LINE:g} 以上のレースだけ買う（設計書「買うレースと買い目を決める」10）。",
        )
