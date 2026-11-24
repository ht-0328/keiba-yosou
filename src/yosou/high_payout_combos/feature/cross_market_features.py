"""ほかの券種の市場から作る材料。"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import horse_columns

from .column_names import LOG_Q, RACE_ID

_WIDE, _QUINELLA, _EXACTA = TicketType.WIDE, TicketType.QUINELLA, TicketType.EXACTA
_TRIO, _TRIFECTA = TicketType.TRIO, TicketType.TRIFECTA

#: 券種ごとの材料の名前。``x_`` はほかの券種での市場の確率の対数、``d_`` はそれとその券種自身の市場の確率の対数との差。
NAMES: dict[TicketType, tuple[str, ...]] = {
    _WIDE: ("x_exa", "x_quin", "d_quin"),
    _QUINELLA: ("x_exa", "x_wide", "d_exa", "d_wide"),
    _EXACTA: ("x_quin", "x_wide", "x_rev", "d_quin"),
    _TRIO: ("x_wide", "x_quin"),
    _TRIFECTA: ("x_trio", "x_exa", "x_quin", "x_wide", "d_trio"),
}
#: 券種ごとの、材料を作るのに板が要るほかの券種。
REQUIRED_MARKETS: dict[TicketType, tuple[TicketType, ...]] = {
    _WIDE: (_EXACTA, _QUINELLA),
    _QUINELLA: (_EXACTA, _WIDE),
    _EXACTA: (_QUINELLA, _WIDE),
    _TRIO: (_WIDE, _QUINELLA),
    _TRIFECTA: (_TRIO, _EXACTA, _QUINELLA, _WIDE),
}
#: 組の中の位置の取り方（0 始まり）。
_FIRST_TWO, _REVERSED = (0, 1), (1, 0)
_ALL_PAIRS = ((0, 1), (0, 2), (1, 2))
_ALL_THREE = (0, 1, 2)


class CrossMarketFeatures:
    """組に含まれる2頭・3頭の組が、ほかの券種の市場でどう見られているかを材料にする。

    ``markets`` は券種ごとの市場の表（列 ``race_id``・``h1``…・``log_own``）。組がその券種の板に無ければ欠損値。
    例: ワイド 03-07 の ``x_quin`` は馬連 03-07 の市場の確率の対数、``x_exa`` は馬単 03→07 と 07→03 の確率の和の対数。
    3連複・3連単の ``x_wide`` と3連複の ``x_quin`` は、組の中の3つの2頭の組の対数の和。
    """

    def __init__(self, markets: Mapping[TicketType, pd.DataFrame]) -> None:
        self._markets = markets
        self._builders = {
            _WIDE: self._wide, _QUINELLA: self._quinella, _EXACTA: self._exacta, _TRIO: self._trio, _TRIFECTA: self._trifecta,
        }

    def of(self, ticket_type: TicketType, rows: pd.DataFrame) -> pd.DataFrame:
        """``rows`` はその券種の市場の表の行。戻り値の列は ``NAMES[ticket_type]``、行の並びと index は ``rows`` と同じ。"""
        return pd.DataFrame(self._builders[ticket_type](rows), index=rows.index)[list(NAMES[ticket_type])]

    def _wide(self, rows: pd.DataFrame) -> dict[str, np.ndarray]:
        quinella = self._log_q(rows, _QUINELLA, _FIRST_TWO)
        return {"x_exa": self._either_order(rows), "x_quin": quinella, "d_quin": quinella - self._own(rows)}

    def _quinella(self, rows: pd.DataFrame) -> dict[str, np.ndarray]:
        exacta, wide = self._either_order(rows), self._log_q(rows, _WIDE, _FIRST_TWO)
        return {"x_exa": exacta, "x_wide": wide, "d_exa": exacta - self._own(rows), "d_wide": wide - self._own(rows)}

    def _exacta(self, rows: pd.DataFrame) -> dict[str, np.ndarray]:
        quinella = self._log_q(rows, _QUINELLA, _FIRST_TWO)
        return {
            "x_quin": quinella, "x_wide": self._log_q(rows, _WIDE, _FIRST_TWO),
            "x_rev": self._log_q(rows, _EXACTA, _REVERSED), "d_quin": quinella - self._own(rows),
        }

    def _trio(self, rows: pd.DataFrame) -> dict[str, np.ndarray]:
        return {"x_wide": self._sum_of_pairs(rows, _WIDE), "x_quin": self._sum_of_pairs(rows, _QUINELLA)}

    def _trifecta(self, rows: pd.DataFrame) -> dict[str, np.ndarray]:
        trio = self._log_q(rows, _TRIO, _ALL_THREE)
        return {
            "x_trio": trio, "x_exa": self._log_q(rows, _EXACTA, _FIRST_TWO), "x_quin": self._log_q(rows, _QUINELLA, _FIRST_TWO),
            "x_wide": self._sum_of_pairs(rows, _WIDE), "d_trio": trio - self._own(rows),
        }

    def _own(self, rows: pd.DataFrame) -> np.ndarray:
        return rows[LOG_Q].to_numpy(dtype=float)

    def _either_order(self, rows: pd.DataFrame) -> np.ndarray:
        """馬単の2つの並び（1頭目→2頭目と、その逆）の市場の確率の和の対数。"""
        return np.logaddexp(self._log_q(rows, _EXACTA, _FIRST_TWO), self._log_q(rows, _EXACTA, _REVERSED))

    def _sum_of_pairs(self, rows: pd.DataFrame, source: TicketType) -> np.ndarray:
        """3頭の組の中の3つの2頭の組それぞれの、``source`` の券種での市場の確率の対数の和。"""
        return np.sum([self._log_q(rows, source, pair) for pair in _ALL_PAIRS], axis=0)

    def _log_q(self, rows: pd.DataFrame, source: TicketType, positions: Sequence[int]) -> np.ndarray:
        """組の ``positions`` の位置の馬で作る組の、``source`` の券種での市場の確率の対数。順不同の券種は馬番の小さい順にして引く。"""
        names = horse_columns(len(positions))
        numbers = np.stack([rows[f"h{position + 1}"].to_numpy(dtype=np.int64) for position in positions], axis=1)
        if not source.spec.is_ordered:
            numbers = np.sort(numbers, axis=1)
        wanted = pd.DataFrame(numbers, columns=names).assign(**{RACE_ID: rows[RACE_ID].to_numpy()})
        market = self._markets[source][[RACE_ID, *names, LOG_Q]].astype({name: np.int64 for name in names})
        return wanted.merge(market, on=[RACE_ID, *names], how="left")[LOG_Q].to_numpy(dtype=float)
