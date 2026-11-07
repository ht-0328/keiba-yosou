"""1日の流れ（DayNotifier）に差し込む部品の組。中央（jvdata-store と今週の予想）か、地方（nvdata-store と地方の予想モデル）。"""

from __future__ import annotations

from dataclasses import dataclass

from 共通 import db

from 今週の予想.forecast_store import ForecastStore

from 発走前の通知.day_notifier import Fetcher, Message, Runner, SavedAt, Schedule
from 発走前の通知.forecast_runner import ForecastRunner
from 発走前の通知.local_forecast_runner import LocalForecastRunner
from 発走前の通知.local_forecast_store import LocalForecastStore
from 発走前の通知.local_race_message import LocalRaceMessage
from 発走前の通知.local_recommendations import LocalRecommendations
from 発走前の通知.local_race_schedule import LocalRaceSchedule
from 発走前の通知.race_message import RaceMessage
from 発走前の通知.race_schedule import RaceSchedule
from 発走前の通知.saved_upset_probabilities import SavedUpsetProbabilities
from 発走前の通知.store_fetcher import StoreFetcher
from 発走前の通知.track_tendencies import TrackTendencies


@dataclass(frozen=True)
class NotifierParts:
    schedule: Schedule
    fetcher: Fetcher
    runner: Runner
    message: Message
    store: SavedAt

    @classmethod
    def jra(cls) -> NotifierParts:
        """中央: 今週の出馬表のレース一覧、jvstore、forecast.py、馬場の傾向と印と実際に買う買い目の文と表の画像（と全頭の予想根拠）、
        今週の予想の保存。"""
        store = ForecastStore()
        schedule = RaceSchedule()
        message = RaceMessage(store, schedule=schedule, tendencies=TrackTendencies(default=db.JRA))
        return cls(schedule=schedule, fetcher=StoreFetcher(), runner=ForecastRunner(), message=message, store=store)

    @classmethod
    def local(cls) -> NotifierParts:
        """地方: 地方の元DB のレース一覧、nvstore、地方の予想（predict と荒れ具合）、馬場の傾向と印と推奨買目の文と表の画像、予想の JSON の保存。
        推奨買目の係数（reports/地方の推奨買目/係数.json）が無ければここで止まる。"""
        store = LocalForecastStore()
        schedule = LocalRaceSchedule()
        recommendations = LocalRecommendations(upsets=SavedUpsetProbabilities(store))
        return cls(schedule=schedule, fetcher=StoreFetcher.local(), runner=LocalForecastRunner(store=store),
                   message=LocalRaceMessage(store, schedule, recommendations=recommendations,
                                            tendencies=TrackTendencies(default=db.LOCAL)), store=store)
