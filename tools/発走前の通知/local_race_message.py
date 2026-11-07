"""保存してある地方の1レースの予想（predict の JSON）から、通知の文（見出し・上位の印・推奨買目）と添付する表の画像を作る。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

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

from 地方の推奨買目.recommendation import STAKE
from 地方の推奨買目.recommendation_set import RecommendationSet

from 発走前の通知.local_bet_rule import LocalBetRule
from 発走前の通知.local_forecast_store import LocalForecastStore
from 発走前の通知.race_frames import RaceFrames
from 発走前の通知.local_race_card import LocalRaceCard
from 発走前の通知.mark_lines import MarkLines
from 発走前の通知.race_image import RaceImage
from 発走前の通知.local_race_schedule import LocalRaceSchedule
from 発走前の通知.race_notice import RaceNotice
from 発走前の通知.race_styles import RaceStyles
from 発走前の通知.scheduled_race import ScheduledRace
from 発走前の通知.tendencies import Tendencies


class Recommendations(Protocol):
    """地方の推奨買目を出す部品（本番は ``LocalRecommendations``）。"""

    def recommend(self, rid: str, forecast: dict[str, Any]) -> RecommendationSet: ...


class NoRecommendations:
    """推奨買目を出さない（全頭の予想の単勝・複勝だけ。テストと、係数が無い環境向け）。"""

    def recommend(self, rid: str, forecast: dict[str, Any]) -> RecommendationSet:
        return RecommendationSet((), "")

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


class LocalRaceMessage:
    """印は中央と同じ ``MarkRule``（◎○▲△☆注。地方には危険な人気馬の判定が無いので 消 は付かない）。
    文は 見出し・その日の馬場の傾向（``tendencies``。先に終わった同じ芝ダのレースがあれば）・印の付いた馬（``MarkLines``）・推奨買目（道具「地方の推奨買目」＋全頭の予想の単勝・複勝。``LocalBetRule``）だけにし、
    全頭の表は画像（``RaceImage``。推定脚質の列は ``styles``）にして添付する。画像は ``reports/発走前の通知/地方/<開催日>/<rid>.png`` に置く。"""

    def __init__(self, store: LocalForecastStore | None = None, schedule: LocalRaceSchedule | None = None,
                 marks: MarkRule | None = None, frames: RaceFrames | None = None, bets: LocalBetRule | None = None,
                 image: RaceImage | None = None, recommendations: Recommendations | None = None,
                 tendencies: Tendencies | None = None, styles: RaceStyles | None = None) -> None:
        self._store = store or LocalForecastStore()
        self._schedule = schedule or LocalRaceSchedule()
        self._marks = marks or MarkRule()
        self._frames = frames or RaceFrames()
        self._bets = bets or LocalBetRule()
        self._image = image or RaceImage()
        self._recommendations = recommendations or NoRecommendations()
        self._tendencies = tendencies
        self._styles = styles

    def build(self, rid: str) -> RaceNotice:
        forecast = self._store.load(rid)
        if forecast is None:
            raise LookupError(f"予想の結果がありません（{rid}）")
        race = self._find(rid)
        tendency = self._tendencies.of(rid, race.venue) if self._tendencies and race else None
        card = self.card(forecast, race, self._frames.read(rid), self._recommendations.recommend(rid, forecast),
                         tendency.text() if tendency else "", self._styles.read(rid) if self._styles else {})
        path = self._store.image_path(rid)
        self._image.draw(card).save(path)
        return RaceNotice(self.describe(card), (path,))

    def card(self, forecast: dict[str, Any], race: ScheduledRace | None, frames: Mapping[int, int],
             recommended: RecommendationSet | None = None, tendency: str = "",
             styles: Mapping[int, str] | None = None) -> LocalRaceCard:
        """predict の JSON（``columns``・``rows``・``title``）・レース一覧の行・推奨買目から、通知の中身を組む。"""
        table = self._ordered(self._marks.assign(self._table(forecast)))
        title = str(forecast.get("title", ""))
        race_day = RACE_DAY in title
        timing = f"{RACE_DAY}の時点" if race_day else "前日の時点（馬体重が届く前なのでオッズだけ）"
        bets = self._bets.pick(table, race_day, recommended or RecommendationSet((), ""))
        return LocalRaceCard(heading=f"{race.venue} {race.number}R" if race else title, name=race.name if race else "",
                             post=f"{race.post:%H:%M} 発走" if race else "", timing=timing, race_day=race_day, table=table,
                             frames=dict(frames), bets=bets, tendency=tendency, styles=dict(styles or {}))

    def describe(self, card: LocalRaceCard) -> str:
        """通知の文: 見出し・馬場の傾向（あれば）・印の付いた馬（1つの印につき1行）・推奨買目。"""
        return "\n".join([f"**{card.title}** 地方の予想・{card.timing}", *([card.tendency] if card.tendency else []),
                          *MarkLines().lines(card.table), *self.bet_lines(card.bets)])

    @staticmethod
    def bet_lines(bets: RecommendationSet) -> list[str]:
        """推奨買目の行: 見出し（1点の金額と合計）・券種ごとの組・添える理由。無ければ「なし」と理由。"""
        if bets.none:
            return [f"推奨買目: なし（{bets.reason}）"]
        lines = [f"推奨買目（1点 {STAKE}円・合計 {bets.points}点 {bets.yen:,}円）:", *bets.lines()]
        if bets.reason:
            lines.append(f"（{bets.reason}）")
        return lines

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
