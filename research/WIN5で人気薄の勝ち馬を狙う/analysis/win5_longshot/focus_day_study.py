"""詳しく見る日（例 2026-11-08）の WIN5 を、本線（今の買い目）と抑え（荒れる前提）で予想し直し、勝ち馬の順位と、本線・抑えに入ったかを見る。"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date

import pandas as pd

from 共通.render import Table

from yosou.form_aptitude_win5_tickets.leg import MARKET, SHARE, RaceWinShare
from yosou.form_aptitude_win5_tickets.payout import PayoutEstimator
from yosou.form_aptitude_win5_tickets.repository.win5_columns import HORSE_NO
from yosou.form_aptitude_win5_tickets.settlement import HIT, STRATEGY, Win5Outcome

from 印の成績.win5_backtest_day import Win5BacktestDay

from .hedge_candidate import CURRENT, NEW, HedgeCandidate
from .hedge_day_bets import HEDGE_PICKS, KIND, MAIN_PICKS, WITH_HEDGE, HedgeDayBets
from .upset_legs import UpsetLegs, popularity_of

#: 表に出す確率の名前。
_CURRENT_LABEL, _NEW_LABEL = "今のモデル", "人気薄の1着の予想を入れた確率"


@dataclass(frozen=True)
class FocusDayStudy:
    """``current`` と ``new`` は対象レース5つの全頭の表（列 レースID・馬番・単勝オッズ・1着になる確率。発売の順）。
    ``winners`` は5レースの勝ち馬の馬番（発売の順）。払戻は分からない日なので、当たりかどうかと、勝ち馬が入ったかだけを見る。"""

    current: Sequence[pd.DataFrame]
    new: Sequence[pd.DataFrame]
    winners: tuple[int, ...]

    def tables(self, race_date: str, history: pd.DataFrame, estimator: PayoutEstimator, handicap: frozenset[str],
               candidates: Sequence[HedgeCandidate]) -> list[Table]:
        days = {CURRENT: self._day(race_date, self.current), NEW: self._day(race_date, self.new)}
        outcome = Win5Outcome(race_date, ((self.winners, 0),), False, tuple(frozenset() for _ in self.winners), 0, 0)
        rows = [row for row in HedgeDayBets(history, UpsetLegs(handicap)).settle(days, candidates, estimator, outcome)
                if row[KIND] == WITH_HEDGE]
        if not rows:
            return [self._ranks(days, None), Table(["項目", "内容"], [["本線", "日の期待値が線に届かず、本線を買わない日"]], title="本線と抑え")]
        return [self._ranks(days, rows[0]), self._bets(rows)]

    def _day(self, race_date: str, legs: Sequence[pd.DataFrame]) -> Win5BacktestDay:
        shared = tuple(RaceWinShare().of(leg) for leg in legs)
        saturday = date.fromisoformat(race_date).weekday() == 5
        return Win5BacktestDay(race_date, "詳しく見る日", saturday, 0, shared, tuple("当日" for _ in shared))

    def _ranks(self, days: dict[str, Win5BacktestDay], row: dict[str, object] | None) -> Table:
        main = self._legs_of(row[MAIN_PICKS]) if row else [()] * len(self.winners)
        hedge = self._legs_of(row[HEDGE_PICKS]) if row else [()] * len(self.winners)
        rows = [self._rank_row(index, winner, days, main[index], hedge[index]) for index, winner in enumerate(self.winners)]
        return Table(["レース", "勝ち馬の馬番", "人気（締め切り前）", "オッズから見た勝率", f"{_CURRENT_LABEL}の確率", f"{_CURRENT_LABEL}の順位",
                      f"{_NEW_LABEL}", f"{_NEW_LABEL}の順位", "人気薄の中の順位", "本線に入ったか", "抑え（選んだもの）に入ったか"], rows,
                     title="勝ち馬に付けた確率と順位", note="確率はレースの中で合計 1 にそろえたもの。人気薄は10番人気以下。")

    @staticmethod
    def _legs_of(text: object) -> list[tuple[int, ...]]:
        if not text:
            return [()] * 5
        return [tuple(int(n) for n in part.split(",") if n) for part in str(text).split("/")]

    @staticmethod
    def _rank_row(index: int, winner: int, days: dict[str, Win5BacktestDay], main: tuple[int, ...], hedge: tuple[int, ...]) -> list[object]:
        current, new = days[CURRENT].legs[index], days[NEW].legs[index]
        popularity = popularity_of(new)
        found = new[HORSE_NO].astype(int) == winner
        current_found = current[HORSE_NO].astype(int) == winner
        longshot_rank = new.loc[popularity >= 10, SHARE].rank(ascending=False, method="min").reindex(new.index)[found]
        return [f"{index + 1}レース目", winner, int(popularity[found].iloc[0]), f"{float(new.loc[found, MARKET].iloc[0]):.3f}",
                f"{float(current.loc[current_found, SHARE].iloc[0]):.3f}", int(current[SHARE].rank(ascending=False, method="min")[current_found].iloc[0]),
                f"{float(new.loc[found, SHARE].iloc[0]):.3f}", int(new[SHARE].rank(ascending=False, method="min")[found].iloc[0]),
                "" if pd.isna(longshot_rank.iloc[0]) else int(longshot_rank.iloc[0]),
                "入った" if winner in main else "入らない", "入った" if winner in hedge else ("抑えなし" if not hedge else "入らない")]

    @staticmethod
    def _bets(rows: list[dict[str, object]]) -> Table:
        shown = [[row[STRATEGY], row[MAIN_PICKS], row[HEDGE_PICKS] or "（抑えなし）", "当たり" if row[HIT] else "外れ"] for row in rows]
        return Table(["買い方", "本線の買い目（馬番。レースは /）", "抑えの買い目", "WIN5"], shown, title="本線と抑えの買い目")
