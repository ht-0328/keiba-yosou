"""買い目の記録（表1）の未精算の WIN5 の行に、元DB の WIN5 の当たり組から払戻を書き足す。"""

from __future__ import annotations

from datetime import timedelta

import duckdb
import pandas as pd

from yosou.form_aptitude_win5_tickets.formation import Formation
from yosou.form_aptitude_win5_tickets.repository import Win5HistoryRepository, Win5ScratchRepository
from yosou.form_aptitude_win5_tickets.settlement import Win5Outcome, Win5Outcomes, Win5Settlement
from yosou.review import ReviewStore, names

from 今週の予想.win5_combo import combo_legs


class Win5BetSettler:
    """表1の未精算の WIN5 の行（ポリシー（WIN5））のうち、元DB に結果（成績の版の WIN5）が入った日のものを、予想のパッケージの
    ``Win5Settlement`` で精算する（当たり組の払戻と、出走取消・競走除外の馬を含む組の返還）。払戻は買った財布（ポリシー用）に戻る。

    結果は月曜の成績の版で入るので、精算はその週の次の予想のときになる。``Win5Settlement`` は1点 100円で数えるので、記録の金額に合わせて掛け直す。
    """

    def __init__(self, store: ReviewStore) -> None:
        self._store = store

    def settle(self, con: duckdb.DuckDBPyConnection) -> int:
        """精算した行の数。"""
        pending = self._store.read(names.BETS_TABLE, f"NOT {names.SETTLED} AND {names.TICKET_TYPE} = ?", [names.WIN5_TICKET])
        if pending.empty:
            return 0
        until = pd.to_datetime(pending[names.RACE_DATE]).max().date() + timedelta(days=1)
        outcomes = Win5Outcomes().of(Win5HistoryRepository(con).read(until), Win5ScratchRepository(con).read(until))
        settled = [row for row in (self._settled(bet, outcomes) for _, bet in pending.iterrows()) if row is not None]
        return self._store.write(names.BETS_TABLE, pd.DataFrame(settled)) if settled else 0

    def _settled(self, bet: pd.Series, outcomes: dict[str, Win5Outcome]) -> dict | None:
        """1行を精算した行。その日の結果がまだ無ければ None。"""
        outcome = outcomes.get(pd.Timestamp(bet[names.RACE_DATE]).date().isoformat())
        if outcome is None:
            return None
        result = Win5Settlement().settle(Formation(combo_legs(bet[names.COMBO])), outcome)
        payout = result.payout * float(bet[names.STAKE_YEN]) / result.stake
        return {**bet.to_dict(), names.PAYOUT_YEN: int(round(payout)), names.SETTLED: True}
