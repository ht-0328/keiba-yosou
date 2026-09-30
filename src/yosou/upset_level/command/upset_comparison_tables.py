"""この予想だけの、基準との比べと使い方の線引きの表。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from 共通.render import Table

from yosou.shared.command.cell_format import rounded
from yosou.shared.evaluation import ENSEMBLE_NAME, ClassEvaluation
from yosou.shared.feature import PredictionTiming

from ..dataset import BetType
from ..evaluation import UserRuleResult

#: 1番人気のオッズだけの基準と比べる時点（オッズを使う時点）。
_ODDS_TIMINGS: tuple[PredictionTiming, ...] = (PredictionTiming.DAY_BEFORE, PredictionTiming.RACE_DAY)
#: 比べの表で、この予想の行と基準の行に付ける名前。
_THIS_MODEL = "この予想（平均）"
_ODDS_ONLY = "1番人気のオッズだけ（平均）"


class UpsetComparisonTables:
    """1つの券種の、検証データでの基準との比べと使い方の線引きを、3つの表にする（設計書 16 の 3）。

    - 利用者の規則を基準にしたときの当たり具合。
    - 「荒れるレースだけ買う」使い方の線引き（中荒れ以上の確率のしきい値ごとの、レース数と実際に中荒れ以上だった割合）。
    - 1番人気のオッズだけで学習した基準と、この予想の比べ（前日・当日）。

    値を計算するのは ``evaluation/`` のクラスで、ここでは表の形にするだけ。
    """

    def __init__(self, bet: BetType, evaluations: Sequence[ClassEvaluation], user_rule: UserRuleResult,
                 thresholds: Mapping[PredictionTiming, pd.DataFrame], odds_only: Sequence[ClassEvaluation]) -> None:
        self._bet = bet
        self._evaluations = tuple(evaluations)
        self._user_rule = user_rule
        self._thresholds = dict(thresholds)
        self._odds_only = tuple(odds_only)

    def tables(self) -> list[Table]:
        return [self._user_rule_table(), self._threshold_table(), self._odds_only_table()]

    def _user_rule_table(self) -> Table:
        """利用者の規則を基準にしたときの、検証データでの当たり具合。"""
        result = self._user_rule
        return Table(
            ["レース数", "規則に当てはまる数", "当てはまったうち中荒れ以上の割合", "中荒れ以上のうち当てはまった割合", "中荒れ以上の割合"],
            [[result.rows, result.hits, rounded(result.precision), rounded(result.recall), rounded(result.base_rate)]],
            title=f"{self._bet.label}: 利用者の規則（1番人気 4.0倍以上かつ 2〜5番人気 10倍未満）を基準にしたとき",
            note="規則に当てはまるレースを「中荒れ以上」と予想したとみなした値。検証データで測る。",
        )

    def _threshold_table(self) -> Table:
        """時点ごと・しきい値ごとの、選ばれるレース数と、そのうち実際に中荒れ以上だった割合。"""
        rows = [
            [timing.label, *(self._cell(value) for value in row)]
            for timing, frame in self._thresholds.items()
            for row in frame.itertuples(index=False)
        ]
        columns = next(iter(self._thresholds.values())).columns if self._thresholds else []
        return Table(
            ["時点", *columns], rows,
            title=f"{self._bet.label}: 「荒れるレースだけ買う」使い方の線引き（中荒れ以上の確率のしきい値ごと）",
            note="平均の「中荒れ以上の確率」がしきい値以上のレースを選んだときの値。検証データで測る。"
                 "しきい値 0 の行は全レース（しきい値を使わないとき）。線は設計書に書かず、この表から選ぶ。",
        )

    def _odds_only_table(self) -> Table:
        """前日・当日の、この予想の平均と、1番人気のオッズだけの基準の平均の当たり具合。"""
        this_model = {e.timing: e for e in self._evaluations if e.model == ENSEMBLE_NAME}
        odds_only = next(e for e in self._odds_only if e.model == ENSEMBLE_NAME)
        rows: list[list[object]] = []
        for timing in _ODDS_TIMINGS:
            rows += [self._score_row(timing, _THIS_MODEL, this_model[timing]),
                     self._score_row(timing, _ODDS_ONLY, odds_only)]
        return Table(
            ["時点", "予想", "ログ損失", "正解率", "マクロF1", "クラスのずれの平均",
             "AUC（中荒れ以上）", "AUC（大荒れ以上）", "AUC（超荒れ）"],
            rows,
            title=f"{self._bet.label}: 1番人気のオッズだけの予想と比べたとき",
            note="基準は、特徴量を1番人気のオッズだけにして、同じ設定・同じ期間で学習した LightGBM と CatBoost の平均。"
                 "前日と当日は同じ列なので、基準の値は同じ。木曜はオッズを使わないので比べない。検証データで測る。",
        )

    def _score_row(self, timing: PredictionTiming, name: str, evaluation: ClassEvaluation) -> list[object]:
        return [
            timing.label, name, rounded(evaluation.log_loss), rounded(evaluation.accuracy), rounded(evaluation.macro_f1),
            rounded(evaluation.mean_class_gap), *(rounded(auc) for auc in evaluation.cumulative_auc),
        ]

    def _cell(self, value: object) -> object:
        """小数は3桁に丸め、整数（レース数）は Python の整数にする。"""
        if isinstance(value, (int, np.integer)):
            return int(value)
        return rounded(float(value))
