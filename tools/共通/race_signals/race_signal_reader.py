"""範囲のレースの ``RaceSignals`` を、3つのリポジトリの結果を rid でつないで作る。"""

from __future__ import annotations

from typing import Any

import duckdb

from 共通 import card, codes, raw
from 共通.race_signals.race_scope import RaceScope
from 共通.race_signals.race_signals import RaceSignals
from 共通.race_signals.repository import AnnouncedOddsSummaryRepository, EntryCountRepository, RaceHeaderRepository

#: 出走馬の行が無いレース（木曜より前）の数。
_NO_ENTRIES = (0, 0, 0)
#: 締め切り前のオッズの無いレース。
_NO_ODDS = (None, 0)


class RaceSignalReader:
    """``RaceScope`` の範囲のレースについて、見出し（``ra``）・出走馬の数（``se``）・締め切り前のオッズ（``o1``）を読んでまとめる。

    SQL は持たない。読むのはリポジトリ（``repository/``）で、ここは結果を rid でつなぐだけ。事実表は作らない。
    """

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._headers = RaceHeaderRepository(con)
        self._entries = EntryCountRepository(con)
        self._odds = AnnouncedOddsSummaryRepository(con)

    def read(self, scope: RaceScope) -> list[RaceSignals]:
        """範囲のレースを、開催日・競馬場・レース番号の順に。"""
        entries = self._entries.read(scope)
        odds = self._odds.read(scope)
        return [self._signals(header, entries.get(header["rid"], _NO_ENTRIES), odds.get(header["rid"], _NO_ODDS))
                for header in self._headers.read(scope)]

    def read_days(self, date_from: str, date_to: str | None = None, venue_code: str | None = None) -> list[RaceSignals]:
        """開催日が ``date_from`` 以降（``date_to`` まで）のレース。"""
        return self.read(RaceScope.days(date_from, date_to, venue_code))

    def read_race(self, rid: str) -> RaceSignals:
        """1レース。DB に無ければ ``LookupError``。"""
        found = self.read(RaceScope.race(rid))
        if not found:
            raise LookupError(f"レースが見つかりません: {rid}")
        return found[0]

    @staticmethod
    def _signals(header: dict[str, Any], counts: tuple[int, int, int], odds: tuple[str | None, int]) -> RaceSignals:
        going = card.going_of(header["track"], header["turf"], header["dirt"])
        entries, numbered, weighed = counts
        announced_at, odds_count = odds
        return RaceSignals(
            rid=header["rid"], race_date=header["race_date"], venue_code=header["venue_code"], venue=codes.venue_name(header["venue_code"]),
            race_no=header["race_no"], post_time=raw.post_time(header["post"]) if header["post"] not in ("", "0000") else None,
            race_name=header["race_name"], class_name=codes.class_name(header["cond_code"], header["grade"]),
            course=codes.TRACK_NAMES.get(header["track"], header["track"]), stage=header["stage"],
            stage_name=codes.STAGE_NAMES.get(header["stage"], header["stage"]), entries=entries, numbered=numbered, weighed=weighed,
            going=going, going_announced=going != card.NOT_ANNOUNCED, odds_announced_at=announced_at, odds_count=odds_count,
        )
