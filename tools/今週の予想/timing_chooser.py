"""1レースを、どの時点（木曜・前日・当日）のモデルで予想するかを決める。"""

from __future__ import annotations

import duckdb

from 共通 import card

from yosou.shared.feature import PredictionTiming
from yosou.shared.repository import AnnouncedOddsRepository

from 今週の予想.timing_choice import TimingChoice

_HORSE_NO = card.ENTRY_HEADERS.index("馬番")
_BODY_WEIGHT = card.ENTRY_HEADERS.index("馬体重")
_NOT_ANNOUNCED = "未発表"


class TimingChooser:
    """DB に入っている情報から、いちばん新しい時点のモデルを選ぶ（設計書「近走と適性から3着以内を予想」07）。

    - 当日: 締め切り前の単勝オッズがあり、馬場状態と馬体重が発表されている。
    - 前日: 締め切り前の単勝オッズがあり、馬番が決まっている（出馬表）。
    - 木曜: それより前（オッズが無い・出走馬名表の段階）。
    オッズは jvdata-store の ``jvstore realtime --date <開催日>`` で取り込む。
    """

    def choose(self, con: duckdb.DuckDBPyConnection, race_id: str) -> TimingChoice:
        header = card.race_header(con, race_id)
        entries = card.race_card(con, race_id, runs=0).entries.rows
        has_odds = not AnnouncedOddsRepository(con).read(race_id).dropna(subset=["odds"]).empty
        numbered = bool(entries) and all(row[_HORSE_NO] for row in entries)
        weighed = bool(entries) and sum(1 for row in entries if row[_BODY_WEIGHT]) * 2 >= len(entries)
        if not has_odds:
            return TimingChoice(PredictionTiming.THURSDAY, "締め切り前のオッズがまだ DB に無いので、木曜（オッズを使わない）のモデル")
        if weighed and header["馬場"] != _NOT_ANNOUNCED:
            return TimingChoice(PredictionTiming.RACE_DAY, "馬体重と馬場状態が発表され、オッズもあるので、当日のモデル")
        if numbered:
            return TimingChoice(PredictionTiming.DAY_BEFORE, "出馬表（馬番）とオッズがあるので、前日のモデル（馬体重はまだ使わない）")
        return TimingChoice(PredictionTiming.THURSDAY, "馬番がまだ決まっていないので、木曜のモデル")
