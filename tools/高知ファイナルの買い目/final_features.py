"""高知の出走の表から、予想の材料（特徴量）の表を作る。学ぶときも予想するときも同じ作り。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from .day_trend import DayTrend
from .horse_form import HorseForm
from .jockey_form import JockeyForm
from .pair_form import PairForm
from .race_relative import RaceRelative
from .run_base import RunBase
from .speed_form import SpeedForm
from .trainer_form import TrainerForm

#: 材料に使う走の条件（単勝オッズがあり、この頭数以上）。
MIN_RUNNERS = 5
#: 1レースだけ予想するときに残す、過去の日数（騎手・調教師の直近365日の成績に足りる長さ）。
RECENT_DAYS = 366


class FinalFeatures:
    """``runs`` は ``KochiRunRepository.read`` の表（高知の全部の出走。これから走るレースの行は ``win_odds`` に発走前の断面を入れておく）。
    手順: 1走ごとの列 → 速さの指数（全部の走で真ん中を取る）→ 馬の近走・騎手（出走した全部の走）→ 材料に使う走に絞る →
    その日の傾向・レースの中の比べ・速さの近走・調教師・馬と騎手の組 → オッズの材料。
    ``focus`` に rid を渡すと、そのレースの行だけを返す。速くするために、そのレースの馬の全部の走と直近 ``RECENT_DAYS`` 日の走だけで作る
    （そのレースの行の値は、全部の走で作ったときと同じになる）。"""

    def __init__(self) -> None:
        self._base = RunBase()
        self._horse = HorseForm()
        self._jockey = JockeyForm()
        self._day = DayTrend()
        self._relative = RaceRelative()
        self._speed = SpeedForm()
        self._trainer = TrainerForm()
        self._pair = PairForm()

    def popularity_rates(self, runs: pd.DataFrame) -> dict[float, float]:
        """騎手の材料に使う、単勝人気ごとの 3着以内率（学ぶときに数えて、モデルと一緒に保存する）。"""
        return self._jockey.rates(self._base.build(runs))

    def build(self, runs: pd.DataFrame, popularity_rates: Mapping[float, float], focus: str | None = None) -> pd.DataFrame:
        d = self._base.build(runs)
        eligible = d["win_odds"].notna() & (d["win_odds"] > 0) & (d["field_size"] >= MIN_RUNNERS)
        d = self._speed.mark(d, eligible)
        d["eligible"] = eligible
        if focus is not None:
            d = self._near(d, focus)
        d = self._jockey.build(self._horse.build(d), popularity_rates)
        d = self._horse.derived(d[d["eligible"]])
        d = self._relative.ranks(self._day.build(d))
        d = self._pair.build(self._trainer.build(self._speed.build(d)))
        d = self._relative.market(d)
        return d if focus is None else d[d["race_id"] == focus].reset_index(drop=True)

    @staticmethod
    def _near(d: pd.DataFrame, focus: str) -> pd.DataFrame:
        """``focus`` のレースの馬の全部の走と、そのレースの日までの直近の走。"""
        race = d[d["race_id"] == focus]
        if race.empty:
            raise LookupError(f"レースの出走馬がありません（{focus}）")
        day = race["race_date"].iloc[0]
        recent = (d["race_date"] >= day - pd.Timedelta(days=RECENT_DAYS)) & (d["race_date"] <= day)
        own = d["horse_id"].isin(race["horse_id"]) & (d["race_date"] <= day)
        return d[recent | own].reset_index(drop=True)
