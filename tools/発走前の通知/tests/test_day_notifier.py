"""DayNotifier（1日の流れ）のテスト。取り込み・予想・投稿・時計は全部差し替える。値は架空。"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from 今週の予想.forecast_store import ForecastStore
from 今週の予想.tests.test_forecast_store import sample_forecast

from 発走前の通知.day_notifier import DayNotifier
from 発走前の通知.race_notice import RaceNotice
from 発走前の通知.scheduled_race import ScheduledRace
from 発走前の通知.win5_slot import Win5Slot

DAY = "2025-04-19"
RACE1 = ScheduledRace("2025041905010101", "東京", 1, "", datetime(2025, 4, 19, 10, 0))
RACE2 = ScheduledRace("2025041905010102", "東京", 2, "", datetime(2025, 4, 19, 10, 30))
#: 元DB が使用中のときの失敗の文（別プロセスの予想の出力の最後の行と同じ形）。
LOCKED = "予想に失敗しました:\nBlockingIOError: DB を別の画面（取得の道具など）で使用中です。終わってから実行してください。"


class _Clock:
    def __init__(self, start: datetime) -> None:
        self.now = start
        self.naps: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.naps.append(seconds)
        self.now += timedelta(seconds=seconds)


class _Schedule:
    """``locked`` 番目の読み出しは元DB が使用中（BlockingIOError）。"""

    def __init__(self, races: list[ScheduledRace], locked: tuple[int, ...] = ()) -> None:
        self.races = races
        self._locked = set(locked)
        self.reads = 0

    def read(self, day: str) -> list[ScheduledRace]:
        self.reads += 1
        if self.reads in self._locked:
            raise BlockingIOError("DB を別の画面（取得の道具など）で使用中です。終わってから実行してください。")
        return list(self.races)


class _Fetcher:
    def __init__(self, calls: list[str], fail: str = "") -> None:
        self._calls = calls
        self._fail = fail

    def sync(self) -> None:
        self._record("sync")

    def fetch_day(self, day: str) -> None:
        self._record(f"fetch_day {day}")

    def fetch_race(self, day: str, rid: str) -> None:
        self._record(f"fetch_race {rid}")

    def _record(self, call: str) -> None:
        self._calls.append(call)
        if call.startswith(self._fail or "\0"):
            raise RuntimeError(f"{call} に失敗")


class _Runner:
    """予想したことにして、結果を保存する（作った時刻を進める）。``fail`` のレースは失敗、``silent`` のレースは結果を作らない。
    ``locked`` 回は元DB が使用中の文で失敗する。"""

    def __init__(self, store: ForecastStore, calls: list[str], fail: str = "", silent: str = "", locked: int = 0) -> None:
        self._store = store
        self._calls = calls
        self._fail = fail
        self._silent = silent
        self._locked = locked
        self._count = 0

    def run_day(self, day: str) -> None:
        self._calls.append(f"run_day {day}")

    def run_race(self, rid: str, day: str) -> None:
        self._calls.append(f"run_race {rid}")
        if self._locked > 0:
            self._locked -= 1
            raise RuntimeError(LOCKED)
        if rid == self._fail:
            raise RuntimeError("予想できません")
        if rid == self._silent:
            return
        self._count += 1
        self._store.save({**sample_forecast(rid), "made_at": f"2025-04-19T10:00:{self._count:02d}"})

    def log_path(self, day: str) -> Path:
        return Path(f"{day}.log")


class _Message:
    def build(self, rid: str) -> RaceNotice:
        return RaceNotice(f"文 {rid}")


class _Poster:
    def __init__(self) -> None:
        self.posts: list[str] = []

    def post(self, text: str, attachment=None) -> None:
        self.posts.append(text)


class _Win5:
    """WIN5 の段の代わり。``start`` で裏の予想を始めたことにし、時計が ``done_at`` を過ぎたら終わったことにする。
    どの時刻に何をしたかを ``calls`` に残す（レースの通知が WIN5 を待っていないかを確かめるため）。"""

    def __init__(self, slot: Win5Slot | None, calls: list[str], clock: _Clock, *, done_at: datetime | None = None,
                 fail_start: bool = False) -> None:
        self._slot = slot
        self._calls = calls
        self._clock = clock
        self._done_at = done_at
        self._fail_start = fail_start

    def slot(self, day: str) -> Win5Slot | None:
        return self._slot

    def start(self, slot: Win5Slot) -> None:
        if self._fail_start:
            raise RuntimeError("WIN5 の取り込みに失敗")
        self._calls.append(f"win5 start {self._clock.now:%H:%M}")

    def finished(self) -> bool:
        return self._done_at is not None and self._clock.now >= self._done_at

    def build(self, slot: Win5Slot) -> RaceNotice:
        self._calls.append(f"win5 post {self._clock.now:%H:%M:%S}")
        return RaceNotice("文 WIN5")

    def cancel(self) -> None:
        self._calls.append(f"win5 cancel {self._clock.now:%H:%M}")


class _TimedFetcher(_Fetcher):
    """そのレースの取り込みを始めた時刻も残す。"""

    def __init__(self, calls: list[str], clock: _Clock) -> None:
        super().__init__(calls)
        self._clock = clock

    def fetch_race(self, day: str, rid: str) -> None:
        self._calls.append(f"fetch_race {rid} {self._clock.now:%H:%M}")


#: 1レース目が 10:35 発走の WIN5（25分前の 10:10 に始める）。
WIN5_SLOT = Win5Slot(DAY, ("2025041905010110", "2025041908010110", "2025041903010111", "2025041905010111", "2025041908010111"),
                     (datetime(2025, 4, 19, 10, 35),) + (None,) * 4)


def _notifier(tmp_path: Path, clock: _Clock, races: list[ScheduledRace], calls: list[str], poster: _Poster, *,
              fetch_fail: str = "", run_fail: str = "", run_silent: str = "", run_locked: int = 0,
              schedule_locked: tuple[int, ...] = (), win5: _Win5 | None = None) -> DayNotifier:
    store = ForecastStore(tmp_path)
    return DayNotifier(minutes_before=10, schedule=_Schedule(races, schedule_locked), fetcher=_Fetcher(calls, fetch_fail),
                       runner=_Runner(store, calls, run_fail, run_silent, run_locked), message=_Message(), poster=poster, store=store,
                       now=lambda: clock.now, sleep=clock.sleep, log=lambda _: None, win5=win5, win5_minutes=25)


def test_朝の準備のあと発走10分前ごとに取り込んで予想して投稿する(tmp_path: Path) -> None:
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 9, 40)), [], _Poster()
    assert _notifier(tmp_path, clock, [RACE1, RACE2], calls, poster).run(DAY) == 0
    assert calls == ["sync", f"fetch_day {DAY}", f"run_day {DAY}", f"fetch_race {RACE1.rid}", f"run_race {RACE1.rid}",
                     f"fetch_race {RACE2.rid}", f"run_race {RACE2.rid}"]
    assert poster.posts == [f"文 {RACE1.rid}", f"文 {RACE2.rid}"]
    # 9:40 → 9:50 は 5分ずつ2回、10:20 までは 5分ずつ6回
    assert clock.naps == [300.0] * 8


def test_遅れて起動したら待たずに通知し_発走が近いレースは飛ばす(tmp_path: Path) -> None:
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 9, 59)), [], _Poster()
    late = ScheduledRace("2025041905010103", "東京", 3, "", datetime(2025, 4, 19, 10, 5))
    _notifier(tmp_path, clock, [RACE1, late, RACE2], calls, poster).run(DAY, prepare=False)
    assert calls == [f"fetch_race {late.rid}", f"run_race {late.rid}", f"fetch_race {RACE2.rid}", f"run_race {RACE2.rid}"]
    assert poster.posts[0] == f"文 {late.rid}"
    # 遅れていた 3R はすぐ通知し、2R（10:30）の 10 分前（10:20）までは 5分ずつ待つ
    assert clock.naps == [300.0] * 4 + [60.0]


def test_レースが無ければ何も投稿せず1(tmp_path: Path) -> None:
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 8, 30)), [], _Poster()
    assert _notifier(tmp_path, clock, [], calls, poster).run(DAY) == 1
    assert calls == ["sync"]
    assert poster.posts == []


def test_予想に失敗したら知らせて次のレースへ(tmp_path: Path) -> None:
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 9, 55)), [], _Poster()
    _notifier(tmp_path, clock, [RACE1, RACE2], calls, poster, run_fail=RACE1.rid).run(DAY, prepare=False)
    assert poster.posts[0].startswith(f"⚠ {RACE1.label} の予想を通知できませんでした。\n予想できません")
    assert poster.posts[1] == f"文 {RACE2.rid}"


def test_結果が作られなかったら知らせる(tmp_path: Path) -> None:
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 9, 55)), [], _Poster()
    notifier = _notifier(tmp_path, clock, [RACE1], calls, poster, run_silent=RACE1.rid)
    assert notifier.notify(RACE1) is False
    assert "予想の結果が作られませんでした" in poster.posts[0]


def test_朝の準備が失敗しても知らせてレースごとの通知は続ける(tmp_path: Path) -> None:
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 9, 55)), [], _Poster()
    _notifier(tmp_path, clock, [RACE1], calls, poster, fetch_fail="fetch_day").run(DAY)
    assert f"run_day {DAY}" not in calls
    assert poster.posts[0].startswith("⚠ 朝の準備（速報の取り込み）に失敗しました")
    assert poster.posts[1] == f"文 {RACE1.rid}"


def test_元DBが使用中で予想に失敗したら待ってやり直す(tmp_path: Path) -> None:
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 9, 50)), [], _Poster()
    assert _notifier(tmp_path, clock, [RACE1], calls, poster, run_locked=1).run(DAY, prepare=False) == 0
    assert calls == [f"fetch_race {RACE1.rid}", f"run_race {RACE1.rid}", f"fetch_race {RACE1.rid}", f"run_race {RACE1.rid}"]
    assert clock.naps == [20.0]
    assert poster.posts == [f"文 {RACE1.rid}"]


def test_元DBが使用中のまま発走が近づいたら知らせて次のレースへ(tmp_path: Path) -> None:
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 9, 55)), [], _Poster()
    _notifier(tmp_path, clock, [RACE1, RACE2], calls, poster, run_locked=2).run(DAY, prepare=False)
    # 9:55:00 と 9:55:20 は 20 秒待ってやり直し、3回目で成功する
    assert calls.count(f"run_race {RACE1.rid}") == 3
    assert clock.naps[:2] == [20.0, 20.0]
    assert poster.posts == [f"文 {RACE1.rid}", f"文 {RACE2.rid}"]
    # ずっと使用中なら、発走 4 分前を切ったところ（3回目の失敗）であきらめて知らせる
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 9, 55)), [], _Poster()
    _notifier(tmp_path, clock, [RACE1], calls, poster, run_locked=99).run(DAY, prepare=False)
    assert calls.count(f"run_race {RACE1.rid}") == 3
    assert poster.posts[0].startswith(f"⚠ {RACE1.label} の予想を通知できませんでした。")


def test_レースの一覧を読み直せなくても前に読んだ一覧で続ける(tmp_path: Path) -> None:
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 9, 55)), [], _Poster()
    # 1回目（起動時）は読め、待つ間の読み直し（2〜4回目）は元DB が使用中
    assert _notifier(tmp_path, clock, [RACE1, RACE2], calls, poster, schedule_locked=(2, 3, 4)).run(DAY, prepare=False) == 0
    assert poster.posts == [f"文 {RACE1.rid}", f"文 {RACE2.rid}"]
    assert 20.0 not in clock.naps


def test_起動時に元DBが使用中なら待って読み直す(tmp_path: Path) -> None:
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 9, 55)), [], _Poster()
    assert _notifier(tmp_path, clock, [RACE1], calls, poster, schedule_locked=(1,)).run(DAY, prepare=False) == 0
    assert clock.naps[0] == 20.0
    assert poster.posts == [f"文 {RACE1.rid}"]


def _win5_notifier(tmp_path: Path, clock: _Clock, calls: list[str], poster: _Poster, win5: _Win5) -> DayNotifier:
    store = ForecastStore(tmp_path)
    return DayNotifier(minutes_before=10, schedule=_Schedule([RACE1, RACE2]), fetcher=_TimedFetcher(calls, clock),
                       runner=_Runner(store, calls), message=_Message(), poster=poster, store=store,
                       now=lambda: clock.now, sleep=clock.sleep, log=lambda _: None, win5=win5, win5_minutes=25)


def _timeline(calls: list[str]) -> list[str]:
    return [call for call in calls if not call.startswith("run_race")]


def test_WIN5は25分前に裏で始め_終わったら投稿し_レースの通知は待たない(tmp_path: Path) -> None:
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 9, 55)), [], _Poster()
    win5 = _Win5(WIN5_SLOT, calls, clock, done_at=datetime(2025, 4, 19, 10, 16))
    assert _win5_notifier(tmp_path, clock, calls, poster, win5).run(DAY, prepare=False) == 0
    assert _timeline(calls) == [f"fetch_race {RACE1.rid} 09:55", "win5 start 10:10", "win5 post 10:16:00", f"fetch_race {RACE2.rid} 10:20"]
    assert poster.posts == [f"文 {RACE1.rid}", "文 WIN5", f"文 {RACE2.rid}"]


def test_WIN5の予想が長引いてもレースの通知は発走10分前ちょうどに行い_そのあとWIN5を投稿する(tmp_path: Path) -> None:
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 9, 55)), [], _Poster()
    win5 = _Win5(WIN5_SLOT, calls, clock, done_at=datetime(2025, 4, 19, 10, 24))
    _win5_notifier(tmp_path, clock, calls, poster, win5).run(DAY, prepare=False)
    assert _timeline(calls) == [f"fetch_race {RACE1.rid} 09:55", "win5 start 10:10", f"fetch_race {RACE2.rid} 10:20", "win5 post 10:24:00"]
    assert poster.posts == [f"文 {RACE1.rid}", f"文 {RACE2.rid}", "文 WIN5"]


def test_1レース目の発走までにWIN5の予想が終わらなければ止めて間に合わなかったと知らせる(tmp_path: Path) -> None:
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 9, 55)), [], _Poster()
    win5 = _Win5(WIN5_SLOT, calls, clock, done_at=None)
    assert _win5_notifier(tmp_path, clock, calls, poster, win5).run(DAY, prepare=False) == 0
    assert "win5 cancel 10:35" in calls and not any(call.startswith("win5 post") for call in calls)
    assert poster.posts[:2] == [f"文 {RACE1.rid}", f"文 {RACE2.rid}"]
    assert poster.posts[2] == f"⚠ {WIN5_SLOT.label} の予想が1レース目の発走に間に合わなかったので、WIN5 は投稿しません。"


def test_WIN5を始められなくても知らせてレースの通知を続ける(tmp_path: Path) -> None:
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 9, 55)), [], _Poster()
    win5 = _Win5(WIN5_SLOT, calls, clock, fail_start=True)
    _win5_notifier(tmp_path, clock, calls, poster, win5).run(DAY, prepare=False)
    assert poster.posts[1].startswith(f"⚠ {WIN5_SLOT.label} の予想を通知できませんでした。\nWIN5 の取り込みに失敗")
    assert poster.posts[2] == f"文 {RACE2.rid}"


def test_WIN5の無い日と間に合わない日はWIN5だけ飛ばす(tmp_path: Path) -> None:
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 9, 55)), [], _Poster()
    _win5_notifier(tmp_path, clock, calls, poster, _Win5(None, calls, clock)).run(DAY, prepare=False)
    assert not any(call.startswith("win5") for call in calls)
    assert poster.posts == [f"文 {RACE1.rid}", f"文 {RACE2.rid}"]
    # 1レース目の発走（10:35）の 8 分前を過ぎて起動したら、WIN5 は飛ばす
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 10, 28)), [], _Poster()
    late = ScheduledRace("2025041905010103", "東京", 3, "", datetime(2025, 4, 19, 11, 0))
    store = ForecastStore(tmp_path)
    DayNotifier(minutes_before=10, schedule=_Schedule([late]), fetcher=_Fetcher(calls), runner=_Runner(store, calls), message=_Message(),
                poster=poster, store=store, now=lambda: clock.now, sleep=clock.sleep, log=lambda _: None,
                win5=_Win5(WIN5_SLOT, calls, clock, done_at=datetime(2025, 4, 19, 10, 30)), win5_minutes=25).run(DAY, prepare=False)
    assert not any(call.startswith("win5") for call in calls)
    assert poster.posts == [f"文 {late.rid}"]


def test_WIN5だけ今すぐは終わるまで待って投稿する_締め切りは見ない(tmp_path: Path) -> None:
    clock, calls, poster = _Clock(datetime(2025, 4, 19, 20, 0)), [], _Poster()
    win5 = _Win5(WIN5_SLOT, calls, clock, done_at=datetime(2025, 4, 19, 20, 4))
    assert _win5_notifier(tmp_path, clock, calls, poster, win5).notify_win5(WIN5_SLOT)
    assert calls == ["win5 start 20:00", "win5 post 20:04:00"]
    assert poster.posts == ["文 WIN5"]
