"""3連単の確率の表から、券種ごとの買い目の当たる確率を出す。"""

from __future__ import annotations

from collections.abc import Callable

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType

from .column_names import COMBO, FIRST, PROBABILITY, SECOND, THIRD

#: 複勝が 2着までになる出走頭数（7頭立て以下）。
PLACE_TWO_MAX_FIELD = 7
#: 組番の1頭ぶんの桁（馬番は 2桁）。
_HORSE_BASE = 100

#: 1つの券種の、3連単の各行が当てる買い目（整数にした組番）と、その重み（3連単の確率）を返す関数。
Outcomes = Callable[[np.ndarray, np.ndarray, int], tuple[np.ndarray, np.ndarray]]


class TicketProbability:
    """1レースの3連単の確率の表から、1つの券種の全部の買い目の当たる確率を出す（設計書 03 の 5. の表）。

    3連単の各行（1着・2着・3着の並び）が当てる買い目を並べ、同じ買い目の確率を足す。例えば馬連 3-7 は、
    1・2着が 3 と 7（順番は問わない）の行の確率の合計である。複勝は 7頭立て以下なら 2着以内、8頭立て以上なら 3着以内。
    ワイドは 2頭とも 3着以内。計算は numpy で、18頭立て（3連単 4,896 通り）でも 1券種 1ミリ秒ほどで終わる。

    ``combo`` は払戻・確定オッズの表の組番と同じ形（馬番を2桁の0埋めでつなぐ。順番を問わない券種は小さい順）。
    """

    def __init__(self) -> None:
        self._outcomes: dict[TicketType, Outcomes] = {
            TicketType.WIN: self._win,
            TicketType.PLACE: self._place,
            TicketType.QUINELLA: self._quinella,
            TicketType.EXACTA: self._exacta,
            TicketType.WIDE: self._wide,
            TicketType.TRIO: self._trio,
            TicketType.TRIFECTA: self._trifecta,
        }

    def of(self, trifecta: pd.DataFrame, ticket_type: TicketType, field_size: int) -> pd.DataFrame:
        """``trifecta`` は列 ``first``・``second``・``third``（馬番）・``probability`` の表（1レースぶん）。

        戻り値は列 ``combo``・``probability`` の表で、組番の小さい順に 1買い目 1行。
        """
        order = trifecta[[FIRST, SECOND, THIRD]].to_numpy(dtype=np.int64)
        weights = trifecta[PROBABILITY].to_numpy(dtype=np.float64)
        codes, outcome_weights = self._outcomes[ticket_type](order, weights, field_size)
        combos, inverse = np.unique(codes, return_inverse=True)
        totals = np.bincount(inverse, weights=outcome_weights, minlength=len(combos))
        width = 2 * ticket_type.spec.horse_count
        return pd.DataFrame({COMBO: pd.Series(combos).astype(str).str.zfill(width), PROBABILITY: totals})

    @staticmethod
    def _code(horses: np.ndarray) -> np.ndarray:
        """馬番の並び（1行 = 1買い目）を、組番の数（例 ``[1, 5, 12]`` → 10512）にする。"""
        powers = _HORSE_BASE ** np.arange(horses.shape[1] - 1, -1, -1, dtype=np.int64)
        return horses @ powers

    def _win(self, order: np.ndarray, weights: np.ndarray, field_size: int) -> tuple[np.ndarray, np.ndarray]:
        return order[:, 0], weights

    def _place(self, order: np.ndarray, weights: np.ndarray, field_size: int) -> tuple[np.ndarray, np.ndarray]:
        places = 2 if field_size <= PLACE_TWO_MAX_FIELD else 3
        return order[:, :places].T.ravel(), np.tile(weights, places)

    def _quinella(self, order: np.ndarray, weights: np.ndarray, field_size: int) -> tuple[np.ndarray, np.ndarray]:
        return self._code(np.sort(order[:, :2], axis=1)), weights

    def _exacta(self, order: np.ndarray, weights: np.ndarray, field_size: int) -> tuple[np.ndarray, np.ndarray]:
        return self._code(order[:, :2]), weights

    def _wide(self, order: np.ndarray, weights: np.ndarray, field_size: int) -> tuple[np.ndarray, np.ndarray]:
        pairs = np.concatenate([order[:, [0, 1]], order[:, [0, 2]], order[:, [1, 2]]])
        return self._code(np.sort(pairs, axis=1)), np.tile(weights, 3)

    def _trio(self, order: np.ndarray, weights: np.ndarray, field_size: int) -> tuple[np.ndarray, np.ndarray]:
        return self._code(np.sort(order, axis=1)), weights

    def _trifecta(self, order: np.ndarray, weights: np.ndarray, field_size: int) -> tuple[np.ndarray, np.ndarray]:
        return self._code(order), weights
