"""較正の方法ごとに、テスト期間の確率のずれと期待値の当たり具合を比べる。"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from itertools import product
from typing import Protocol

import numpy as np
import pandas as pd
from sklearn.metrics import log_loss

from 共通.render import Table

from yosou.shared.dataset.column_names import PLACE_PAYOUT, POPULARITY
from yosou.shared.evaluation import ProbabilityBands, ValueBands
from yosou.shared.evaluation.value_bands import ACTUAL_HIT, COUNT, PAYBACK, PREDICTED_HIT
from yosou.shared.place_value import PLACE_PROBABILITY, PLACE_VALUE
from yosou.shared.workflow.calibration_check import LABEL, PART, PART_TEST, PART_VALID, PROBABILITY, SEGMENT, TIMING

from ..comparison.table_formatter import TableFormatter
from .calibration_frame_builder import WINDOW_COLUMN

#: 較正しない場合の名前。
RAW = "較正なし"
#: 期待値で買う線と、「人気上位しか選ばなくなっていないか」を見る人気の線。
_VALUE_LINE = 1.0
_LONGSHOT_POPULARITY = 10
#: ログ損失を計算するときの端の丸め。
_EDGE = 1e-6


class Calibration(Protocol):
    """確率をそろえ直す方法（``PlattCalibration``・``IsotonicCalibration``）の決まり。"""

    def fit(self, probability: np.ndarray, label: np.ndarray) -> Calibration:
        ...

    def apply(self, probability: np.ndarray) -> np.ndarray:
        ...


class CalibrationComparison:
    """較正の方法ごとに、区切り × 時点 × 区分ごとに検証期間で較正を学び、テスト期間に当てて、ずれと期待値の当たり具合を比べる。

    テスト期間の結果は、較正を学ぶのに使わない。複勝的中の確率と期待値は、確率を較正した比（較正後 ÷ 較正前）を掛けて直す
    （複勝的中の確率は3着以内の確率に比例するため）。``methods`` は 方法の名前 → 較正を作る関数。「較正なし」は必ず並べる。
    """

    def __init__(self, frame: pd.DataFrame, methods: Mapping[str, Callable[[], Calibration]]) -> None:
        self._frame = frame
        self._methods = dict(methods)
        self._names = [RAW, *self._methods]

    def table(self) -> Table:
        test = self._calibrated_test()
        groups = list(test.groupby([TIMING, SEGMENT], sort=False))
        rows = [self._row(key, group, name) for (key, group), name in product(groups, self._names)]
        return TableFormatter().table(
            pd.DataFrame(rows), "較正の方法ごとの、テスト期間の確率のずれと期待値の当たり具合（7つの区切りの合計）",
            note="較正は区切りごとに検証期間で学び、テスト期間に当てた。ログ損失・帯ごとのずれの平均は小さいほど良い。"
                 "「ログ損失が較正なしより小さい区切り」は、7つの区切りのうち、較正でテスト期間のログ損失が下がった数。"
                 "期待値1以上は、複勝の期待値が 1 以上の馬を全部 100円ずつ買ったときの成績（前日・当日だけ）。",
        )

    def _calibrated_test(self) -> pd.DataFrame:
        """テスト期間の行に、方法ごとの較正後の確率の列（列の名前は方法の名前）を足した表。"""
        keys = [TIMING, SEGMENT, WINDOW_COLUMN]
        parts = [self._calibrate(group) for _, group in self._frame.groupby(keys, sort=False)]
        return pd.concat(parts, ignore_index=True)

    def _calibrate(self, group: pd.DataFrame) -> pd.DataFrame:
        valid, test = group[group[PART] == PART_VALID], group[group[PART] == PART_TEST]
        fitted = {name: make().fit(valid[PROBABILITY].to_numpy(), valid[LABEL].to_numpy())
                  for name, make in self._methods.items()}
        calibrated = {name: calibration.apply(test[PROBABILITY].to_numpy()) for name, calibration in fitted.items()}
        return test.assign(**{RAW: test[PROBABILITY].to_numpy()}, **calibrated)

    def _row(self, key: tuple[str, str], group: pd.DataFrame, name: str) -> dict[str, object]:
        label, probability = group[LABEL], group[name]
        ratio = probability / group[PROBABILITY].where(group[PROBABILITY] > 0)
        value, hit = group[PLACE_VALUE] * ratio, group[PLACE_PROBABILITY] * ratio
        bought = ValueBands().at_least(value, hit, group[PLACE_PAYOUT], _VALUE_LINE)
        chosen = pd.to_numeric(group.loc[value >= _VALUE_LINE, POPULARITY], errors="coerce")
        return {
            "時点": key[0], "区分": key[1], "方法": name, "頭数": len(group),
            "ログ損失": self._log_loss(label, probability), "帯ごとのずれの平均": ProbabilityBands().gap(label, probability),
            "実際 ÷ 予想": label.mean() / probability.mean(), "ログ損失が較正なしより小さい区切り": self._better_windows(group, name),
            "期待値1以上の点数": bought[COUNT], "その予想の的中率": bought[PREDICTED_HIT], "その実際の的中率": bought[ACTUAL_HIT],
            "その回収率": bought[PAYBACK],
            "そのうち10番人気以下の割合": (chosen >= _LONGSHOT_POPULARITY).mean() if len(chosen) else np.nan,
        }

    def _better_windows(self, group: pd.DataFrame, name: str) -> int:
        windows = [part for _, part in group.groupby(WINDOW_COLUMN, sort=False)]
        return sum(self._log_loss(part[LABEL], part[name]) < self._log_loss(part[LABEL], part[RAW]) for part in windows)

    def _log_loss(self, label: pd.Series, probability: pd.Series) -> float:
        return float(log_loss(label, probability.clip(_EDGE, 1 - _EDGE), labels=[0, 1]))
