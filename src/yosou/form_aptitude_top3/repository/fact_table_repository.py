"""事実表（一時表）を用意する。"""

from __future__ import annotations

import duckdb

from 共通 import facts


class FactTableRepository:
    """事実表（1行 = 1頭の出走。中央の確定成績）を、接続の一時表として用意する。

    SQL は ``tools/共通/facts.py`` のものを使い、同じ SQL を2か所に書かない（設計書 04）。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con

    def ensure(self) -> None:
        """事実表が無ければ作る。あれば何もしない。"""
        facts.ensure_facts(self._con)
