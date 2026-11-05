"""1レースの推奨買目を決める流れ: 全頭の予想 → 票の表 → 1着・2着・3着の条件つきロジット → 券種ごとの組の確率 → 最新のオッズで期待値 → 買い方で選ぶ。"""

from __future__ import annotations

from collections.abc import Sequence

import duckdb
import pandas as pd

from .forecast_horses import ForecastHorses
from .position_coefficients import PositionCoefficients
from .position_model import EV, PROBABILITY, PositionModel
from .race_pools import RacePools
from .recommendation import Recommendation
from .recommendation_set import RecommendationSet
from .repository import AnnouncedTicketOddsRepository, LocalFrameRepository
from .ticket_plan import RECOMMENDED_PLANS, TicketPlan
from .ticket_probabilities import TICKET_KEYS, TicketProbabilities

_TRIFECTA = "3連単"


class Recommender:
    """``recommend(rid, forecast)`` は、地方の predict の JSON（モデルごとの 1着・3着以内の確率つき）から推奨買目を返す。
    頭数の線に届かない券種は出さず、その旨を理由に添える。オッズが欠けている・線に届く組が無い、なら点の無いまとまり（理由つき）。"""

    def __init__(self, con: duckdb.DuckDBPyConnection, coefficients: PositionCoefficients,
                 plans: Sequence[TicketPlan] = RECOMMENDED_PLANS, model: PositionModel | None = None) -> None:
        self._con = con
        self._coefficients = coefficients
        self._plans = tuple(plans)
        self._model = model or PositionModel()

    def recommend(self, rid: str, forecast: dict) -> RecommendationSet:
        horses = ForecastHorses().of(forecast, int(rid), f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}")
        heads = len(horses)
        plans = [plan for plan in self._plans if plan.applies(heads)]
        skipped = [plan.ticket for plan in self._plans if not plan.applies(heads)]
        note = f"{heads}頭なので {'・'.join(skipped)} は推奨買目の対象外" if skipped else ""
        if not plans:
            return RecommendationSet((), note)
        tables = RacePools(self._con).build(rid, horses)
        if tables.horses.empty:
            return RecommendationSet((), "オッズか予想の確率が欠けた馬がいるので推奨買目を出さない")
        combos = self._model.predict(tables, self._coefficients)
        probabilities = TicketProbabilities().of(combos, self._frames(rid))
        rows: list[Recommendation] = []
        for plan in plans:
            priced = self._priced(plan.ticket, probabilities[plan.ticket], combos, rid)
            rows += self._rows(plan, plan.choose(priced))
        if rows:
            return RecommendationSet(tuple(rows), note)
        return RecommendationSet((), "。".join(reason for reason in ("期待値が線に届く組が無い", note) if reason))

    def _frames(self, rid: str) -> pd.DataFrame:
        frames = LocalFrameRepository(self._con).read(rid)
        return pd.DataFrame({"race_id": int(rid), "horse_no": list(frames), "frame_no": list(frames.values())})

    def _priced(self, ticket: str, probabilities: pd.DataFrame, combos: pd.DataFrame, rid: str) -> pd.DataFrame:
        """組の確率に、その券種の最新のオッズを付ける（オッズの無い組は買えないので落とす）。"""
        if ticket == _TRIFECTA:
            return combos.rename(columns={"first": "a", "second": "b", "third": "c"})
        odds = AnnouncedTicketOddsRepository(self._con, ticket).load(rid)
        return probabilities.merge(odds, on=["race_id", *TICKET_KEYS[ticket]], how="inner")

    @staticmethod
    def _rows(plan: TicketPlan, chosen: pd.DataFrame) -> list[Recommendation]:
        keys = list(TICKET_KEYS[plan.ticket])
        ordered = chosen.sort_values(keys)
        return [Recommendation(plan.ticket, tuple(int(row[key]) for key in keys), float(row["odds"]), float(row[PROBABILITY]), float(row[EV]))
                for _, row in ordered.iterrows()]
