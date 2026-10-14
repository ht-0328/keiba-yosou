"""7つの区切りでの確かめの結果を表にする。"""

from __future__ import annotations

import pandas as pd

from 共通.render import Table

from yosou.shared.command.cell_format import rounded
from yosou.shared.evaluation import Evaluation

from ..workflow import COMPARISON_COLUMNS, TIMING_LABELS, WindowedBacktestResult

#: 当たり具合の表の列。
_COLUMNS = ["区切り", "モデル", "行数", "ログ損失", "AUC", "Brier", "確率1位の馬の{label}率", "確率1位の馬の複勝回収率",
            "人気最上位の馬の{label}率", "人気最上位の馬の複勝回収率", "人気の中での AUC"]


class WindowedBacktestTables:
    """7つの区切りでの確かめの結果（``WindowedBacktestResult``）を、目的変数ごとの「特別競走の行の当たり具合」「全レースの行の当たり具合（参考）」
    「木曜のモデルとの比べ」と、書いた予測の表 の表にする（設計書 16 の 4）。"""

    def __init__(self, result: WindowedBacktestResult) -> None:
        self._result = result

    def tables(self) -> list[Table]:
        tables: list[Table] = []
        for label, rows in self._result.special.items():
            tables.append(self._evaluations(label, rows, f"特別競走の行での当たり具合: {label}（{self._result.variant}。{self._result.feature_count}個）",
                                            "テスト期間の特別競走の行（Y = 1）だけで測った。採用の基準は、平均（アンサンブル）のログ損失が「頭数から見た割合」より"
                                            "小さい区切りが7つのうち5つ以上あり、全期間でも小さいこと（設計書 16 の 4）。"))
        for label, rows in self._result.all_rows.items():
            tables.append(self._evaluations(label, rows, f"全レースの行での当たり具合（参考）: {label}", "平場を含むテスト期間の全部の行。参考に出す。"))
        for label, comparison in self._result.comparisons.items():
            tables.append(self._comparison(label, comparison))
        tables.append(self._prediction_files())
        return tables

    def _evaluations(self, label: str, rows: list[tuple[str, list[Evaluation]]], title: str, note: str) -> Table:
        columns = [column.format(label=label) for column in _COLUMNS]
        return Table(columns, [self._row(name, evaluation) for name, evaluations in rows for evaluation in evaluations], title=title, note=note)

    def _row(self, name: str, evaluation: Evaluation) -> list[object]:
        return [
            name, evaluation.model, evaluation.rows, rounded(evaluation.log_loss), rounded(evaluation.auc), rounded(evaluation.brier),
            rounded(evaluation.top_pick_place_rate), rounded(evaluation.top_pick_place_payback),
            rounded(evaluation.popularity_pick_place_rate), rounded(evaluation.popularity_pick_place_payback),
            rounded(evaluation.auc_within_popularity),
        ]

    def _comparison(self, label: str, comparison: pd.DataFrame) -> Table:
        rows = [[row[column] if column in COMPARISON_COLUMNS[:2] else rounded(row[column]) for column in COMPARISON_COLUMNS]
                for _, row in comparison.iterrows()]
        return Table(list(COMPARISON_COLUMNS), rows, title=f"中央の木曜のモデルとの比べ: {label}",
                     note="同じレース・同じ馬（特別競走の出走馬）で測った。木曜のモデルは材料が多いので、差は木曜に出し直す価値の目安（参考。設計書 16 の 3）。")

    def _prediction_files(self) -> Table:
        timing_label = next(iter(TIMING_LABELS.values()))
        rows = [[label, timing_label, str(path)] for label, path in self._result.prediction_paths.items()]
        return Table(["目的変数", "時点", "書いた予測の表"], rows, title="予測の表（道具「印の成績」の --form・--win に渡す。--timing 木曜 --no-danger）")
