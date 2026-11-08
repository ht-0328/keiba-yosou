"""1日の流れ: 朝の準備 → レースごとに発走の N 分前を待って、速報の取り込み → 予想 → Discord に投稿。
WIN5 のある日は、1レース目の発走の M 分前にも 速報の取り込み → WIN5 の予想 → 投稿。"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol

from 発走前の通知.race_notice import RaceNotice
from 発走前の通知.scheduled_race import ScheduledRace
from 発走前の通知.win5_slot import Win5Slot

#: 発走までこれより短いレースは通知しない（取り込みと予想に 1〜2分かかる）。
DEFAULT_MARGIN = timedelta(minutes=2)
#: 待つときに1回に眠る長さの上限。この間隔でレースの一覧を読み直し、発走時刻の変更を拾う。
MAX_NAP = timedelta(minutes=5)
#: 元DB が使用中（別の画面や道具がロックを持っている）で失敗したときに、やり直すまでの待ち。
LOCK_RETRY = timedelta(seconds=20)
#: やり直した取り込みと予想が発走に間に合うと見る、発走までの残り（取り込み 15 秒＋予想 1〜3 分）。
RETRY_ROOM = timedelta(minutes=4)
#: 失敗の文にこれがあれば、元DB が使用中だったと見る（自分のロック・別プロセスの予想や取り込みの出力・DuckDB のロック）。
LOCK_WORDS = ("使用中", "lock")
#: 失敗の知らせの頭に付ける印。
WARNING = "⚠"
#: WIN5 の取り込みと予想を始める時刻（1レース目の発走の何分前か）の既定。WIN5 の予想は 3〜6 分かかるので、レースの通知（10分前）より
#: 前に始め、1レース目の発走の 15〜20分前に投稿する（WIN5 の発売の締め切りに間に合わせる）。
DEFAULT_WIN5_MINUTES = 25
#: やり直した WIN5 の取り込みと予想が間に合うと見る、1レース目の発走までの残り（取り込み 30 秒＋予想 3〜6 分＋計画 1 分）。
WIN5_RETRY_ROOM = timedelta(minutes=8)


# 部品のつなぎ目。中央（RaceSchedule・StoreFetcher・ForecastRunner・RaceMessage・ForecastStore）と
# 地方（LocalRaceSchedule・StoreFetcher.local()・LocalForecastRunner・LocalRaceMessage・LocalForecastStore）を同じ流れで動かす。


class Schedule(Protocol):
    def read(self, day: str) -> list[ScheduledRace]: ...


class Fetcher(Protocol):
    def sync(self) -> None: ...

    def fetch_day(self, day: str) -> None: ...

    def fetch_race(self, day: str, rid: str) -> None: ...


class Runner(Protocol):
    def run_day(self, day: str) -> None: ...

    def run_race(self, rid: str, day: str) -> None: ...

    def log_path(self, day: str) -> Path: ...


class Message(Protocol):
    def build(self, rid: str) -> RaceNotice: ...


class SavedAt(Protocol):
    def saved_at(self, rid: str) -> datetime | None: ...


class Poster(Protocol):
    def post(self, text: str, attachments: Sequence[Path] = ()) -> None: ...


class Win5(Protocol):
    def slot(self, day: str) -> Win5Slot | None: ...

    def build(self, slot: Win5Slot) -> RaceNotice: ...


def _stderr(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


class DayNotifier:
    """朝の準備は 出馬表の取り込み → その日の速報の取り込み → 全レースの予想（複勝の勝負レースはその日の全レースの予想から決まる）。
    そのあと、発走の早い順に、発走の ``minutes_before`` 分前になったら 速報の取り込み → 予想 → 投稿。
    失敗しても止めず、その旨を投稿して次のレースへ進む。元DB が使用中（別の画面や道具がロックを持っている）で失敗したときは、
    発走に間に合う間は待ってやり直し、レースの一覧を読み直せないときは前に読んだ一覧で続ける。時計と眠りは差し替えられる（テストのため）。

    ``win5`` を渡すと（中央だけ）、WIN5 のある日は、1レース目の発走の ``win5_minutes`` 分前に WIN5 の段（``Win5Job.build``）を行って投稿する。
    待つ間は、そこより前に始めるレースの通知を先に行う。WIN5 の無い日・対象レースが元DB に無い日・1レース目の発走に間に合わない時刻に
    起動した日は、WIN5 だけを飛ばす。WIN5 が失敗しても、その旨を投稿して、ほかのレースの通知を続ける。
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
        #: 最後に読めたレースの一覧（元DB が使用中で読み直せないときに使う）。
        self._races: list[ScheduledRace] | None = None
        self._win5 = win5
        self._win5_minutes = win5_minutes
        #: その日の WIN5 をまだ通知していない（飛ばしてもいない）か。
        self._win5_pending = False

    def run(self, day: str, *, prepare: bool = True) -> int:
        """その日を最後のレースまで。レースが無ければ何も投稿せずに 1。"""
        if prepare and self._sync:
            self._prepare_step("出馬表の取り込み", self._fetcher.sync)
        if not self._read_schedule(day):
            self._log(f"{day} に予想するレースがありません（出馬表が DB に無ければ、jvstore sync か nvstore sync で取り込む）")
            return 1
        if prepare:
            self._prepare(day)
        done: set[str] = set()
        notified = 0
        self._win5_pending = self._win5 is not None
        while True:
            race = self._next_race(day, done)
            if self._win5_turn(day, race):
                continue
            if race is None:
                break
            if self._nap_until(race.due_at(self._minutes), race.label):
                continue
            notified += int(self.notify(race))
            done.add(race.rid)
        self._log(f"{day} の通知を終えました（{notified} レース）")
        return 0

    def notify(self, race: ScheduledRace) -> bool:
        """1レース分: 速報の取り込み → 予想 → 投稿。元DB が使用中で失敗したら、発走に間に合う間は待ってやり直す。
        それでも失敗したら、その旨を投稿して False。"""
        self._log(f"{race.label}: 速報を取り込んで予想します")
        return self._deliver(race.label, lambda: self._forecast(race), race.post - RETRY_ROOM)

    def notify_win5(self, slot: Win5Slot) -> bool:
        """WIN5 の段: 速報の取り込み → WIN5 の予想 → 買う計画の決め直し → 投稿（``notify`` と同じく、使用中ならやり直し、失敗は知らせる）。"""
        if self._win5 is None:
            raise RuntimeError("WIN5 の部品がありません（中央の通知だけが WIN5 を扱います）")
        win5 = self._win5
        self._log(f"{slot.label}: 速報を取り込んで WIN5 を予想します")
        return self._deliver(slot.label, lambda: win5.build(slot), slot.first_post - WIN5_RETRY_ROOM)

    def _deliver(self, label: str, build: Callable[[], RaceNotice], retry_until: datetime) -> bool:
        """``build`` で文を作って投稿する。元DB が使用中で失敗したら、待ってやり直しても ``retry_until`` より前なら、待ってやり直す。
        それでも失敗したら、その旨を投稿して False。"""
        while True:
            try:
                notice = build()
                self._poster.post(notice.text, notice.attachments)
            except Exception as error:  # noqa: BLE001 — どんな失敗でも次のレースへ進めるよう、理由を投稿して続ける
                if self._should_retry(retry_until, error):
                    self._log(f"{label}: 元DB が使用中でした。{LOCK_RETRY.total_seconds():.0f} 秒待ってやり直します")
                    self._sleep(LOCK_RETRY.total_seconds())
                    continue
                self._report_failure(label, error)
                return False
            self._log(f"{label}: 投稿しました")
            return True

    def _forecast(self, race: ScheduledRace) -> RaceNotice:
        self._fetcher.fetch_race(race.day, race.rid)
        before = self._store.saved_at(race.rid)
        self._runner.run_race(race.rid, race.day)
        if self._store.saved_at(race.rid) == before:
            raise RuntimeError(f"予想の結果が作られませんでした（記録: {self._runner.log_path(race.day)}）")
        return self._message.build(race.rid)

    def _should_retry(self, retry_until: datetime, error: Exception) -> bool:
        """元DB のロックが原因の失敗で、待ってやり直しても ``retry_until``（発走からやり直しに要る時間を引いた時刻）より前なら True。"""
        locked = isinstance(error, BlockingIOError) or any(word in str(error) for word in LOCK_WORDS)
        return locked and self._now() + LOCK_RETRY < retry_until

    def _report_failure(self, label: str, error: Exception) -> None:
        self._log(f"{label}: 失敗しました。{error}")
        try:
            self._poster.post(f"{WARNING} {label} の予想を通知できませんでした。\n{error}")
        except Exception as second:  # noqa: BLE001 — 知らせも出せないときは記録だけ残す
            self._log(f"{label}: 失敗の知らせも投稿できませんでした。{second}")

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

    def _win5_turn(self, day: str, race: ScheduledRace | None) -> bool:
        """WIN5 の番なら、始める時刻まで待つか、WIN5 の段を行って True（呼ぶ側はレースを選び直す）。WIN5 の番でなければ False。
        WIN5 の番は、まだ通知していない WIN5 があり、始める時刻が次のレースの始める時刻より前（か、次のレースが無い）とき。"""
        slot = self._pending_win5(day)
        if slot is None:
            return False
        due = slot.due_at(self._win5_minutes)
        if race is not None and race.due_at(self._minutes) < due:
            return False
        if self._nap_until(due, slot.label):
            return True
        self.notify_win5(slot)
        self._win5_pending = False
        return True

    def _pending_win5(self, day: str) -> Win5Slot | None:
        """まだ通知していない、間に合う WIN5。無い日・間に合わない日は、その旨を記録して以後は見ない。元DB が使用中なら、今回は None。"""
        if not self._win5_pending or self._win5 is None:
            return None
        try:
            slot = self._win5.slot(day)
        except BlockingIOError as error:
            self._log(f"WIN5 の対象レースを読めませんでした（{error}）。あとで読み直します")
            return None
        if slot is None:
            self._log(f"{day} は WIN5 が無いか、速報の WIN5 がまだ元DB に無いので、WIN5 は飛ばします")
        elif self._now() + WIN5_RETRY_ROOM >= slot.first_post:
            self._log(f"{slot.label}: 1レース目の発走に間に合わないので、WIN5 は飛ばします")
            slot = None
        self._win5_pending = slot is not None
        return slot

    def _nap_until(self, when: datetime, label: str) -> bool:
        """``when`` までの残りが無ければ False。あれば上限までの長さだけ眠って True（呼ぶ側はレースを選び直す）。"""
        remaining = when - self._now()
        if remaining <= timedelta(0):
            return False
        nap = min(remaining, MAX_NAP)
        self._log(f"{label}: {when:%H:%M} まで待ちます（あと {remaining.total_seconds() / 60:.0f} 分）")
        self._sleep(nap.total_seconds())
        return True
