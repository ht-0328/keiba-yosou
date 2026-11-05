"""保存してある地方の1レースの予想（predict の JSON）から、通知の文（見出し・上位の印・買い目）と添付する表の画像を作る。"""

from __future__ import annotations

from collections.abc import Mapping
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
from 今週の予想.mark_rule import MARK_ORDER, MarkRule

from 発走前の通知.local_bet_rule import LocalBetRule
from 発走前の通知.local_forecast_store import LocalForecastStore
from 発走前の通知.local_frames import LocalFrames
from 発走前の通知.local_race_card import LocalRaceCard
from 発走前の通知.local_race_image import LocalRaceImage
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
#: 当日の時点の見出し（predict の title に入る言葉）。
RACE_DAY = "当日"
#: 文に書く上位の印（◎○▲）。
_LEAD_MARKS = MARK_ORDER[:3]


class LocalRaceMessage:
    """印は中央と同じ ``MarkRule``（◎○▲△☆注。地方には危険な人気馬の判定が無いので 消 は付かない）。
    文は 見出し・◎○▲の馬・買い目（``LocalBetRule``）だけにし、全頭の表は画像（``LocalRaceImage``）にして添付する。
    画像は ``reports/発走前の通知/地方/<開催日>/<rid>.png`` に置く。"""

    def __init__(self, store: LocalForecastStore | None = None, schedule: LocalRaceSchedule | None = None,
                 marks: MarkRule | None = None, frames: LocalFrames | None = None, bets: LocalBetRule | None = None,
                 image: LocalRaceImage | None = None) -> None:
        self._store = store or LocalForecastStore()
        self._schedule = schedule or LocalRaceSchedule()
        self._marks = marks or MarkRule()
        self._frames = frames or LocalFrames()
        self._bets = bets or LocalBetRule()
        self._image = image or LocalRaceImage()

    def build(self, rid: str) -> RaceNotice:
        forecast = self._store.load(rid)
        if forecast is None:
            raise LookupError(f"予想の結果がありません（{rid}）")
        card = self.card(forecast, self._find(rid), self._frames.read(rid))
        path = self._store.image_path(rid)
        self._image.draw(card).save(path)
        return RaceNotice(self.describe(card), path)

    def card(self, forecast: dict[str, Any], race: ScheduledRace | None, frames: Mapping[int, int]) -> LocalRaceCard:
        """predict の JSON（``columns``・``rows``・``title``）とレース一覧の行から、通知の中身を組む。"""
        table = self._ordered(self._marks.assign(self._table(forecast)))
        title = str(forecast.get("title", ""))
        race_day = RACE_DAY in title
        timing = f"{RACE_DAY}の時点" if race_day else "前日の時点（馬体重が届く前なのでオッズだけ）"
        return LocalRaceCard(heading=f"{race.venue} {race.number}R" if race else title, name=race.name if race else "",
                             post=f"{race.post:%H:%M} 発走" if race else "", timing=timing, race_day=race_day, table=table,
                             frames=dict(frames), bets=self._bets.pick(table, race_day))

    def describe(self, card: LocalRaceCard) -> str:
        """通知の文: 見出し・◎○▲の馬・買い目。"""
        return "\n".join([f"**{card.title}** 地方の予想・{card.timing}", self._lead(card.table), *card.bets.text()])

    @staticmethod
    def _lead(table: pd.DataFrame) -> str:
        leads = table[table[MARK].isin(_LEAD_MARKS)]
        return "　".join(f"{row[MARK]} {int(row[HORSE_NO])} {row[HORSE_NAME]}" for _, row in leads.iterrows())

    @staticmethod
    def _table(forecast: dict[str, Any]) -> pd.DataFrame:
        frame = pd.DataFrame(forecast["rows"], columns=forecast["columns"])
        return frame[list(_COLUMNS)].rename(columns=_COLUMNS)

    @staticmethod
    def _ordered(table: pd.DataFrame) -> pd.DataFrame:
        """印の順（◎○▲△☆注、最後に無印）。同じ印の中は 3着以内の確率の高い順。"""
        order = table[MARK].map({mark: index for index, mark in enumerate(MARK_ORDER)}).fillna(len(MARK_ORDER))
        return table.assign(_order=order).sort_values(["_order", PROBABILITY], ascending=[True, False]).drop(columns="_order")

    def _find(self, rid: str) -> ScheduledRace | None:
        day = f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}"
        return next((race for race in self._schedule.read(day) if race.rid == rid), None)
