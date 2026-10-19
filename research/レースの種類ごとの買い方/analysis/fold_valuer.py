"""区切りごとに、直前の2つの区切りで重みを推定し、その区切りの組に組の確率と期待値を付ける。"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType

from .design_matrix import DesignMatrix
from .penalized_blend_fitter import PenalizedBlendFitter
from .weight_method import FIRST_PENALTY, WeightMethod

#: 残す組の期待値の下限（決まりの線の候補のいちばん下。docs/01 の 4）。
MIN_VALUE = 1.0
#: 残す組のオッズの上限（オッズの上限の候補のいちばん上）。
MAX_ODDS = 10000.0
#: ワイドは1レースで3組当たるので、組の確率の合計を 3 にそろえる（本番の ``WIDE_WINNERS``）。
WIDE_WINNERS = 3.0


@dataclass
class FoldLog:
    """1つの区切りで選んだ罰則の強さと重み、罰則ごとの学習に使っていない区切りでの対数尤度。"""

    fold: str
    penalty: float
    weights: list[float]
    likelihoods: dict[float, float] = field(default_factory=dict)


class FoldValuer:
    """1つの券種・1つの案について、区切りの順に次を繰り返す（docs/01 の 4・5）。

    1. 直前の2つの区切りの組で、罰則の強さの候補ごとに重みを推定する（``sample`` が 1 より大きければ、レースID を割った余りが 0 のレースだけ）。
    2. 罰則の強さは、その区切りより前の区切りでの「学習に使っていない区切りの対数尤度」の合計がいちばん高いものを使う（最初は ``FIRST_PENALTY``）。
    3. その重みで、その区切りの全部の組に組の確率と期待値（確率 × 確定オッズ）を付け、期待値が ``MIN_VALUE`` 以上でオッズが ``MAX_ODDS`` 以下の組を残す。

    ``frames`` は区切りの名前の順に、その区切りの組の表（``ComboFeatures`` の表を区切りで分けたもの）を返すもの。
    """

    def __init__(self, ticket_type: TicketType, method: WeightMethod, sample: int = 1) -> None:
        self._ticket_type = ticket_type
        self._method = method
        self._sample = sample
        self._design = DesignMatrix(method)
        self._light = DesignMatrix(method, np.float32)

    def run(self, frames: Iterator[tuple[str, pd.DataFrame]]) -> tuple[pd.DataFrame, list[FoldLog]]:
        history: list[tuple[str, pd.DataFrame]] = []
        totals = {penalty: 0.0 for penalty in self._method.penalties}
        valued, logs = [], []
        for fold, frame in frames:
            if len(history) == 2:
                train = pd.concat([self._sampled(old) for _, old in history], ignore_index=True)
                weights = {penalty: self._fit(train, penalty) for penalty in self._method.penalties}
                chosen = self._choose(totals, logs)
                checked = self._sampled(frame)
                likelihoods = {penalty: self._likelihood(weights[penalty], checked) for penalty in weights}
                for penalty, value in likelihoods.items():
                    totals[penalty] += value
                valued.append(self._value(frame, weights[chosen]))
                logs.append(FoldLog(fold, chosen, [float(value) for value in weights[chosen]], likelihoods))
            history = [*history[-1:], (fold, frame)]
        return pd.concat(valued, ignore_index=True), logs

    def _choose(self, totals: dict[float, float], logs: list[FoldLog]) -> float:
        if len(totals) == 1:
            return next(iter(totals))
        return FIRST_PENALTY if not logs else max(totals, key=lambda penalty: totals[penalty])

    def _sampled(self, frame: pd.DataFrame) -> pd.DataFrame:
        if self._sample <= 1:
            return frame
        return frame[frame["race_id"].astype(np.int64) % self._sample == 0]

    def _fit(self, train: pd.DataFrame, penalty: float) -> np.ndarray:
        rows = train[train.groupby("race_id", sort=False)["hit"].transform("sum") > 0]
        features, hit, starts = self._arrays(rows)
        return PenalizedBlendFitter(penalty).fit(features, hit, starts, self._design.penalized())

    def _likelihood(self, weights: np.ndarray, frame: pd.DataFrame) -> float:
        rows = frame[frame.groupby("race_id", sort=False)["hit"].transform("sum") > 0]
        features, hit, starts = self._arrays(rows)
        return PenalizedBlendFitter().log_likelihood(weights, features, hit, starts)

    def _arrays(self, rows: pd.DataFrame) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        race = rows["race_id"].to_numpy()
        starts = np.flatnonzero(np.r_[True, race[1:] != race[:-1]])
        return self._design.of(rows), rows["hit"].to_numpy(dtype=bool), starts

    def _value(self, frame: pd.DataFrame, weights: np.ndarray) -> pd.DataFrame:
        score = pd.Series(self._light.of(frame) @ weights.astype(np.float32), index=frame.index, dtype=np.float64)
        race = frame["race_id"]
        exponent = np.exp(score - score.groupby(race, sort=False).transform("max"))
        winners = WIDE_WINNERS if self._ticket_type is TicketType.WIDE else 1.0
        probability = exponent / exponent.groupby(race, sort=False).transform("sum") * winners
        value = probability * frame["odds"]
        keep = (value >= MIN_VALUE) & (frame["odds"] <= MAX_ODDS)
        columns = ["race_id", "race_date", "fold", "expectation", "kind_group", "top",
                   *(f"h{at}" for at in range(1, self._ticket_type.spec.horse_count + 1)), "odds", "payout", "hit"]
        return frame.loc[keep, columns].assign(probability=probability[keep], value=value[keep]).reset_index(drop=True)


def fold_order(name: str) -> tuple[int, int]:
    """区切りの名前の並び順。例: ``2020年後半`` → (2020, 1)。1年で1つの区切り（``2026年``）は (2026, 0)。"""
    found = re.fullmatch(r"(\d{4})年(前半|後半)?", name)
    if not found:
        raise ValueError(f"区切りの名前が読めません: {name}")
    return int(found.group(1)), 1 if found.group(2) == "後半" else 0


def frames_by_fold(load_year: Callable[[int], pd.DataFrame], years: range) -> Iterator[tuple[str, pd.DataFrame]]:
    """年ごとの組の表を順に読み、区切りの順に返す（読んだ年は、その年の区切りを返し終えたら手放す）。"""
    for year in years:
        table = load_year(year)
        for fold in sorted(table["fold"].unique(), key=fold_order):
            yield fold, table[table["fold"] == fold].reset_index(drop=True)
        del table
