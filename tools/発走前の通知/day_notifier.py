"""1日の流れ: 朝の準備 → レースごとに発走の N 分前を待って、速報の取り込み → 予想 → Discord に投稿。
WIN5 のある日は、1レース目の発走の M 分前に速報を取り込んで WIN5 の予想を裏で始め、終わったら投稿する（レースの通知は待たせない）。"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from datetime import datetime, timedelta

from 発走前の通知.day_notifier_protocols import Fetcher, Message, Poster, Runner, SavedAt, Schedule, Win5
from 発走前の通知.notice_delivery import LOCK_RETRY, LOCK_WORDS, WARNING, NoticeDelivery
from 発走前の通知.race_notice import RaceNotice
from 発走前の通知.scheduled_race import ScheduledRace
from 発走前の通知.win5_notifier import DEFAULT_WIN5_MINUTES, Win5Notifier
from 発走前の通知.win5_slot import Win5Slot

__all__ = ["DayNotifier", "Fetcher", "Message", "Poster", "Runner", "SavedAt", "Schedule", "Win5", "LOCK_RETRY", "LOCK_WORDS", "WARNING"]

#: 発走までこれより短いレースは通知しない（取り込みと予想に 1〜2分かかる）。
DEFAULT_MARGIN = timedelta(minutes=2)
#: 待つときに1回に眠る長さの上限。この間隔でレースの一覧を読み直し、発走時刻の変更を拾う。
MAX_NAP = timedelta(minutes=5)
#: やり直した取り込みと予想が発走に間に合うと見る、発走までの残り（取り込み 15 秒＋予想 1〜3 分）。
RETRY_ROOM = timedelta(minutes=4)


def _stderr(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


class DayNotifier:
    """朝の準備は 出馬表の取り込み → その日の速報の取り込み → 全レースの予想（複勝の勝負レースはその日の全レースの予想から決まる）。
    そのあと、発走の早い順に、発走の ``minutes_before`` 分前になったら 速報の取り込み → 予想 → 投稿。
    失敗しても止めず、その旨を投稿して次のレースへ進む。元DB が使用中（別の画面や道具がロックを持っている）で失敗したときは、
    発走に間に合う間は待ってやり直し、レースの一覧を読み直せないときは前に読んだ一覧で続ける（``NoticeDelivery``）。
    時計と眠りは差し替えられる（テストのため）。

    ``win5`` を渡すと（中央だけ）、WIN5 のある日は、1レース目の発走の ``win5_minutes`` 分前に、取り込みと元DB の写しだけをこの流れで済ませ、
    WIN5 の予想は裏の処理として始める（``Win5Notifier``）。ループは待たずにほかのレースへ進み、回るたびに裏の予想が終わったかを確かめて、
    終わっていれば投稿する（裏で予想している間は、眠りを 20 秒ずつにする）。裏の予想は元DB の写しを読むので、ほかのレースの取り込みと
    予想とは元DB を取り合わない。WIN5 の無い日・対象レースが元DB に無い日・1レース目の発走に間に合わない時刻に起動した日は WIN5 だけを飛ばし、
    1レース目の発走時刻までに予想が終わらなければ投稿せずに知らせる。
    """

    def __init__(self, *, minutes_before: int, schedule: Schedule, fetcher: Fetcher, runner: Runner,
                 message: Message, poster: Poster, store: SavedAt, sync: bool = True,
                 margin: timedelta = DEFAULT_MARGIN, now: Callable[[], datetime] = datetime.now,
                 sleep: Callable[[float], None] = time.sleep, log: Callable[[str], None] = _stderr,
                 win5: Win5 | None = None, win5_minutes: int = DEFAULT_WIN5_MINUTES) -> None:
        self._minutes = minutes_before
        self._schedule = schedule
        self._fetcher = fetcher
        self._runner = runner
        self._message = message
        self._poster = poster
        self._store = store
        self._sync = sync
        self._margin = margin
        self._now = now
        self._sleep = sleep
        self._log = log
        self._delivery = NoticeDelivery(poster, now, sleep, log)
        #: 最後に読めたレースの一覧（元DB が使用中で読み直せないときに使う）。
        self._races: list[ScheduledRace] | None = None
        self._win5 = Win5Notifier(win5, self._delivery, minutes=win5_minutes, now=now, sleep=sleep, log=log) if win5 else None

    def run(self, day: str, *, prepare: bool = True) -> int:
        """その日を最後のレースまで（裏で WIN5 を予想していれば、それが終わるまで）。レースが無ければ何も投稿せずに 1。"""
        if prepare and self._sync:
            self._prepare_step("出馬表の取り込み", self._fetcher.sync)
        if not self._read_schedule(day):
            self._log(f"{day} に予想するレースがありません（出馬表が DB に無ければ、jvstore sync か nvstore sync で取り込む）")
            return 1
        if prepare:
            self._prepare(day)
        done: set[str] = set()
        notified = 0
        if self._win5 is not None:
            self._win5.begin_day()
        while True:
            self._check_win5()
            race = self._next_race(day, done)
            if self._win5_turn(day, race):
                continue
            if race is None and not self._win5_running():
                break
            if race is None or self._nap_until(race.due_at(self._minutes), race.label):
                self._nap_while_win5(race)
                continue
            notified += int(self.notify(race))
            done.add(race.rid)
        self._log(f"{day} の通知を終えました（{notified} レース）")
        return 0

    def notify(self, race: ScheduledRace) -> bool:
        """1レース分: 速報の取り込み → 予想 → 投稿。元DB が使用中で失敗したら、発走に間に合う間は待ってやり直す。
        それでも失敗したら、その旨を投稿して False。"""
        self._log(f"{race.label}: 速報を取り込んで予想します")
        return self._delivery.deliver(race.label, lambda: self._forecast(race), race.post - RETRY_ROOM)

    def notify_win5(self, slot: Win5Slot) -> bool:
        """WIN5 だけを今すぐ: 取り込みと元DB の写し → 裏の予想が終わるまで待つ → 投稿（``notify.py --win5``。締め切りは見ない）。"""
        if self._win5 is None:
            raise RuntimeError("WIN5 の部品がありません（中央の通知だけが WIN5 を扱います）")
        self._win5.begin_day()
        return self._win5.start(slot, deadline=False) and self._win5.wait()

    def _forecast(self, race: ScheduledRace) -> RaceNotice:
        self._fetcher.fetch_race(race.day, race.rid)
        before = self._store.saved_at(race.rid)
        self._runner.run_race(race.rid, race.day)
        if self._store.saved_at(race.rid) == before:
            raise RuntimeError(f"予想の結果が作られませんでした（記録: {self._runner.log_path(race.day)}）")
        return self._message.build(race.rid)

    def _prepare(self, day: str) -> None:
        """速報の取り込み → 全レースの予想。どちらかが失敗したら、その旨を投稿して（レースごとの通知は続ける）。"""
        if self._prepare_step("速報の取り込み", lambda: self._fetcher.fetch_day(day)):
            self._prepare_step("全レースの予想", lambda: self._runner.run_day(day))

    def _prepare_step(self, label: str, step: Callable[[], None]) -> bool:
        try:
            step()
        except Exception as error:  # noqa: BLE001 — 朝の準備が失敗しても、レースごとの通知は続ける
            self._log(f"{label}に失敗しました。{error}")
            self._poster.post(f"{WARNING} 朝の準備（{label}）に失敗しました。レースごとの通知は続けます。\n{error}")
            return False
        return True

    def _read_schedule(self, day: str) -> list[ScheduledRace]:
        """レースの一覧を DB から読み直す。元DB が使用中で読めなければ、前に読めた一覧で続ける（まだ無ければ待って読み直す）。"""
        while True:
            try:
                self._races = self._schedule.read(day)
                return self._races
            except BlockingIOError as error:
                if self._races is not None:
                    self._log(f"レースの一覧を読み直せませんでした（{error}）。前に読んだ一覧で続けます")
                    return self._races
                self._log(f"レースの一覧を読めませんでした（{error}）。{LOCK_RETRY.total_seconds():.0f} 秒待って読み直します")
                self._sleep(LOCK_RETRY.total_seconds())

    def _next_race(self, day: str, done: set[str]) -> ScheduledRace | None:
        """まだ通知していない、発走まで余裕のあるレースのうち一番早いもの。発走時刻の変更を拾うため、毎回 DB から読み直す。"""
        limit = self._now() + self._margin
        races = self._read_schedule(day)
        self._skip_passed(races, done, limit)
        remaining = [race for race in races if race.rid not in done]
        return remaining[0] if remaining else None

    def _skip_passed(self, races: list[ScheduledRace], done: set[str], limit: datetime) -> None:
        passed = [race for race in races if race.rid not in done and race.post <= limit]
        for race in passed:
            self._log(f"{race.label}: 発走が近い（または過ぎた）ので通知しません")
            done.add(race.rid)

    def _check_win5(self) -> None:
        if self._win5 is not None:
            self._win5.check()

    def _win5_running(self) -> bool:
        return self._win5 is not None and self._win5.running

    def _win5_turn(self, day: str, race: ScheduledRace | None) -> bool:
        """WIN5 を始める番なら、始める時刻まで待つか、WIN5 を始めて True（呼ぶ側はレースを選び直す）。番でなければ False。
        番は、まだ始めていない WIN5 があり、始める時刻が次のレースの始める時刻より前（か、次のレースが無い）とき。"""
        slot = self._win5.pending(day) if self._win5 is not None else None
        if slot is None:
            return False
        due = self._win5.start_at(slot)
        if race is not None and race.due_at(self._minutes) < due:
            return False
        if self._nap_until(due, slot.label):
            return True
        self._win5.start(slot)
        return True

    def _nap_while_win5(self, race: ScheduledRace | None) -> None:
        """次のレースが無く、裏で WIN5 を予想しているときだけ、終わるのを短く待つ（レースがあれば ``_nap_until`` が眠っている）。"""
        if race is None and self._win5_running():
            self._sleep(self._nap_limit().total_seconds())

    def _nap_limit(self) -> timedelta:
        return self._win5.nap_limit(MAX_NAP) if self._win5 is not None else MAX_NAP

    def _nap_until(self, when: datetime, label: str) -> bool:
        """``when`` までの残りが無ければ False。あれば上限までの長さだけ眠って True（呼ぶ側はレースを選び直す）。"""
        remaining = when - self._now()
        if remaining <= timedelta(0):
            return False
        nap = min(remaining, self._nap_limit())
        self._log(f"{label}: {when:%H:%M} まで待ちます（あと {remaining.total_seconds() / 60:.0f} 分）")
        self._sleep(nap.total_seconds())
        return True
