"""1レースの、材料の有無と予想の判定の組。"""

from __future__ import annotations

from dataclasses import dataclass

from 共通.race_signals import RaceSignals
from 取得と予想の状況.forecast_verdict import ForecastVerdict


@dataclass(frozen=True)
class RaceStatus:
    """1レースぶん。``signals`` は DB に何が入っているか、``verdict`` は予想がそれに追いついているか。"""

    signals: RaceSignals
    verdict: ForecastVerdict
