"""どのレースを読むか（開催日の範囲・競馬場・rid）を、SQL の条件にする。"""

from __future__ import annotations

from dataclasses import dataclass

from 共通 import keys
from 共通.filters import parse_date


@dataclass(frozen=True)
class RaceScope:
    """読むレースの範囲。``rid`` を渡せばその1レース、渡さなければ開催日の範囲（``date_to`` は省ける）。

    日付は ``YYYY-MM-DD``。``venue_code`` は競馬場コード（``05``）。``jra_only`` が真なら中央のレースだけ
    （jvdata-store の DB には地方のレースも混ざっている）。地方競馬DATA の DB（nvdata-store）を読むときは偽にする。
    """

    date_from: str | None = None
    date_to: str | None = None
    venue_code: str | None = None
    rid: str | None = None
    jra_only: bool = True

    @classmethod
    def race(cls, rid: str) -> "RaceScope":
        """1レースだけ。rid の桁が違えば ``ValueError``。"""
        keys.split_rid(rid)
        return cls(rid=rid)

    @classmethod
    def days(cls, date_from: str, date_to: str | None = None, venue_code: str | None = None, *, jra_only: bool = True) -> "RaceScope":
        """開催日が ``date_from`` 以降（``date_to`` まで）のレース。日付の形が違えば ``ValueError``。"""
        return cls(date_from=parse_date(date_from), date_to=parse_date(date_to) if date_to else None, venue_code=venue_code,
                   jra_only=jra_only)

    def where(self, alias: str = "") -> tuple[str, list[str]]:
        """WHERE 句の条件（``jra_only`` なら中央だけ、を含む）と、その引数。"""
        clauses, params = [keys.jra_only(alias) if self.jra_only else "TRUE"], []
        if self.rid:
            clause, values = keys.rid_condition(self.rid, alias)
            return f"{clauses[0]} AND {clause}", values
        day = keys.race_date_expr(alias)
        if self.date_from:
            clauses.append(f"{day} >= ?")
            params.append(self.date_from)
        if self.date_to:
            clauses.append(f"{day} <= ?")
            params.append(self.date_to)
        if self.venue_code:
            clauses.append(f"{keys.col('競馬場コード', alias)} = ?")
            params.append(self.venue_code)
        return " AND ".join(clauses), params
