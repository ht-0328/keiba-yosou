"""荒れ具合の予想の、比べ方の表（現行と計算）。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from 共通.render import Table

from yosou.shared.dataset import TrainingData

from ..upset import UpsetScores
from ..upset.upset_calculation_runner import BET, METHOD
from ..walk_forward import PART, PART_TEST, WINDOW
from .table_formatter import TableFormatter


class UpsetComparison:
    """荒れ具合の予想を、現行の作り方（レース単位で4段階を学ぶ）と、計算で出す新しい方法で比べる表を作る
    （既存モデルの修正計画の 3「荒れ具合」）。

    採用の基準（計画の 3）: 同じ券種・同じ払戻の区分で、新しい方法が現行に劣らず、各券種で使えることを確かめてから置き換える。
    ``predictions`` は方法の名前 → 予測の表（1行 = 1レース × 1券種。固い〜超荒れの4つの確率）。
    """

    def __init__(self, upset: TrainingData, predictions: Mapping[str, pd.DataFrame]) -> None:
        self._scores = UpsetScores(upset)
        frames = [self._tested(name, frame) for name, frame in predictions.items()]
        self._predictions = pd.concat(frames, ignore_index=True)
        self._format = TableFormatter()

    def tables(self) -> list[Table]:
        pooled = self._scores.table(self._predictions, [BET, METHOD])
        by_window = self._scores.table(self._predictions, [BET, WINDOW, METHOD])
        wide = by_window.pivot_table(index=[BET, WINDOW], columns=METHOD, values="ログ損失").reset_index()
        return [
            self._format.table(pooled, "荒れ具合: 券種・方法ごとの当たり具合（7つの区切りのテスト期間の合計）",
                               note="正解率・マクロF1・中荒れ以上のAUC は大きいほど、ログ損失は小さいほど良い。"
                                    "確定オッズで計算するので、実際に予想する時点より楽観側。"),
            self._format.table(wide, "荒れ具合: 券種・区切りごとのログ損失（小さいほど良い）"),
        ]

    def _tested(self, name: str, frame: pd.DataFrame) -> pd.DataFrame:
        """テスト期間の行だけにして、方法の名前を付ける（計算の予測はテスト期間だけ）。"""
        chosen = frame[frame[PART] == PART_TEST] if PART in frame.columns else frame
        return chosen.assign(**{METHOD: name})
