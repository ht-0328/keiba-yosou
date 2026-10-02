"""学習の結果を表にする。"""

from __future__ import annotations

from datetime import timedelta

from 共通.render import Table

from ..dataset import RACE_DATE, TrainingData
from ..evaluation import Evaluation, TrainingReport
from .cell_format import day_text, rounded


class TrainingReportTables:
    """学習の結果（``TrainingReport``）を、4つの表（期間・当たり具合・人気の基準との比べ方・保存したモデル）にする。

    目的変数の名前（``TrainingData.label_name``。例: 3着以内）は、表の見出しに使う。
    ``subject`` は表題の頭に付ける言葉（例: 区分の名前）。区分ごとに学習するとき、どの表か分かるようにする。
    """

    def __init__(self, report: TrainingReport, subject: str = "") -> None:
        self._report = report
        self._subject = f"{subject}: " if subject else ""
        self._label_name = report.split.train.label_name

    def tables(self) -> list[Table]:
        return [self._periods(), self._evaluations(), self._popularity_comparison(), self._model_folders()]

    def _periods(self) -> Table:
        parts = self._report.split.parts()
        return Table(
            ["区分", "最初の開催日", "最後の開催日", "行数", f"{self._label_name}の割合"],
            [self._warmup_row(), *(self._period_row(name, part) for name, part in parts.items())],
            title=f"{self._subject}学習データの期間",
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
        top_pick = f"確率1位の馬の{self._label_name}率"
        return Table(
            ["時点", "モデル", "木の数", "行数", "ログ損失", "AUC", "Brier", top_pick],
            [self._evaluation_row(evaluation) for evaluation in self._report.evaluations],
            title=f"{self._subject}検証データでの当たり具合",
            note=f"ログ損失・Brier は小さいほど、AUC・{top_pick}は大きいほど良い"
                 "（指標の意味は穴馬の設計書 16）。",
        )

    def _evaluation_row(self, evaluation: Evaluation) -> list[object]:
        return [
            evaluation.timing.label, evaluation.model, evaluation.tree_count, evaluation.rows,
            rounded(evaluation.log_loss), rounded(evaluation.auc), rounded(evaluation.brier),
            rounded(evaluation.top_pick_place_rate),
        ]

    def _popularity_comparison(self) -> Table:
        label = self._label_name
        return Table(
            [
                "時点", "モデル", f"確率1位の馬の{label}率", f"人気最上位の馬の{label}率",
                "確率1位の馬の複勝回収率", "人気最上位の馬の複勝回収率", "人気の中での AUC",
            ],
            [self._comparison_row(evaluation) for evaluation in self._report.evaluations],
            title=f"{self._subject}人気の基準との比べ方",
            note="人気最上位の馬は、各レースで確定単勝人気がいちばん上の馬（全頭の予想なら 1番人気、穴馬の予想なら 4番か 6番人気）。"
                 "確率1位の値が人気最上位と同じなら、モデルは人気順をなぞっているだけである。"
                 "人気の中での AUC は、同じ人気の馬どうしで比べた AUC で、0.5 なら人気で説明できないところを何も当てていない。"
                 "複勝回収率は、複勝を 100円ずつ買ったときの払戻の合計 ÷ 買った金額（1 で元返し）。",
        )

    def _comparison_row(self, evaluation: Evaluation) -> list[object]:
        return [
            evaluation.timing.label, evaluation.model,
            rounded(evaluation.top_pick_place_rate), rounded(evaluation.popularity_pick_place_rate),
            rounded(evaluation.top_pick_place_payback), rounded(evaluation.popularity_pick_place_payback),
            rounded(evaluation.auc_within_popularity),
        ]

    def _model_folders(self) -> Table:
        catalog = self._report.split.train.catalog
        folders = self._report.model_folders
        return Table(
            ["時点", "特徴量の数", "保存したフォルダ"],
            [[timing.label, len(catalog.columns_for(timing)), str(folder)]
             for timing, folder in folders.items()],
            title=f"{self._subject}保存したモデル",
        )
