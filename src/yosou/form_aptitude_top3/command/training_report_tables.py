"""学習の結果を表にする。"""

from __future__ import annotations

from datetime import timedelta

from 共通.render import Table

from ..dataset import RACE_DATE, TrainingData
from ..evaluation import Evaluation
from ..workflow import TrainingReport
from .cell_format import day_text, rounded


class TrainingReportTables:
    """学習の結果（``TrainingReport``）を、3つの表（期間・当たり具合・保存したモデル）にする。"""

    def __init__(self, report: TrainingReport) -> None:
        self._report = report

    def tables(self) -> list[Table]:
        return [self._periods(), self._evaluations(), self._model_folders()]

    def _periods(self) -> Table:
        parts = self._report.split.parts()
        return Table(
            ["区分", "最初の開催日", "最後の開催日", "行数", "3着以内の割合"],
            [self._warmup_row(), *(self._period_row(name, part) for name, part in parts.items())],
            title="学習データの期間",
            note="ウォームアップは過去走の計算にだけ使い、サンプルにしない。"
                 "テストデータは最後に1回だけ確かめる用なので、ここでは当たり具合を測らない。",
        )

    def _warmup_row(self) -> list[object]:
        """ウォームアップ期間の行。サンプルにしないので、行数と割合は空欄。"""
        period = self._report.period
        last_day = period.train_first_day - timedelta(days=1)
        return ["ウォームアップ", period.warmup_first_day.isoformat(), last_day.isoformat(), None, None]

    def _period_row(self, name: str, part: TrainingData) -> list[object]:
        days = part.ids[RACE_DATE]
        return [name, day_text(days.min()), day_text(days.max()), len(part), rounded(part.label.mean())]

    def _evaluations(self) -> Table:
        return Table(
            ["時点", "モデル", "木の数", "行数", "ログ損失", "AUC", "Brier", "確率1位の馬の3着以内率"],
            [self._evaluation_row(evaluation) for evaluation in self._report.evaluations],
            title="検証データでの当たり具合",
            note="ログ損失・Brier は小さいほど、AUC・確率1位の馬の3着以内率は大きいほど良い。"
                 "評価指標は仮（設計書で次に決める）。",
        )

    def _evaluation_row(self, evaluation: Evaluation) -> list[object]:
        return [
            evaluation.timing.label, evaluation.model, evaluation.tree_count, evaluation.rows,
            rounded(evaluation.log_loss), rounded(evaluation.auc), rounded(evaluation.brier),
            rounded(evaluation.top_pick_place_rate),
        ]

    def _model_folders(self) -> Table:
        folders = self._report.model_folders
        return Table(
            ["時点", "特徴量の数", "保存したフォルダ"],
            [[timing.label, len(timing.feature_columns()), str(folder)]
             for timing, folder in folders.items()],
            title="保存したモデル",
        )
