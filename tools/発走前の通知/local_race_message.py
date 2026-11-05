"""保存してある地方の1レースの予想（predict の JSON）から、印と買い目つきの通知の文を作る。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from 今週の予想.forecast_columns import (
    HORSE_NAME,
    HORSE_NO,
    MARK,
    MARKET_TOP3,
    PLACE_VALUE,
    PROBABILITY,
    WIN_ODDS,
    WIN_PROBABILITY,
    WIN_VALUE,
)
from 今週の予想.mark_rule import TOP_MARK, MarkRule
from 今週の予想.ticket_rules import PLACE_VALUE_LINE

from 発走前の通知.local_forecast_store import LocalForecastStore
from 発走前の通知.local_race_schedule import LocalRaceSchedule
from 発走前の通知.race_notice import RaceNotice
from 発走前の通知.scheduled_race import ScheduledRace

#: predict の表の列名 → 印の決め方（MarkRule）が使う列名。
_COLUMNS: dict[str, str] = {
    "馬番": HORSE_NO,
    "馬名": HORSE_NAME,
    "単勝オッズ": WIN_ODDS,
    "オッズから見た3着以内率": MARKET_TOP3,
    "複勝の期待値": PLACE_VALUE,
    "1着になる確率": WIN_PROBABILITY,
    "単勝の期待値": WIN_VALUE,
    "3着以内に入る確率": PROBABILITY,
}
#: 単勝を買う ◎ の単勝の期待値の線（地方で採用している買い方。当日の時点だけ）。
WIN_VALUE_LINE = 1.00
#: 1点の金額（円）。
STAKE = 100
#: 当日の時点の見出し（predict の title に入る言葉）。
RACE_DAY = "当日"
#: 表の見出し。
HEADER = "印 馬番 馬名 | 単勝 | 3着以内 | 1着 | 複勝の期待値 | 単勝の期待値"


class LocalRaceMessage:
    """印は中央と同じ ``MarkRule``（◎○▲△☆注。地方には危険な人気馬の判定が無いので 消 は付かない）。
    買い目は地方で採用している「当日の ◎ の単勝（期待値 1.00 以上）」と「当日の複勝（期待値 1.25 以上）」だけ。
    前日の時点（馬体重が届く前。オッズだけ）は買い目を出さず、その旨を書く。添付は無い。"""

    def __init__(self, store: LocalForecastStore | None = None, schedule: LocalRaceSchedule | None = None,
                 marks: MarkRule | None = None) -> None:
        self._store = store or LocalForecastStore()
        self._schedule = schedule or LocalRaceSchedule()
        self._marks = marks or MarkRule()

    def build(self, rid: str) -> RaceNotice:
        forecast = self._store.load(rid)
        if forecast is None:
            raise LookupError(f"予想の結果がありません（{rid}）")
        return RaceNotice(self.describe(forecast, self._find(rid)), None)

    def describe(self, forecast: dict[str, Any], race: ScheduledRace | None) -> str:
        """predict の JSON（``columns``・``rows``・``title``）から、見出し・全頭の表（印の順）・買い目。"""
        table = self._marks.assign(self._table(forecast))
        race_day = RACE_DAY in str(forecast.get("title", ""))
        timing = f"{RACE_DAY}の時点" if race_day else "前日の時点（馬体重が届く前なのでオッズだけ）"
        label = race.label if race else str(forecast.get("title", ""))
        lines = [f"**{label}** 地方の予想・{timing}", HEADER]
        lines += [self._row(row) for _, row in table.iterrows()]
        lines += ["", *self._bets(table, race_day)]
        return "\n".join(lines)

    @staticmethod
    def _table(forecast: dict[str, Any]) -> pd.DataFrame:
        frame = pd.DataFrame(forecast["rows"], columns=forecast["columns"])
        return frame[list(_COLUMNS)].rename(columns=_COLUMNS)

    @staticmethod
    def _row(row: pd.Series) -> str:
        return (f"{row[MARK]} {int(row[HORSE_NO])} {row[HORSE_NAME]} | {row[WIN_ODDS]:.1f} | {row[PROBABILITY]:.0%} | "
                f"{row[WIN_PROBABILITY]:.0%} | {row[PLACE_VALUE]:.2f} | {row[WIN_VALUE]:.2f}")

    @staticmethod
    def _bets(table: pd.DataFrame, race_day: bool) -> list[str]:
        if not race_day:
            return ["買い目: なし（馬体重が届く前の前日の時点では買わない）"]
        bets: list[str] = []
        top = table[table[MARK] == TOP_MARK]
        if not top.empty and top.iloc[0][WIN_VALUE] >= WIN_VALUE_LINE:
            pick = top.iloc[0]
            bets.append(f"単勝 ◎{int(pick[HORSE_NO])} {pick[HORSE_NAME]}（期待値 {pick[WIN_VALUE]:.2f}）{STAKE}円")
        for _, row in table[table[PLACE_VALUE] >= PLACE_VALUE_LINE].iterrows():
            bets.append(f"複勝 {int(row[HORSE_NO])} {row[HORSE_NAME]}（期待値 {row[PLACE_VALUE]:.2f}）{STAKE}円")
        if not bets:
            return [f"買い目: なし（単勝は ◎ の期待値 {WIN_VALUE_LINE:.2f} 以上、複勝は期待値 {PLACE_VALUE_LINE:.2f} 以上のときだけ買う）"]
        return ["実際に買う:", *bets]

    def _find(self, rid: str) -> ScheduledRace | None:
        day = f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}"
        return next((race for race in self._schedule.read(day) if race.rid == rid), None)
