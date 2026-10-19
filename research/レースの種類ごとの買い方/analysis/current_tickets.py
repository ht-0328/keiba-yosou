"""今の本番の買い目（道具「印の成績」の買い目の CSV）を、開催日ごとの成績にする。"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType

from .rule_day_table import HIT_RACES, PAYOUT, POINTS, RACES


class CurrentTickets:
    """道具「印の成績」が書いた買い目の CSV（``買い目/<モデル>-race_day.csv``）から、``<券種>（組の期待値）`` の買い目のうち
    外した理由の無いもの（トリガミとオッズの無い組を除いたもの）を読み、券種ごとに配列 [開催日, 4]（点数・払戻・買ったレース・当たったレース）にする。

    比べる相手（今の本番）の成績を、新しい案と同じ形で数えるために使う。CSV は大きいので、DuckDB で要る行だけ読む（元DB は開かない）。
    """

    def __init__(self, path: Path, days: Sequence[pd.Timestamp]) -> None:
        self._path = Path(path)
        self._days = pd.DatetimeIndex(days)

    def rule(self, label: str, expectation: str | None = None) -> np.ndarray:
        """買い方 ``label``（例 ``単勝``）の、外した理由の無い買い目の配列 [開催日, 4]。``expectation`` があれば、その期待度のレースだけ。"""
        where = f"買い方 = '{label}'" + (f" AND 期待度 = '{expectation}'" if expectation else "")
        races = duckdb.sql(f"""
            SELECT レースID AS race_id, any_value(開催日) AS race_date, count(*) AS points, sum(CAST("払戻（100円あたり）" AS DOUBLE)) AS payout
            FROM read_csv('{self._path.as_posix()}', header=true, all_varchar=true)
            WHERE {where} AND coalesce(外した理由, '') = ''
            GROUP BY ALL""").df()
        return self._days_of(races)

    def read(self) -> dict[TicketType, np.ndarray]:
        races = duckdb.sql(f"""
            SELECT 券種 AS ticket, レースID AS race_id, any_value(開催日) AS race_date, count(*) AS points,
                   sum(CAST("払戻（100円あたり）" AS DOUBLE)) AS payout
            FROM read_csv('{self._path.as_posix()}', header=true, all_varchar=true)
            WHERE 買い方 LIKE '%（組の期待値）' AND coalesce(外した理由, '') = ''
            GROUP BY ALL""").df()
        return {ticket_type: self._days_of(races[races["ticket"] == ticket_type.label]) for ticket_type in TicketType
                if (races["ticket"] == ticket_type.label).any()}

    def _days_of(self, races: pd.DataFrame) -> np.ndarray:
        day = self._days.get_indexer(pd.to_datetime(races["race_date"]))
        races = races[day >= 0]
        day = day[day >= 0]
        out = np.zeros((len(self._days), 4))
        for slot, values in ((POINTS, races["points"]), (PAYOUT, races["payout"]), (RACES, np.ones(len(races))),
                             (HIT_RACES, (races["payout"] > 0).astype(float))):
            out[:, slot] = np.bincount(day, weights=np.asarray(values, dtype=float), minlength=len(self._days))
        return out
