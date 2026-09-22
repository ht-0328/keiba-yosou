"""多クラス分類の学習の結果を表にする。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta

from 共通.render import Table

from ..dataset import RACE_DATE, TrainingData
from ..evaluation import ENSEMBLE_NAME, ClassEvaluation, TrainingReport
from .cell_format import day_text, rounded


class ClassTrainingReportTables:
    """多クラス分類の学習の結果（``TrainingReport``）を、4つの表（期間・当たり具合・混同行列・保存したモデル）にする
    （荒れ具合の設計書 16）。

    ``class_names`` はクラスの番号の順の名前（例: 固い・中荒れ・大荒れ・超荒れ）。表の見出しに使う。
    ``subject`` は表題の頭に付ける言葉（例: 券種の名前）。券種ごとに学習するとき、どの表か分かるようにする。
    """

    def __init__(self, report: TrainingReport, class_names: Sequence[str], subject: str = "") -> None:
        self._report = report
        self._class_names = tuple(class_names)
        self._subject = f"{subject}: " if subject else ""
        self._label_name = report.split.train.label_name

    def tables(self) -> list[Table]:
        return [self._periods(), self._evaluations(), self._confusion_matrices(), self._model_folders()]

    def _periods(self) -> Table:
        parts = self._report.split.parts()
        share_columns = [f"{name}の割合" for name in self._class_names]
        return Table(
            ["区分", "最初の開催日", "最後の開催日", "行数", *share_columns],
            [self._warmup_row(), *(self._period_row(name, part) for name, part in parts.items())],
            title=f"{self._subject}学習データの期間（目的変数: {self._label_name}）",
            note="ウォームアップは近走と過去の荒れ率の計算にだけ使い、サンプルにしない。"
                 "テストデータは最後に1回だけ確かめる用なので、ここでは当たり具合を測らない。",
        )

    def _warmup_row(self) -> list[object]:
        """ウォームアップ期間の行。サンプルにしないので、行数と割合は空欄。"""
        period = self._report.period
        last_day = period.train_first_day - timedelta(days=1)
        empty = [None] * len(self._class_names)
        return ["ウォームアップ", period.warmup_first_day.isoformat(), last_day.isoformat(), None, *empty]

    def _period_row(self, name: str, part: TrainingData) -> list[object]:
        days = part.ids[RACE_DATE]
        shares = [rounded((part.label == label).mean()) for label in part.class_labels]
        return [name, day_text(days.min()), day_text(days.max()), len(part), *shares]

    def _evaluations(self) -> Table:
        auc_columns = [f"AUC（{name}以上）" for name in self._class_names[1:]]
        return Table(
            ["時点", "モデル", "木の数", "行数", "正解率", "マクロF1", "クラスのずれの平均", "ログ損失", *auc_columns],
            [self._evaluation_row(evaluation) for evaluation in self._report.evaluations],
            title=f"{self._subject}検証データでの当たり具合",
            note="正解率・マクロF1・AUC は大きいほど、クラスのずれの平均・ログ損失は小さいほど良い。"
                 "AUC（〇〇以上）は、そのクラス以上になる確率（累積確率）を二値の予測とみなした AUC。",
        )

    def _evaluation_row(self, evaluation: ClassEvaluation) -> list[object]:
        return [
            evaluation.timing.label, evaluation.model, evaluation.tree_count, evaluation.rows,
            rounded(evaluation.accuracy), rounded(evaluation.macro_f1), rounded(evaluation.mean_class_gap),
            rounded(evaluation.log_loss), *(rounded(auc) for auc in evaluation.cumulative_auc),
        ]

    def _confusion_matrices(self) -> Table:
        """アンサンブルの混同行列。1行 = 1つの時点の実際のクラス、列 = いちばん高いクラス。"""
        ensembles = [e for e in self._report.evaluations if e.model == ENSEMBLE_NAME]
        rows = [
            [evaluation.timing.label, actual_name, *counts]
            for evaluation in ensembles
            for actual_name, counts in zip(self._class_names, evaluation.confusion_matrix, strict=True)
        ]
        return Table(
            ["時点", "実際のクラス", *(f"予測: {name}" for name in self._class_names)], rows,
            title=f"{self._subject}混同行列（平均の予測）",
            note="行が実際のクラス、列がいちばん高いクラスの件数。対角線が当たり。隣の列への外れは、順序の近い外れ。",
        )

    def _model_folders(self) -> Table:
        catalog = self._report.split.train.catalog
        folders = self._report.model_folders
        return Table(
            ["時点", "特徴量の数", "保存したフォルダ"],
            [[timing.label, len(catalog.columns_for(timing)), str(folder)] for timing, folder in folders.items()],
            title=f"{self._subject}保存したモデル",
        )
