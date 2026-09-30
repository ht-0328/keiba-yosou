"""開催日の間ずっと動き、各レースの発走の少し前に予想して記録し、最後に精算して成績をまとめる。"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

import duckdb

from フォワードテスト.clock import Clock
from フォワードテスト.forward_recorder import ForwardRecorder
from フォワードテスト.forward_summary import ForwardSummary
from フォワードテスト.ledger import Ledger
from フォワードテスト.settlement import Settlement

#: 1回に待つ長さの上限（秒）。発走時刻の変更に、この間隔で気づく。
_WAIT_STEP = 60.0
#: その日のレースが DB にまだ無いとき（jvdata-store の取り込み前）に、待ってみる長さ（分）と間隔（秒）。
_CARD_PATIENCE_MINUTES, _CARD_RETRY = 60, 300.0
#: DB が開けないときに待つ長さ（秒）と、あきらめるまでの回数。
_RETRY_WAIT, _RETRY_TIMES = 10.0, 30
#: 最後のレースの発走から精算を始めるまで（分）、精算をあきらめるまで（分）、精算をやり直す間隔（秒）。
_SETTLE_AFTER, _SETTLE_UNTIL, _SETTLE_RETRY = 40, 180, 600.0


class ForwardFollower:
    """開催日 ``day`` の各レースを、発走の ``minutes_before`` 分前になったら予想して記録する。

    オッズは jvdata-store の ``jvstore realtime --follow`` が発走の12分前に取り直すので、その断面で予想する。
    最後のレースの発走から40分たったら、結果が出たものから精算し、成績の文書を書き直す。
    発走を過ぎたレースと、記録済みのレースは予想しない（途中から動かしても、やり直しても、二重に記録しない）。
    DB を開けない（jvdata-store が書き込み中）ときは、少し待ってやり直す。
    """

    def __init__(self, predictor, ledger: Ledger, open_db: Callable[[], Any], *,
                 minutes_before: int = 10, clock: Clock | None = None, log: Callable[[str], None] = print) -> None:
        self._predictor = predictor
        self._ledger = ledger
        self._open_db = open_db
        self._recorder = ForwardRecorder(predictor, ledger)
        self._minutes_before = minutes_before
        self._clock = clock or Clock()
        self._log = log

    def run(self, day: str) -> None:
        """``day``（YYYY-MM-DD）の最後のレースが終わり、精算が済むまで動く。"""
        loaded = self._predictor.load_models()
        started = self._clock.now()
        posts: list[datetime] = []
        while True:
            races = [race for race in self._with_db(lambda con: self._predictor.races(con, day, "00:00")) if race["発走"]]
            if not races and self._clock.now() < started + timedelta(minutes=_CARD_PATIENCE_MINUTES):
                self._log("その日のレースが DB にまだありません。jvdata-store の取り込みを待ちます")
                self._clock.sleep(_CARD_RETRY)
                continue
            posts = [self._post(day, race) for race in races]
            recorded = self._ledger.recorded_races()
            pending = [(race, post) for race, post in zip(races, posts, strict=True)
                       if race["rid"] not in recorded and post > self._clock.now()]
            if not pending:
                break
            due = [race for race, post in pending if post - timedelta(minutes=self._minutes_before) <= self._clock.now()]
            if not due:
                earliest = min(post for _, post in pending) - timedelta(minutes=self._minutes_before)
                self._clock.sleep(min(_WAIT_STEP, (earliest - self._clock.now()).total_seconds()))
                continue
            self._with_db(lambda con: self._record(con, day, due, loaded))
        self._settle(max(posts) if posts else self._clock.now(), day)

    def _record(self, con: duckdb.DuckDBPyConnection, day: str, races: list[dict], loaded: list) -> None:
        for race in races:
            count = self._recorder.record(con, day, race, loaded, self._clock.now())
            self._log(f"{race['場']}{race['R']}R（{race['発走']}）を予想して記録しました（買い目 {count} 点）")

    def _settle(self, last_post: datetime, day: str) -> None:
        """最後のレースの発走から待ってから、結果が出たものを精算する。その日の買い目が全部精算できるまでくり返す。"""
        start, until = last_post + timedelta(minutes=_SETTLE_AFTER), last_post + timedelta(minutes=_SETTLE_UNTIL)
        while self._clock.now() < start:
            self._clock.sleep(min(_WAIT_STEP, (start - self._clock.now()).total_seconds()))
        settlement, summary = Settlement(self._ledger), ForwardSummary(self._ledger)
        while True:
            settled = self._with_db(lambda con: settlement.settle(con, self._clock.now()))
            path = summary.write(self._clock.now())
            waiting = self._waiting(day)
            self._log(f"{settled} 点を精算しました。未精算 {waiting} 点。成績: {path}")
            if waiting == 0 or self._clock.now() >= until:
                return
            self._clock.sleep(_SETTLE_RETRY)

    def _waiting(self, day: str) -> int:
        buys = self._ledger.buys()
        return int(((buys["開催日"] == day) & (buys["精算"] == "")).sum())

    def _with_db(self, action: Callable[[duckdb.DuckDBPyConnection], Any]) -> Any:
        for attempt in range(_RETRY_TIMES):
            try:
                with self._open_db() as con:
                    return action(con)
            except (duckdb.IOException, BlockingIOError) as error:
                if attempt == _RETRY_TIMES - 1:
                    raise
                self._log(f"DB を開けないので {_RETRY_WAIT:.0f} 秒待ってやり直します（{error.__class__.__name__}）")
                self._clock.sleep(_RETRY_WAIT)
        return None

    @staticmethod
    def _post(day: str, race: dict) -> datetime:
        return datetime.strptime(f"{day} {race['発走']}", "%Y-%m-%d %H:%M")
