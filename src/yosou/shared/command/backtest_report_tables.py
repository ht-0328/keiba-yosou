"""テスト期間の確かめの結果を表にする。"""

from __future__ import annotations

from collections.abc import Mapping

from 共通.render import Table

from ..dataset import RACE_DATE, RACE_ID
from ..evaluation import BacktestReport, Evaluation
from ..feature import PredictionTiming
from .cell_format import day_text, rounded


class BacktestReportTables:
    """テスト期間の確かめの結果（``BacktestReport``）を、期間・目的変数ごとの当たり具合・書いた予測の表 の表にする。

    ``timing_labels`` は時点 → 表に出す名前（地方の予想は木曜の枠を「出馬表」と出す）。省略すると時点の名前のまま。
    """

    def __init__(self, report: BacktestReport, timing_labels: Mapping[PredictionTiming, str] | None = None) -> None:
        self._report = report
        self._timing_labels = dict(timing_labels or {})

    def tables(self) -> list[Table]:
        return [self._period(), *(self._evaluations(label, rows) for label, rows in self._report.evaluations.items()),
                self._prediction_files()]

    def _timing_label(self, timing: PredictionTiming) -> str:
        return self._timing_labels.get(timing, timing.label)

    def _period(self) -> Table:
        test = self._report.test
        days = test.ids[RACE_DATE]
        return Table(
            ["区分", "最初の開催日", "最後の開催日", "行数", "レース数"],
            [["テスト", day_text(days.min()), day_text(days.max()), len(test), test.ids[RACE_ID].nunique()]],
            title="テスト期間",
            note=f"学習 {self._report.period.train_first_day} 〜、検証 {self._report.period.valid_first_day} 〜 のモデルで、"
                 f"テスト {self._report.period.test_first_day} 〜 のレースを予測し直した（学習にも早期終了にも使っていない期間）。",
        )

    def _evaluations(self, label: str, evaluations: list[Evaluation]) -> Table:
        top_pick = f"確率1位の馬の{label}率"
        return Table(
            ["時点", "モデル", "行数", "ログ損失", "AUC", "Brier", top_pick, "確率1位の馬の複勝回収率",
             f"人気最上位の馬の{label}率", "人気最上位の馬の複勝回収率", "人気の中での AUC"],
            [self._row(evaluation) for evaluation in evaluations],
            title=f"テスト期間での当たり具合: {label}",
            note="ログ損失・Brier は小さいほど、AUC・率・回収率は大きいほど良い。「市場の確率」はオッズから見た率をそのまま確率としたもの、"
                 "「頭数から見た割合」はオッズの無い時点の基準（3 ÷ 頭数、1 ÷ 頭数）。採用の基準は、平均（アンサンブル）のログ損失が"
                 "この基準の行より小さいこと（地方の設計書 16 の 4）。",
        )

    def _row(self, evaluation: Evaluation) -> list[object]:
        return [
            self._timing_label(evaluation.timing), evaluation.model, evaluation.rows,
            rounded(evaluation.log_loss), rounded(evaluation.auc), rounded(evaluation.brier),
            rounded(evaluation.top_pick_place_rate), rounded(evaluation.top_pick_place_payback),
            rounded(evaluation.popularity_pick_place_rate), rounded(evaluation.popularity_pick_place_payback),
            rounded(evaluation.auc_within_popularity),
        ]

    def _prediction_files(self) -> Table:
        rows = [[label, self._timing_label(timing), str(path)]
                for label, paths in self._report.prediction_paths.items() for timing, path in paths.items()]
        return Table(["目的変数", "時点", "書いた予測の表"], rows, title="予測の表（道具「印の成績」の --form・--win に渡す）")
