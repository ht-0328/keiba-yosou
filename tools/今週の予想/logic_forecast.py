"""AI＋ロジック予想: AI だけの予想（全レースの印の買い目）を、AI が材料にしていないロジックで直した判断の1行。"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from 今週の予想.logic_skip import LogicSkip
from 今週の予想.mark_return import MarkReturn
from 今週の予想.open_class_logic import OpenClassLogic
from 今週の予想.slow_pace_logic import SlowPaceLogic

#: 文と画像の見出し。
LABEL = "AI＋ロジック予想"


class LogicForecast:
    """印は AI だけの予想と同じで、全レースの印の買い目を買うかだけをロジックで直す（研究「AIとロジックの予想」）。

    ロジックは2つ。展開（``SlowPaceLogic``）と、クラス（``OpenClassLogic``）。どちらかに当たれば見送る（両方に当たれば展開の理由を出す）。

    - AI が買うレースでロジックに当たれば「見送り」と理由、当たらなければ「AI と同じく買う」。
    - AI が見送るレースは「見送り（AI と同じ）」。当日の予想でなく印の買い目が無ければ None（行を出さない）。
    """

    def __init__(self, pace: SlowPaceLogic | None = None, open_class: OpenClassLogic | None = None) -> None:
        self._pace = pace or SlowPaceLogic()
        self._open_class = open_class or OpenClassLogic()

    def line(self, forecast: dict[str, Any], styles: Mapping[int, str]) -> str | None:
        found = MarkReturn.of(forecast)
        if found is None or found.multiple is None:
            return None
        if not found.buys:
            return "見送り（AI と同じ）"
        skip = self._skip(forecast, styles)
        if skip is not None:
            return f"印の買い目は見送り（{skip.reason}）"
        return "印の買い目を AI と同じく買う（ロジックに当たらない）"

    def skip(self, forecast: dict[str, Any], styles: Mapping[int, str]) -> LogicSkip | None:
        """AI が買うレースをロジックで見送るなら、その理由。AI が見送るレース・印の買い目が無いレース・ロジックに当たらないレースは None。"""
        found = MarkReturn.of(forecast)
        if found is None or found.multiple is None or not found.buys:
            return None
        return self._skip(forecast, styles)

    def _skip(self, forecast: dict[str, Any], styles: Mapping[int, str]) -> LogicSkip | None:
        horses = forecast.get("horses") or []
        top = next((int(horse["horse_no"]) for horse in horses if horse.get("mark") == "◎" and horse.get("horse_no") is not None), None)
        if self._pace.skips(styles, len(horses), top):
            return LogicSkip("展開", self._pace.reason(styles, len(horses), top))
        class_name = str((forecast.get("header") or {}).get("クラス", ""))
        if self._open_class.skips(class_name):
            return LogicSkip("クラス", self._open_class.reason(class_name))
        return None
