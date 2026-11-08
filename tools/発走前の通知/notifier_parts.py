"""1日の流れ（DayNotifier）に差し込む部品の組。中央（jvdata-store と今週の予想）か、地方（nvdata-store と地方の予想モデル）。"""

from __future__ import annotations

from dataclasses import dataclass

from 共通 import db

from yosou.review import ReviewStore

from 今週の予想.forecast_store import ForecastStore
from 今週の予想.wallet import Wallet
from 今週の予想.win5_planner import Win5Planner
from 今週の予想.win5_record_store import Win5RecordStore

from 発走前の通知.background_program import BackgroundProgram
from 発走前の通知.database_snapshot import DatabaseSnapshot
from 発走前の通知.day_notifier_protocols import Fetcher, Message, Runner, SavedAt, Schedule, Win5
from 発走前の通知.figure_cache_copy import FigureCacheCopy
from 発走前の通知.folders import WIN5_LOG_NAME, WIN5_PROGRAM
from 発走前の通知.forecast_runner import ForecastRunner
from 発走前の通知.local_forecast_runner import LocalForecastRunner
from 発走前の通知.local_forecast_store import LocalForecastStore
from 発走前の通知.local_race_message import LocalRaceMessage
from 発走前の通知.local_recommendations import LocalRecommendations
from 発走前の通知.local_race_schedule import LocalRaceSchedule
from 発走前の通知.race_message import RaceMessage
from 発走前の通知.race_schedule import RaceSchedule
from 発走前の通知.race_styles import RaceStyles
from 発走前の通知.saved_upset_probabilities import SavedUpsetProbabilities
from 発走前の通知.store_fetcher import StoreFetcher
from 発走前の通知.track_tendencies import TrackTendencies
from 発走前の通知.win5_job import Win5Job
from 発走前の通知.win5_message import Win5Message
from 発走前の通知.win5_schedule import Win5Schedule


@dataclass(frozen=True)
class NotifierParts:
    schedule: Schedule
    fetcher: Fetcher
    runner: Runner
    message: Message
    store: SavedAt
    #: WIN5 の段（中央だけ。地方は None）。
    win5: Win5 | None = None

    @classmethod
    def jra(cls) -> NotifierParts:
        """中央: 今週の出馬表のレース一覧、jvstore、forecast.py、馬場の傾向と印と実際に買う買い目の文と表の画像（と全頭の予想根拠）、
        今週の予想の保存。WIN5 の段（``Win5Job``。元DB の写しで WIN5 の予想を裏で動かす）も付ける。"""
        store = ForecastStore()
        schedule = RaceSchedule()
        message = RaceMessage(store, schedule=schedule, tendencies=TrackTendencies(default=db.JRA), styles=RaceStyles())
        fetcher = StoreFetcher()
        return cls(schedule=schedule, fetcher=fetcher, runner=ForecastRunner(), message=message, store=store,
                   win5=cls.win5_job(store, fetcher))

    @staticmethod
    def win5_job(store: ForecastStore, fetcher: StoreFetcher) -> Win5Job:
        """中央の WIN5 の段: 元DB の WIN5 と発走時刻、jvstore（0B51 と対象レースのオッズ）、元DB の写し、裏で動かす WIN5 の予想
        （予想のパッケージの predict）、WIN5 の文（財布の判断は買う計画と同じ ``Win5Planner``）。"""
        records = Win5RecordStore.beside(store)
        return Win5Job(schedule=Win5Schedule(), fetcher=fetcher, snapshot=DatabaseSnapshot(), figures=FigureCacheCopy(),
                       predictor=BackgroundProgram(program=WIN5_PROGRAM, log_name=WIN5_LOG_NAME),
                       message=Win5Message(records, Win5Planner(Wallet(ReviewStore()))), records=records)

    @classmethod
    def local(cls) -> NotifierParts:
        """地方: 地方の元DB のレース一覧、nvstore、地方の予想（predict と荒れ具合）、馬場の傾向と印と推奨買目の文と表の画像、予想の JSON の保存。
        推奨買目の係数（reports/地方の推奨買目/係数.json）が無ければここで止まる。"""
        store = LocalForecastStore()
        schedule = LocalRaceSchedule()
        recommendations = LocalRecommendations(upsets=SavedUpsetProbabilities(store))
        return cls(schedule=schedule, fetcher=StoreFetcher.local(), runner=LocalForecastRunner(store=store),
                   message=LocalRaceMessage(store, schedule, recommendations=recommendations,
                                            tendencies=TrackTendencies(default=db.LOCAL), styles=RaceStyles.local()), store=store)
