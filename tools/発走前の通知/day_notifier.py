"""1日の流れ: 朝の準備 → レースごとに発走の N 分前を待って、速報の取り込み → 予想 → Discord に投稿。"""

from __future__ import annotations

import sys
import time
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Protocol

from 今週の予想.forecast_store import ForecastStore

from 発走前の通知.forecast_runner import ForecastRunner
from 発走前の通知.race_message import RaceMessage
from 発走前の通知.race_notice import RaceNotice
from 発走前の通知.race_schedule import RaceSchedule
from 発走前の通知.scheduled_race import ScheduledRace
from 発走前の通知.store_fetcher import StoreFetcher

#: 発走までこれより短いレースは通知しない（取り込みと予想に 1〜2分かかる）。
DEFAULT_MARGIN = timedelta(minutes=2)
#: 待つときに1回に眠る長さの上限。この間隔でレースの一覧を読み直し、発走時刻の変更を拾う。
MAX_NAP = timedelta(minutes=5)
#: 失敗の知らせの頭に付ける印。
WARNING = "⚠"


class Poster(Protocol):
    def post(self, text: str, attachment=None) -> None: ...


def _stderr(text: str) -> None:
    print(text, file=sys.stderr, flush=True)


class DayNotifier:
    """朝の準備は 出馬表の取り込み → その日の速報の取り込み → 全レースの予想（複勝の勝負レースはその日の全レースの予想から決まる）。
    そのあと、発走の早い順に、発走の ``minutes_before`` 分前になったら 速報の取り込み → 予想 → 投稿。
    失敗しても止めず、その旨を投稿して次のレースへ進む。時計と眠りは差し替えられる（テストのため）。
    """

    def __init__(self, *, minutes_before: int, schedule: RaceSchedule, fetcher: StoreFetcher, runner: ForecastRunner,
                 message: RaceMessage, poster: Poster, store: ForecastStore, sync: bool = True,
                 margin: timedelta = DEFAULT_MARGIN, now: Callable[[], datetime] = datetime.now,
                 sleep: Callable[[float], None] = time.sleep, log: Callable[[str], None] = _stderr) -> None:
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

    def run(self, day: str, *, prepare: bool = True) -> int:
        """その日を最後のレースまで。レースが無ければ何も投稿せずに 1。"""
        if prepare and self._sync:
            self._prepare_step("出馬表の取り込み", self._fetcher.sync)
        if not self._schedule.read(day):
            self._log(f"{day} に予想するレースがありません（出馬表が DB に無い週は、jvdata-store で jvstore sync）")
            return 1
        if prepare:
            self._prepare(day)
        done: set[str] = set()
        notified = 0
        while True:
            race = self._next_race(day, done)
            if race is None:
                break
            if self._nap_until(race.due_at(self._minutes), race):
                continue
            notified += int(self.notify(race))
            done.add(race.rid)
        self._log(f"{day} の通知を終えました（{notified} レース）")
        return 0

    def notify(self, race: ScheduledRace) -> bool:
        """1レース分: 速報の取り込み → 予想 → 投稿。失敗したら、その旨を投稿して False。"""
        self._log(f"{race.label}: 速報を取り込んで予想します")
        try:
            notice = self._forecast(race)
            self._poster.post(notice.text, notice.attachment)
        except Exception as error:  # noqa: BLE001 — どんな失敗でも次のレースへ進めるよう、理由を投稿して続ける
            self._report_failure(race, error)
            return False
        self._log(f"{race.label}: 投稿しました")
        return True

    def _forecast(self, race: ScheduledRace) -> RaceNotice:
        self._fetcher.fetch_race(race.day, race.rid)
        before = self._store.saved_at(race.rid)
        self._runner.run_race(race.rid, race.day)
        if self._store.saved_at(race.rid) == before:
            raise RuntimeError(f"予想の結果が作られませんでした（記録: {self._runner.log_path(race.day)}）")
        return self._message.build(race.rid)

    def _report_failure(self, race: ScheduledRace, error: Exception) -> None:
        self._log(f"{race.label}: 失敗しました。{error}")
        try:
            self._poster.post(f"{WARNING} {race.label} の予想を通知できませんでした。\n{error}")
        except Exception as second:  # noqa: BLE001 — 知らせも出せないときは記録だけ残す
            self._log(f"{race.label}: 失敗の知らせも投稿できませんでした。{second}")

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

    def _next_race(self, day: str, done: set[str]) -> ScheduledRace | None:
        """まだ通知していない、発走まで余裕のあるレースのうち一番早いもの。発走時刻の変更を拾うため、毎回 DB から読み直す。"""
        limit = self._now() + self._margin
        races = self._schedule.read(day)
        self._skip_passed(races, done, limit)
        remaining = [race for race in races if race.rid not in done]
        return remaining[0] if remaining else None

    def _skip_passed(self, races: list[ScheduledRace], done: set[str], limit: datetime) -> None:
        passed = [race for race in races if race.rid not in done and race.post <= limit]
        for race in passed:
            self._log(f"{race.label}: 発走が近い（または過ぎた）ので通知しません")
            done.add(race.rid)

    def _nap_until(self, when: datetime, race: ScheduledRace) -> bool:
        """``when`` までの残りが無ければ False。あれば上限までの長さだけ眠って True（呼ぶ側はレースを選び直す）。"""
        remaining = when - self._now()
        if remaining <= timedelta(0):
            return False
        nap = min(remaining, MAX_NAP)
        self._log(f"{race.label}: {when:%H:%M} まで待ちます（あと {remaining.total_seconds() / 60:.0f} 分）")
        self._sleep(nap.total_seconds())
        return True
