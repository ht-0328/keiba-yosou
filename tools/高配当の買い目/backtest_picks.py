"""年ごとの予測から、買い目の決まりで買い目を選ぶ。"""

from __future__ import annotations

from collections.abc import Callable
from itertools import chain
from typing import Any

import pandas as pd

from yosou.shared.betting import TicketType

from 高配当の買い目.pick_columns import PICK_COLUMNS
from 高配当の買い目.repository.yearly_prediction_reader import YearlyPredictionReader


class BacktestPicks:
    """年ごとの予測（``reader``。``YearlyPredictionReader``）から、買い目の決まり（``make_rule(期待値の線, 上限の点数)`` が返す部品の ``pick``。
    予想のパッケージの ``HighPayoutRule``）で買う組を選ぶ。戻り値は1行 = 1点（列 ``PICK_COLUMNS``。全部の券種をつないだもの）。

    2段に分かれている。``candidates`` は、いちばん低い期待値の線・上限の点数なしで選んだ組（どの決まりの買い目もこの中にある）。
    ``select`` は、その中から決まり（期待値の線・上限の点数）ごとの買い目を選び直す。線の感度の表のように決まりを替えて何度も数えるとき、
    予測のファイル（3連単は数千万行）を読むのを1回にするため。期待値の線を上げても、上限の点数（確率の高い順）を付けても、選ばれる組は
    予測の全部から同じ決まりで選んだものと変わらない。
    """

    def __init__(self, reader: YearlyPredictionReader, make_rule: Callable[[float, int | None], Any], ticket_types: tuple[TicketType, ...]) -> None:
        self._reader = reader
        self._make_rule = make_rule
        self._ticket_types = ticket_types

    def candidates(self, lowest_value_line: float) -> pd.DataFrame:
        rule = self._make_rule(lowest_value_line, None)
        # 券種ごと・年ごとの予測の表を順に1つずつ読み、読んだそばから買う組だけに減らす
        yearly_tables = chain.from_iterable(map(self._reader.read, self._ticket_types))
        parts = [rule.pick(table) for table in yearly_tables]
        kept = [part for part in parts if not part.empty]
        return pd.concat(kept, ignore_index=True) if kept else pd.DataFrame(columns=list(PICK_COLUMNS))

    def select(self, candidates: pd.DataFrame, value_line: float, max_points: int | None) -> pd.DataFrame:
        """``candidates`` から、期待値の線 ``value_line``・1レース1券種の上限の点数 ``max_points``（None は上限なし）の買い目。"""
        if candidates.empty:
            return candidates
        return self._make_rule(value_line, max_points).pick(candidates)

    def years(self) -> set[int]:
        """対象の券種のどれかに予測のある年。"""
        return set(chain.from_iterable(map(self._reader.years, self._ticket_types)))
