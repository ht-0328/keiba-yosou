"""保存してあるばんえいの1レースの予想（道具「ばんえいの予想」の predict の JSON）から、通知の文と添付する表の画像を作る。
形は地方の通知（``LocalRaceMessage``）に合わせる: 見出しと時点・印の付いた馬（1つの印につき1行）・推奨買目、全頭の表は画像。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd

from 今週の予想.forecast_columns import HORSE_NAME, HORSE_NO, MARK, MARK_REASON, PLACE_VALUE, PROBABILITY, WIN_ODDS, WIN_PROBABILITY, WIN_VALUE
from 今週の予想.mark_rule import MARK_ORDER

from 発走前の通知.banei_forecast_store import BaneiForecastStore
from 発走前の通知.banei_race_card import NO_PICKS, NOTES, STAKE, BaneiRaceCard
from 発走前の通知.mark_lines import MarkLines
from 発走前の通知.race_frames import RaceFrames
from 発走前の通知.race_image import RaceImage
from 発走前の通知.race_jockeys import RaceJockeys
from 発走前の通知.race_notice import RaceNotice

#: 見出しに書く場の名前（レース一覧と同じ）。
VENUE = "ばんえい帯広"
#: ずれの強い組に付ける印。
STRONG = "★"
#: 予想の JSON のキー → 表の列名。
_COLUMNS: dict[str, str] = {"number": HORSE_NO, "name": HORSE_NAME, "mark": MARK, "mark_reason": MARK_REASON, "win_odds": WIN_ODDS,
                            "p_win": WIN_PROBABILITY, "p_top3": PROBABILITY, "win_value": WIN_VALUE, "place_value": PLACE_VALUE}


class BaneiRaceMessage:
    def __init__(self, store: BaneiForecastStore | None = None, *, frames: RaceFrames | None = None, jockeys: RaceJockeys | None = None,
                 image: RaceImage | None = None) -> None:
        self._store = store or BaneiForecastStore()
        self._frames = frames or RaceFrames()
        self._jockeys = jockeys or RaceJockeys()
        self._image = image or RaceImage()

    def build(self, rid: str) -> RaceNotice:
        forecast = self._store.load(rid)
        if forecast is None:
            raise LookupError(f"予想の結果がありません（{rid}）")
        card = self.card(forecast, self._frames.read(rid), self._jockeys.read(rid))
        path = self._store.image_path(rid)
        self._image.draw(card).save(path)
        return RaceNotice(self.describe(card), (path,))

    def card(self, forecast: dict[str, Any], frames: Mapping[int, int], jockeys: Mapping[int, str]) -> BaneiRaceCard:
        """予想の JSON・枠番・騎手名から、通知の中身を組む。"""
        post = str(forecast.get("post") or "")
        weighed = bool(forecast.get("body_weights"))
        water = forecast.get("water")
        lines = self._ticket_lines(forecast["picks"])
        return BaneiRaceCard(heading=f"{VENUE} {forecast['race_number']}R", name=self._name(forecast),
                             post=f"{post[:2]}:{post[2:]} 発走" if len(post) == 4 else "",
                             timing="当日の時点" if weighed else "馬体重が届く前の時点", race_day=weighed,
                             table=self._table(forecast), frames=dict(frames), jockeys=dict(jockeys), lines=lines, points=len(forecast["picks"]),
                             track=f"馬場水分 {water:.1f}%" if water is not None else "馬場水分 未発表")

    def describe(self, card: BaneiRaceCard) -> str:
        """通知の文: 見出しと時点・馬場水分・印の付いた馬（1つの印につき1行）・推奨買目。"""
        return "\n".join([f"**{card.title}** ばんえいの予想・{card.timing}", card.track, *MarkLines().lines(card.table), *self.bet_lines(card)])

    @staticmethod
    def bet_lines(card: BaneiRaceCard) -> list[str]:
        """推奨買目の行: 見出し（1点の金額と合計）・3連単の行・説明。無ければ「なし」と理由。"""
        if not card.lines:
            return [f"推奨買目: なし（{NO_PICKS}）"]
        return [f"推奨買目（1点 {STAKE}円・合計 {card.points}点 {card.points * STAKE:,}円）:", *card.lines, *(f"（{note}）" for note in NOTES)]

    @staticmethod
    def _name(forecast: dict[str, Any]) -> str:
        return " ".join(part for part in (forecast.get("race_name"), forecast.get("condition")) if part)

    @staticmethod
    def _table(forecast: dict[str, Any]) -> pd.DataFrame:
        """印の順（◎○▲△☆注、最後に無印）。同じ印の中は勝つ確率の高い順（JSON の並び）。値の無いオッズと期待値は欠損。"""
        frame = pd.DataFrame(forecast["runners"]).reindex(columns=list(_COLUMNS)).rename(columns=_COLUMNS)
        for column in (WIN_ODDS, WIN_VALUE, PLACE_VALUE):
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        order = frame[MARK].map({mark: index for index, mark in enumerate(MARK_ORDER)}).fillna(len(MARK_ORDER))
        return frame.assign(_order=order).sort_values("_order", kind="stable").drop(columns="_order").reset_index(drop=True)

    @staticmethod
    def _ticket_lines(picks: list[dict[str, Any]]) -> tuple[str, ...]:
        """1着の馬ごとに1行（例 ``3連単 ★8→1→7・8→1→3``）。行の順は、その行でいちばんずれの大きい組の順。"""
        groups: dict[int, list[str]] = {}
        for pick in picks:
            order = "→".join(str(number) for number in pick["order"])
            groups.setdefault(int(pick["order"][0]), []).append(f"{STRONG if pick['strong'] else ''}{order}")
        return tuple("3連単 " + "・".join(orders) for orders in groups.values())
