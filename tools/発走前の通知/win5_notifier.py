"""1日の流れの中の WIN5: 始める時刻を決め、予想を裏で始め、終わったら投稿する（レースの通知は待たせない）。"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from 発走前の通知.day_notifier_protocols import Win5
from 発走前の通知.notice_delivery import NoticeDelivery
from 発走前の通知.win5_slot import Win5Slot

#: WIN5 の取り込みと予想を始める時刻（1レース目の発走の何分前か）の既定。WIN5 の予想は 3〜6 分かかるので、レースの通知（10分前）より
#: 前に始め、1レース目の発走の 15〜20分前に投稿する（WIN5 の発売の締め切りに間に合わせる）。
DEFAULT_WIN5_MINUTES = 25
#: 予想を始める前の段（取り込みと元DB の写し）をやり直しても間に合うと見る、1レース目の発走までの残り（前の段 30 秒＋予想 3〜6 分）。
#: これより遅く起動した日は WIN5 を飛ばす。
WIN5_RETRY_ROOM = timedelta(minutes=8)
#: 裏で予想している間に、1回に眠る長さの上限（終わったらすぐ投稿するため）。
WIN5_POLL = timedelta(seconds=20)


class Win5Notifier:
    """WIN5 の段の進み具合を持つ（1日に1回）。``DayNotifier`` がループの中で呼ぶ。

    - ``pending``: まだ始めていない、間に合う WIN5（無い日・間に合わない時刻に起動した日は、その旨を記録して以後は見ない）。
    - ``start``: 取り込みと元DB の写しまでを今の流れで済ませ（数十秒。元DB が使用中なら、1レース目の発走の 8 分前まで待ってやり直す）、
      予想は裏の処理として始めて、すぐ戻る。
    - ``check``: 裏の予想が終わっていれば文を作って投稿する。1レース目の発走時刻を過ぎても終わらない（か、過ぎてから終わった）ときは、
      投稿せずに「間に合わなかった」と知らせる。
    - ``wait``: 終わるまで待って投稿する（``notify.py --win5`` で今すぐ1回だけ出すとき。締め切りは見ない）。
    """

    def __init__(self, job: Win5, delivery: NoticeDelivery, *, minutes: int = DEFAULT_WIN5_MINUTES,
                 now: Callable[[], datetime] = datetime.now, sleep: Callable[[float], None], log: Callable[[str], None]) -> None:
        self._job = job
        self._delivery = delivery
        self._minutes = minutes
        self._now = now
        self._sleep = sleep
        self._log = log
        self._pending = False
        #: 裏で予想している WIN5（無ければ None）と、投稿の締め切り（None なら見ない）。
        self._running: Win5Slot | None = None
        self._deadline: datetime | None = None
        self.posted = False

    def begin_day(self) -> None:
        self._pending, self._running, self._deadline, self.posted = True, None, None, False

    @property
    def running(self) -> bool:
        return self._running is not None

    def start_at(self, slot: Win5Slot) -> datetime:
        return slot.due_at(self._minutes)

    def pending(self, day: str) -> Win5Slot | None:
        """まだ始めていない、間に合う WIN5。元DB が使用中で読めなければ、今回は None（あとで読み直す）。"""
        if not self._pending:
            return None
        try:
            slot = self._job.slot(day)
        except BlockingIOError as error:
            self._log(f"WIN5 の対象レースを読めませんでした（{error}）。あとで読み直します")
            return None
        if slot is None:
            self._log(f"{day} は WIN5 が無いか、速報の WIN5 がまだ元DB に無いので、WIN5 は飛ばします")
        elif self._now() + WIN5_RETRY_ROOM >= slot.first_post:
            self._log(f"{slot.label}: 1レース目の発走に間に合わないので、WIN5 は飛ばします")
            slot = None
        self._pending = slot is not None
        return slot

    def start(self, slot: Win5Slot, *, deadline: bool = True) -> bool:
        """取り込みと元DB の写しを済ませ、予想を裏で始める。始められなければ、その旨を投稿して False。"""
        self._pending = False
        self._log(f"{slot.label}: 速報を取り込み、WIN5 の予想を裏で始めます")
        if not self._delivery.attempt(slot.label, lambda: self._job.start(slot), slot.first_post - WIN5_RETRY_ROOM):
            return False
        self._running, self._deadline = slot, (slot.first_post if deadline else None)
        return True

    def check(self) -> None:
        """裏の予想が終わっていれば投稿する。締め切りを過ぎていれば止めて知らせる。"""
        slot = self._running
        if slot is None:
            return
        if self._deadline is not None and self._now() >= self._deadline:
            self._job.cancel()
            self._running = None
            self._delivery.warn(slot.label, f"{slot.label} の予想が1レース目の発走に間に合わなかったので、WIN5 は投稿しません。")
            return
        if not self._job.finished():
            return
        self._running = None
        self.posted = self._delivery.deliver(slot.label, lambda: self._job.build(slot), self._now())

    def nap_limit(self, limit: timedelta) -> timedelta:
        """眠る長さの上限（裏で予想している間は短くする）。"""
        return min(limit, WIN5_POLL) if self.running else limit

    def wait(self) -> bool:
        """裏の予想が終わるまで待って投稿する。投稿できたら True。"""
        while self.running:
            self._sleep(WIN5_POLL.total_seconds())
            self.check()
        return self.posted
