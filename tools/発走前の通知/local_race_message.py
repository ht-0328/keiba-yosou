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
from 今週の予想.mark_rule import MARK_ORDER, NO_MARK, MarkRule

from 地方の直前の買い目.late_bet_file import LateBetFile
from 地方の直前の買い目.late_bets import LateBets

from 地方の推奨買目.mark_bets import MarkBets
from 地方の推奨買目.recommendation import STAKE
from 地方の推奨買目.recommendation_set import RecommendationSet

from 発走前の通知.local_bet_rule import LocalBetRule
from 発走前の通知.local_expectation import LocalExpectation
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
    """地方の推奨買目と印の買い目を出す部品（本番は ``LocalRecommendations``）。``marks`` の ``marked`` は印を付けた全頭の表。"""

    def recommend(self, rid: str, forecast: dict[str, Any]) -> RecommendationSet: ...

    def marks(self, rid: str, forecast: dict[str, Any], marked: pd.DataFrame) -> MarkBets: ...


class NoRecommendations:
    """推奨買目と印の買い目を出さない（全頭の予想の単勝・複勝だけ。テストと、係数が無い環境向け）。"""

    def recommend(self, rid: str, forecast: dict[str, Any]) -> RecommendationSet:
        return RecommendationSet((), "")

    def marks(self, rid: str, forecast: dict[str, Any], marked: pd.DataFrame) -> MarkBets:
        return MarkBets()

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
#: 印の買い目の見出し（中央の通知と同じ言葉）。
MARK_BETS_LABEL = "印の買い目"
#: 直前の買い目の見出し。実際の通知の時刻のオッズでの成績を確かめている間は「確かめ中」と添える。
LATE_BETS_LABEL = "直前の買い目（確かめ中・1点 100円）"


class LocalRaceMessage:
    """印は中央と同じ ``MarkRule``（◎○▲△☆注。地方には危険な人気馬の判定が無いので 消 は付かない）。
    文は 見出し・期待度（``LocalExpectation``。直前の買い目の線への近さの点数の S・A・B・C。中央の ◎ランク・配当率の代わりの1つの目安で、
    買い目と同じく当日の時点だけ出し、買い目は変えない）・
    その日の馬場の傾向（``tendencies``。先に終わった同じ芝ダのレースがあれば）・印の付いた馬（``MarkLines``）・推奨買目（道具「地方の推奨買目」＋全頭の予想の単勝・複勝。``LocalBetRule``）・
    印の買い目（道具「地方の推奨買目」の ``MarkRecommender``。単勝 ◎・馬単 ◎→○▲☆・3連単 ◎→○▲☆→○▲△☆ を 1レース 5,000円で配り、見込みの回収率で買うか見送るか。当日の時点だけ）だけにし、
    直前の買い目（道具「地方の直前の買い目」。発走前の予想が ``<rid>.直前.json`` に書いたものを読むだけ。単勝と、その馬を1着に固定した 3連単。
    推奨買目・印の買い目とは別の買い方で、合計には入れない。期待度はこの買い目の線への近さから出す）も当日の時点だけ出し、
    全頭の表は画像（``RaceImage``。推定脚質の列は ``styles``。見出しに期待度の札）にして添付する。画像は ``reports/発走前の通知/地方/<開催日>/<rid>.png`` に置く。"""

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
        self._late = LateBetFile()

    def build(self, rid: str) -> RaceNotice:
        forecast = self._store.load(rid)
        if forecast is None:
            raise LookupError(f"予想の結果がありません（{rid}）")
        race = self._find(rid)
        tendency = self._tendencies.of(rid, race.venue) if self._tendencies and race else None
        marks = self._recommendations.marks(rid, forecast, self.marked(forecast)) if self._race_day(forecast) else MarkBets()
        card = self.card(forecast, race, self._frames.read(rid), self._recommendations.recommend(rid, forecast),
                         tendency.text() if tendency else "", self._styles.read(rid) if self._styles else {}, marks,
                         self._late.read(self._store.late_path(rid)))
        path = self._store.image_path(rid)
        self._image.draw(card).save(path)
        return RaceNotice(self.describe(card), (path,))

    def marked(self, forecast: dict[str, Any]) -> pd.DataFrame:
        """predict の JSON の全頭に印を付け、印の順（◎○▲△☆注、最後に無印）に並べた表。"""
        return self._ordered(self._marks.assign(self._table(forecast)))

    def card(self, forecast: dict[str, Any], race: ScheduledRace | None, frames: Mapping[int, int],
             recommended: RecommendationSet | None = None, tendency: str = "",
             styles: Mapping[int, str] | None = None, marks: MarkBets | None = None, late: LateBets | None = None) -> LocalRaceCard:
        """predict の JSON（``columns``・``rows``・``title``）・レース一覧の行・推奨買目・印の買い目から、通知の中身を組む。"""
        table = self.marked(forecast)
        title = str(forecast.get("title", ""))
        race_day = self._race_day(forecast)
        timing = f"{RACE_DAY}の時点" if race_day else "前日の時点（馬体重が届く前なのでオッズだけ）"
        recommended = recommended or RecommendationSet((), "")
        bets = self._bets.pick(table, race_day, recommended)
        return LocalRaceCard(heading=f"{race.venue} {race.number}R" if race else title, name=race.name if race else "",
                             post=f"{race.post:%H:%M} 発走" if race else "", timing=timing, race_day=race_day, table=table,
                             frames=dict(frames), bets=bets, tendency=tendency, styles=dict(styles or {}),
                             expectation=LocalExpectation.of(late) if race_day else LocalExpectation.not_race_day(),
                             marks=marks if marks is not None and race_day else MarkBets(), late=late if race_day else None)

    def describe(self, card: LocalRaceCard) -> str:
        """通知の文: 見出し・期待度・馬場の傾向（あれば）・印の付いた馬（1つの印につき1行）・推奨買目・印の買い目（当日の時点）。"""
        return "\n".join([f"**{card.title}** 地方の予想・{card.timing}", card.expectation.text(), *([card.tendency] if card.tendency else []),
                          *MarkLines().lines(card.table), *self.bet_lines(card.bets), *self.mark_lines(card.marks), *self.late_lines(card.late, card.table)])

    @staticmethod
    def late_lines(late: LateBets | None, table: pd.DataFrame | None = None) -> list[str]:
        """直前の買い目の行: 買う馬がいれば見出しと 単勝・3連単の行、いなければ「なし（理由）」。ファイルが無ければ何も出さない。
        ``table``（印を付けた全頭の表）を渡すと、馬番のあとにその馬の印を添える（例 ``3☆``。無印の馬は馬番だけ）。"""
        if late is None:
            return []
        if late.empty:
            return [f"{LATE_BETS_LABEL}: なし（{late.reason}）"]
        marks = {} if table is None else {int(no): mark for no, mark in zip(table[HORSE_NO], table[MARK]) if pd.notna(no) and mark != NO_MARK}
        return [f"{LATE_BETS_LABEL}:", *(f"- {line}" for line in late.lines(lambda no: f"{no}{marks.get(no, '')}"))]

    @staticmethod
    def mark_lines(marks: MarkBets) -> list[str]:
        """印の買い目の行: 見出し（買うか見送りか・合計・当たったときに戻る額。出せなければ「なし（理由）」）と、買い方ごとの行。"""
        if marks.empty:
            return []
        return [f"{MARK_BETS_LABEL}: {marks.heading}", *(f"- {line}" for line in marks.lines)]

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
    def _race_day(forecast: dict[str, Any]) -> bool:
        return RACE_DAY in str(forecast.get("title", ""))

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
