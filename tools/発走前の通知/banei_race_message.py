"""ばんえいの1レースの通知の文（見出し・馬場水分・印・3連単の買い目）。"""

from __future__ import annotations

from typing import Any

from 発走前の通知.banei_forecast_store import BaneiForecastStore
from 発走前の通知.race_notice import RaceNotice

#: 見出しに書く場の名前。
VENUE = "帯広（ばんえい）"
#: 1点の金額（円）。
UNIT = 100
#: ずれの強い組に付ける印。
STRONG = "★"
#: 買い目の説明（文の最後に添える）。
NOTE = ("買い目は、予想の組の確率が 1% 以上で、世間の見立てより 1.5倍以上高い組（★ は 2倍以上）。オッズは見ていない。"
        "過去8年の通算は 約120%（年によっては 100% を割ることがある。確かめ中）。")


class BaneiRaceMessage:
    def __init__(self, store: BaneiForecastStore | None = None) -> None:
        self._store = store or BaneiForecastStore()

    def build(self, rid: str) -> RaceNotice:
        forecast = self._store.load(rid)
        if forecast is None:
            raise RuntimeError(f"{rid} の予想がありません")
        lines = [self._headline(forecast), self._track(forecast), "", *self._marks(forecast), "", *self._tickets(forecast)]
        return RaceNotice(text="\n".join(lines))

    @staticmethod
    def _headline(forecast: dict[str, Any]) -> str:
        post = str(forecast.get("post") or "")
        time = f"（{post[:2]}:{post[2:]} 発走）" if len(post) == 4 else ""
        name = " ".join(part for part in (forecast.get("race_name"), forecast.get("condition")) if part)
        return f"**{VENUE} {forecast['race_number']}R {name}{time}**"

    @staticmethod
    def _track(forecast: dict[str, Any]) -> str:
        water = forecast.get("water")
        track = f"馬場水分 {water:.1f}%" if water is not None else "馬場水分 未発表"
        weights = "" if forecast.get("body_weights") else "・馬体重は未着（馬体重なしで予想）"
        return f"{track}{weights}"

    @staticmethod
    def _marks(forecast: dict[str, Any]) -> list[str]:
        marked = [runner for runner in forecast["runners"] if runner["mark"]]
        return [f"{runner['mark']} {runner['number']} {runner['name']}（勝つ確率 {runner['p_win'] * 100:.0f}%・世間の見立て {runner['c_win'] * 100:.0f}%）"
                for runner in marked]

    @staticmethod
    def _tickets(forecast: dict[str, Any]) -> list[str]:
        picks = forecast["picks"]
        if not picks:
            return ["3連単: 買う組なし（見送り。世間の見立てとずれた組が無い）"]
        lines = [f"3連単 {len(picks)}点・{len(picks) * UNIT:,}円（1点 {UNIT}円）"]
        for pick in picks:
            order = "→".join(str(number) for number in pick["order"])
            mark = f"{STRONG} " if pick["strong"] else ""
            lines.append(f"{mark}{order}（確率 {pick['probability'] * 100:.1f}%・ずれ {pick['gap']:.1f}倍）")
        lines.append(NOTE)
        return lines
