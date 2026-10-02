"""予想の結果（辞書）を、標準出力に出す表にする。"""

from __future__ import annotations

from typing import Any

from 共通.render import Table

#: 表の見出し。
HEADERS: tuple[str, ...] = (
    "順位", "印", "馬番", "馬名", "3着以内の確率", "単勝", "人気", "市場の見立て", "複勝の期待値", "良い点", "悪い点",
)


class ForecastTable:
    """1レースの予想の結果を、全頭の表（3着以内の確率の高い順）にする。良い点・悪い点は分類の名前だけ並べる。"""

    def table(self, forecast: dict[str, Any]) -> Table:
        rows = [self._row(horse) for horse in forecast["horses"]]
        note = f"時点: {forecast['timing']}（{forecast['timing_reason']}）。予想: {forecast['model']}。"
        if forecast.get("pool_free"):
            note += " 券種のオッズが無いので、券種オッズなしのモデルで予想した。"
        return Table(title=forecast["title"], columns=list(HEADERS), rows=rows, note=note)

    def _row(self, horse: dict[str, Any]) -> list[Any]:
        return [
            horse["rank"], horse["mark"], horse["horse_no"], horse["horse_name"], _percent(horse["probability"]),
            horse["win_odds"], _whole(horse["popularity"]), _percent(horse["market_top3"]), _number(horse["place_value"]),
            "・".join(point["category"] for point in horse["good"]), "・".join(point["category"] for point in horse["bad"]),
        ]


def _percent(value: float | None) -> str:
    return "" if value is None else f"{value:.1%}"


def _number(value: float | None) -> str:
    return "" if value is None else f"{value:.2f}"


def _whole(value: float | None) -> str:
    return "" if value is None else f"{value:.0f}"
