"""通知の文を作って投稿する（元DB が使用中なら待ってやり直し、失敗は知らせる）。"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from 発走前の通知.day_notifier_protocols import Poster
from 発走前の通知.race_notice import RaceNotice

#: 元DB が使用中（別の画面や道具がロックを持っている）で失敗したときに、やり直すまでの待ち。
LOCK_RETRY = timedelta(seconds=20)
#: 失敗の文にこれがあれば、元DB が使用中だったと見る（自分のロック・別プロセスの予想や取り込みの出力・DuckDB のロック）。
LOCK_WORDS = ("使用中", "lock")
#: 失敗の知らせの頭に付ける印。
WARNING = "⚠"


class NoticeDelivery:
    """``attempt`` は1つの段（取り込み → 予想 → 投稿、WIN5 の始め など）を行い、元DB が使用中で失敗したら、待ってやり直しても
    ``retry_until`` より前なら待ってやり直す。それでも失敗したら、その旨を投稿して False。``deliver`` は文を作って投稿する段。
    1日の流れ（``DayNotifier``）と WIN5 の段（``Win5Notifier``）が同じ決まりで使う。時計と眠りは差し替えられる（テストのため）。"""

    def __init__(self, poster: Poster, now: Callable[[], datetime], sleep: Callable[[float], None], log: Callable[[str], None]) -> None:
        self._poster = poster
        self._now = now
        self._sleep = sleep
        self._log = log

    def deliver(self, label: str, build: Callable[[], RaceNotice], retry_until: datetime) -> bool:
        """``build`` で文を作って投稿する。"""
        ok = self.attempt(label, lambda: self._post(build()), retry_until)
        if ok:
            self._log(f"{label}: 投稿しました")
        return ok

    def attempt(self, label: str, action: Callable[[], None], retry_until: datetime) -> bool:
        while True:
            try:
                action()
            except Exception as error:  # noqa: BLE001 — どんな失敗でも次のレースへ進めるよう、理由を投稿して続ける
                if self._should_retry(retry_until, error):
                    self._log(f"{label}: 元DB が使用中でした。{LOCK_RETRY.total_seconds():.0f} 秒待ってやり直します")
                    self._sleep(LOCK_RETRY.total_seconds())
                    continue
                self.report_failure(label, error)
                return False
            return True

    def warn(self, label: str, text: str) -> None:
        """知らせ（頭に ⚠）を投稿する。投稿できなければ記録だけ残す。"""
        self._log(f"{label}: {text}")
        try:
            self._poster.post(f"{WARNING} {text}")
        except Exception as error:  # noqa: BLE001 — 知らせも出せないときは記録だけ残す
            self._log(f"{label}: 知らせも投稿できませんでした。{error}")

    def report_failure(self, label: str, error: Exception) -> None:
        self.warn(label, f"{label} の予想を通知できませんでした。\n{error}")

    def _post(self, notice: RaceNotice) -> None:
        self._poster.post(notice.text, notice.attachments)

    def _should_retry(self, retry_until: datetime, error: Exception) -> bool:
        """元DB のロックが原因の失敗で、待ってやり直しても ``retry_until``（発走からやり直しに要る時間を引いた時刻）より前なら True。"""
        locked = isinstance(error, BlockingIOError) or any(word in str(error) for word in LOCK_WORDS)
        return locked and self._now() + LOCK_RETRY < retry_until
