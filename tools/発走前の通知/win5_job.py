"""WIN5 の段: その日の WIN5 を探し、速報の取り込みと元DB の写しを作って WIN5 の予想を裏で始め、終わったら通知の文を作る。"""

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


# 部品のつなぎ目（中央の Win5Schedule・StoreFetcher・DatabaseSnapshot・BackgroundProgram）。テストは差し替える。


class Win5Source(Protocol):
    def read(self, day: str) -> Win5Slot | None: ...


class Win5Fetcher(Protocol):
    def fetch_win5(self, day: str) -> None: ...

    def fetch_races(self, day: str, rids: tuple[str, ...]) -> None: ...


class Snapshot(Protocol):
    def take(self, day: str) -> Path: ...

    def remove(self, day: str) -> None: ...


class FigureCopier(Protocol):
    def copy(self, snapshot_db: Path) -> Path: ...


class Background(Protocol):
    def start(self, arguments: list[str], label: str, day: str) -> None: ...

    def finished(self) -> bool: ...

    @property
    def returncode(self) -> int | None: ...

    def tail(self) -> str: ...

    def kill(self) -> None: ...

    def log_path(self, day: str) -> Path: ...


def _stderr(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


class Win5Job:
    """``slot`` は、その日の WIN5 を元DB から読む。まだ無ければ、その日に1回だけ速報の WIN5（0B51）を取り込んで読み直す
    （jvdata-store の ``jvstore realtime`` が 0B51 を取らない版でも動くように）。元DB が使用中で読めなければ、前に読めたものを返す
    （まだ無ければ ``BlockingIOError`` をそのまま出し、呼ぶ側が後で読み直す）。

    ``start`` は、速報の WIN5 と、開催日単位の速報・対象レース5つのオッズを取り直し（数秒〜十数秒）、元DB の写しを作って（7 秒ほど）、
    WIN5 の予想（``predictor``。段階の予算と線は予想のパッケージの既定）を写しに向けて裏で始める。スピード指数のとっておきも写しの隣に写して渡す
    （``FigureCacheCopy``。本物のとっておきを写しの印で上書きして、あとのレースの予想を作り直しで遅らせないため）。裏の予想は写しだけを読むので、ほかのレースの
    取り込み（元DB への書き込み）と予想（元DB のロック）を邪魔しない。``finished`` で終わったかを確かめ、``build`` で写しを消して、
    記録が新しくなったことを確かめてから通知の文を作る（失敗なら記録の最後を添えて ``RuntimeError``）。``cancel`` は裏の予想を止める。

    買う計画（plan.json・回顧の表1・まとめの WIN5 の節）は、このあとのレースの予想（forecast.py がその日の計画を決め直す）で書き直される。
    通知の文の財布の判断は、同じ決まり（``Win5Planner``）でその場で出す（``Win5Message``）。
    """

    def __init__(self, *, schedule: Win5Source, fetcher: Win5Fetcher, snapshot: Snapshot, figures: FigureCopier, predictor: Background,
                 message: Win5Message, records: Win5RecordStore, log: Callable[[str], None] = _stderr) -> None:
        self._schedule = schedule
        self._fetcher = fetcher
        self._snapshot = snapshot
        self._figures = figures
        self._predictor = predictor
        self._message = message
        self._records = records
        self._log = log
        self._fetched: set[str] = set()
        self._last: Win5Slot | None = None
        #: 裏の予想を始める前の記録の時刻と、その開催日。
        self._before: str | None = None
        self._day = ""

    def slot(self, day: str) -> Win5Slot | None:
        """その日の WIN5。無い日は None。"""
        found = self._read(day)
        if found is None and day not in self._fetched:
            self._fetched.add(day)
            found = self._read(day) if self._fetch_win5(day) else None
        self._last = found
        return found

    def start(self, slot: Win5Slot) -> None:
        self._fetcher.fetch_win5(slot.day)
        self._fetcher.fetch_races(slot.day, slot.race_ids)
        copied = self._snapshot.take(slot.day)
        cache = self._figures.copy(copied)
        self._before, self._day = self._records.made_at(date.fromisoformat(slot.day)), slot.day
        self._predictor.start(["--date", slot.day, "--db", str(copied), "--figure-cache", str(cache)], "WIN5 の予想", slot.day)

    def finished(self) -> bool:
        return self._predictor.finished()

    def build(self, slot: Win5Slot) -> RaceNotice:
        self._snapshot.remove(slot.day)
        if self._predictor.returncode != 0:
            raise RuntimeError(f"WIN5 の予想に失敗しました（記録: {self._predictor.log_path(slot.day)}）:\n{self._predictor.tail()}")
        if self._records.made_at(date.fromisoformat(slot.day)) in (None, self._before):
            raise RuntimeError(f"WIN5 の予想の結果が作られませんでした（記録: {self._predictor.log_path(slot.day)}）")
        return self._message.build(slot)

    def cancel(self) -> None:
        self._predictor.kill()
        if self._day:
            self._snapshot.remove(self._day)

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
