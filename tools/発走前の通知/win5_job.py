"""WIN5 の段: その日の WIN5 を探し、1レース目の発走の前に 速報の取り込み → WIN5 の予想 → 買う計画の決め直し → 通知の文。"""

from __future__ import annotations

import sys
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Protocol

from 今週の予想.win5_record_store import Win5RecordStore

from 発走前の通知.race_notice import RaceNotice
from 発走前の通知.win5_message import Win5Message
from 発走前の通知.win5_slot import Win5Slot


# 部品のつなぎ目（中央の Win5Schedule・StoreFetcher・ForecastRunner）。テストは差し替える。


class Win5Source(Protocol):
    def read(self, day: str) -> Win5Slot | None: ...


class Win5Fetcher(Protocol):
    def fetch_win5(self, day: str) -> None: ...

    def fetch_races(self, day: str, rids: tuple[str, ...]) -> None: ...


class ProgramRunner(Protocol):
    def run(self, arguments: list[str], label: str, day: str) -> None: ...

    def log_path(self, day: str) -> Path: ...


class PlanRunner(Protocol):
    def run_plan(self, day: str) -> None: ...


def _stderr(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


class Win5Job:
    """``slot`` は、その日の WIN5 を元DB から読む。まだ無ければ、その日に1回だけ速報の WIN5（0B51）を取り込んで読み直す
    （jvdata-store の ``jvstore realtime`` が 0B51 を取らない版でも動くように）。元DB が使用中で読めなければ、前に読めたものを返す
    （まだ無ければ ``BlockingIOError`` をそのまま出し、呼ぶ側が後で読み直す）。

    ``build`` は、速報の WIN5 と、開催日単位の速報・対象レース5つのオッズを取り直し、WIN5 の予想（``predictor``。予算と線は予想のパッケージの既定）を
    動かし、記録が新しくなったことを確かめてから、その日の買う計画を決め直し（``planner``。WIN5 の買う計画と買い目の記録・まとめの WIN5 の節も
    書き直す。失敗しても文は出す）、通知の文を作る。予想が失敗したら ``RuntimeError``（呼ぶ側がその旨を投稿して、ほかのレースの通知を続ける）。
    """

    def __init__(self, *, schedule: Win5Source, fetcher: Win5Fetcher, predictor: ProgramRunner, planner: PlanRunner,
                 message: Win5Message, records: Win5RecordStore, log: Callable[[str], None] = _stderr) -> None:
        self._schedule = schedule
        self._fetcher = fetcher
        self._predictor = predictor
        self._planner = planner
        self._message = message
        self._records = records
        self._log = log
        self._fetched: set[str] = set()
        self._last: Win5Slot | None = None

    def slot(self, day: str) -> Win5Slot | None:
        """その日の WIN5。無い日は None。"""
        found = self._read(day)
        if found is None and day not in self._fetched:
            self._fetched.add(day)
            found = self._read(day) if self._fetch_win5(day) else None
        self._last = found
        return found

    def build(self, slot: Win5Slot) -> RaceNotice:
        self._fetcher.fetch_win5(slot.day)
        self._fetcher.fetch_races(slot.day, slot.race_ids)
        day = date.fromisoformat(slot.day)
        before = self._records.made_at(day)
        self._predictor.run(["--date", slot.day], "WIN5 の予想", slot.day)
        if self._records.made_at(day) in (None, before):
            raise RuntimeError(f"WIN5 の予想の結果が作られませんでした（記録: {self._predictor.log_path(slot.day)}）")
        self._replan(slot.day)
        return self._message.build(slot)

    def _read(self, day: str) -> Win5Slot | None:
        try:
            return self._schedule.read(day)
        except BlockingIOError:
            if self._last is None:
                raise
            self._log(f"WIN5 の対象レースを読み直せませんでした（元DB が使用中）。前に読んだ {self._last.label} で続けます")
            return self._last

    def _fetch_win5(self, day: str) -> bool:
        """速報の WIN5 を取り込む。失敗したら記録だけ残して False（WIN5 は飛ばし、ほかのレースの通知は続ける）。"""
        try:
            self._fetcher.fetch_win5(day)
        except Exception as error:  # noqa: BLE001 — WIN5 の取り込みが失敗しても、ほかのレースの通知は続ける
            self._log(f"速報の WIN5 を取り込めませんでした。{error}")
            return False
        return True

    def _replan(self, day: str) -> None:
        try:
            self._planner.run_plan(day)
        except Exception as error:  # noqa: BLE001 — 計画の決め直しが失敗しても、WIN5 の予想の文は出す
            self._log(f"WIN5 の予想のあとの買う計画の決め直しに失敗しました（文は予想の判断で出します）。{error}")
