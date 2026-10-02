"""1レースが重賞（G1・G2・G3）かどうかと、そのグレードを読む。"""

from __future__ import annotations

import duckdb

from 共通 import keys, stakes


class StakesGradeRepository:
    """重賞の判定は ``共通/stakes.py`` の対応表（グレードコード A・B・C、中央だけ、障害の重賞は含めない）に任せる。

    分析ツール「重賞攻略」と予想モデル「重賞の傾向と近走から3着以内を予想」（引退）が対象にするレースと同じ決め方にするため、
    ここで別に決めない。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def grade_of(self, race_id: str) -> str | None:
        """重賞ならグレードの呼び名（G1・G2・G3）。重賞でなければ None。"""
        table = keys.q(stakes.ensure_stakes_map(self._con))
        row = self._con.execute(f"SELECT grade FROM {table} WHERE race_id = ?", [race_id]).fetchone()
        return None if row is None else stakes.GRADE_NAMES.get(row[0])
