"""1レースを当日の予想の部品で予想し、期待値が線以上の馬を「買ったつもり」で記録する。"""

from __future__ import annotations

from datetime import datetime

import duckdb

from フォワードテスト.ledger import Ledger
from フォワードテスト.repository import OddsSnapshotRepository


class ForwardRecorder:
    """発走の少し前のレースを予想して、買い目とレースの記録を ``Ledger`` に足す。

    予想は当日の予想（``tools/当日の予想/``）と同じモデル・同じ線で行う。実際に買うときに使う道具を、そのまま確かめるためである。
    使ったオッズの断面の発表時刻も残す（締め切り前の断面で予想したことを、あとで確かめられるように）。
    """

    def __init__(self, predictor, ledger: Ledger, line: float, stake: int = 100) -> None:
        self._predictor = predictor
        self._ledger = ledger
        self._line = line
        self._stake = stake

    def record(self, con: duckdb.DuckDBPyConnection, day: str, race: dict, loaded: list, now: datetime) -> int:
        """開催日 ``day``（YYYY-MM-DD）の1レースを予想して記録する。記録した買い目の数を返す。"""
        snapshot = OddsSnapshotRepository(con).read(race["rid"])
        base = {"記録時刻": now.strftime("%Y-%m-%d %H:%M"), "開催日": day, "race_id": race["rid"],
                "発走": race["発走"], "場": race["場"], "R": race["R"],
                "オッズの発表時刻": "" if snapshot is None else f"{snapshot[1]}（データ区分 {snapshot[0]}）"}
        try:
            label, table = self._predictor.predict(con, race["rid"], loaded)
        except ValueError as error:
            self._ledger.append([], {**base, "モデル": "", "買い目の数": 0, "予想できない理由": str(error)})
            return 0
        records = [dict(zip(table.columns, row)) for row in table.rows]
        buys = [self._buy(base, race, record, label) for record in records if (record.get("期待値") or 0) >= self._line]
        self._ledger.append(buys, {**base, "モデル": label, "買い目の数": len(buys), "予想できない理由": ""})
        return len(buys)

    def _buy(self, base: dict, race: dict, record: dict, label: str) -> dict[str, object]:
        return {**base, "レース名": race.get("レース名") or "", "馬番": record["馬番"], "馬名": record["馬名"],
                "人気": record.get("使用した人気"), "単勝オッズ": record.get("単勝オッズ"),
                "複勝オッズ（最低）": record.get("複勝オッズ（最低）"),
                "3着以内の確率": _round(record.get("3着以内の確率"), 4), "期待値": _round(record.get("期待値"), 3),
                "線": self._line, "モデル": label, "賭け金": self._stake, "払戻": "", "精算": "", "精算時刻": ""}


def _round(value, digits: int):
    return "" if value is None else round(float(value), digits)
