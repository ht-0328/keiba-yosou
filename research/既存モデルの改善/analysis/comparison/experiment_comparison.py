"""材料を1つずつ足す実験と、条件で分ける実験の、比べ方の表。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from 共通.render import Table

from yosou.shared.dataset import TrainingData
from yosou.shared.dataset.column_names import POPULARITY

from ..scores import BinaryScores
from ..walk_forward import PART, PART_TEST, PREDICTION_COLUMN, WINDOW
from ..windows import TestWindow
from .prediction_join import LABEL, PredictionJoin
from .table_formatter import TableFormatter

#: 出発点の作り方の鍵（variant_catalog と同じ。全頭の変更版そのまま）。
BASE = "base"
#: 採用の基準: base よりログ損失が小さい区切りの数（全頭の採用の基準と同じ 5 / 7）。
MIN_BETTER_WINDOWS = 5
#: base との差の列の倍率（差がごく小さく、4桁に丸めると 0 に見えるので 1000倍して出す）。
_DIFFERENCE_SCALE = 1000
#: base との差の列の名前。
_DIFFERENCE = "base との差（×1000）"


class ExperimentComparison:
    """全頭の変更版（base）に材料を足した作り方・条件で分けた作り方を、base と比べる表を作る（既存モデルの修正計画の 2・4）。

    採用の基準（計画の「共通の材料追加・学習の分割」）: テスト期間のログ損失が base より小さい区切りが
    ``MIN_BETTER_WINDOWS`` 以上あり、7つの区切りを合わせたログ損失も base より小さいこと。

    ``predictions`` は作り方の鍵 → 予測の表、``names`` は作り方の鍵 → 表に出す名前。base は必ず入れる。
    """

    def __init__(self, data: TrainingData, predictions: Mapping[str, pd.DataFrame], names: Mapping[str, str],
                 windows: tuple[TestWindow, ...]) -> None:
        if BASE not in predictions:
            raise ValueError("比べる出発点（base）の予測がありません。先に walk_forward.py で base を回してください")
        join = PredictionJoin(data)
        self._tests = {key: self._test_part(join.of(frame)) for key, frame in predictions.items()}
        self._names = dict(names)
        self._windows = windows
        self._format = TableFormatter()

    def tables(self) -> list[Table]:
        by_window = self._by_window()
        return [self._verdict(by_window), self._format.table(
            by_window.reset_index(), "材料の実験: 区切りごとのログ損失（テスト期間）",
            note="ログ損失は小さいほど良い。列は作り方。")]

    def _test_part(self, frame: pd.DataFrame) -> pd.DataFrame:
        return frame[frame[PART] == PART_TEST]

    def _by_window(self) -> pd.DataFrame:
        """区切り × 作り方 のログ損失。"""
        rows = {window.name: {self._names[key]: self._log_loss(test[test[WINDOW] == window.name])
                              for key, test in self._tests.items()} for window in self._windows}
        return pd.DataFrame.from_dict(rows, orient="index").rename_axis("区切り")

    def _verdict(self, by_window: pd.DataFrame) -> Table:
        base_name = self._names[BASE]
        pooled = {key: BinaryScores().of(test[LABEL], test[PREDICTION_COLUMN], test[POPULARITY])
                  for key, test in self._tests.items()}
        rows = [self._verdict_row(key, by_window, pooled) for key in self._tests if key != BASE]
        base_row = {"作り方": base_name, "base より小さい区切り": None, "ログ損失（全期間）": pooled[BASE]["ログ損失"],
                    _DIFFERENCE: 0.0, "人気別AUC（全期間）": pooled[BASE]["人気別AUC"], "採用": "（出発点）"}
        return self._format.table(
            pd.DataFrame([base_row, *rows]), "材料の実験: base と比べた採否（テスト期間）",
            note=f"採用は、base よりログ損失が小さい区切りが {MIN_BETTER_WINDOWS} / {len(self._windows)} 以上あり、"
                 "全期間を合わせても小さいもの。base との差は、全期間のログ損失の差を 1000倍した値で、負なら良くなった。")

    def _verdict_row(self, key: str, by_window: pd.DataFrame, pooled: Mapping[str, dict]) -> dict[str, object]:
        name, base_name = self._names[key], self._names[BASE]
        better = int((by_window[name] < by_window[base_name]).sum())
        difference = (pooled[key]["ログ損失"] - pooled[BASE]["ログ損失"]) * _DIFFERENCE_SCALE
        adopted = better >= MIN_BETTER_WINDOWS and difference < 0
        return {"作り方": name, "base より小さい区切り": f"{better} / {len(by_window)}",
                "ログ損失（全期間）": pooled[key]["ログ損失"], _DIFFERENCE: difference,
                "人気別AUC（全期間）": pooled[key]["人気別AUC"], "採用": "はい" if adopted else "いいえ"}

    def _log_loss(self, chosen: pd.DataFrame) -> float:
        if chosen.empty:
            return float("nan")
        return BinaryScores().of(chosen[LABEL], chosen[PREDICTION_COLUMN], chosen[POPULARITY])["ログ損失"]
