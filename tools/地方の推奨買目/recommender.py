"""1レースの推奨買目を決める流れ: 全頭の予想 → 票の表 → 1着・2着・3着の条件つきロジット → 券種ごとの組の確率 → 最新のオッズで期待値 → 買い方で選ぶ。
荒れ具合の条件のある券種（3連複）は、先に地方の荒れ具合の予想（中荒れ以上の確率）を見て、線に届かないレースでは買わない。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

import duckdb
import pandas as pd

from .combo_forms import ComboForms
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


class UpsetSource(Protocol):
    """券種ごとの中荒れ以上の確率を出す部品（本番は ``UpsetProbabilities``）。"""

    def of(self, con: duckdb.DuckDBPyConnection, rid: str, tickets: Sequence[str]) -> dict[str, float]: ...


class Recommender:
    """``recommend(rid, forecast)`` は、地方の predict の JSON（モデルごとの 1着・3着以内の確率つき）から推奨買目を返す。
    頭数の線に届かない券種・荒れ具合の線に届かない券種は出さず、その旨を理由に添える。荒れ具合の予想が出せない（モデルが無い・馬体重がまだ無い）ときも、
    その券種だけを対象外にして理由に添える。オッズが欠けている・線に届く組が無い、なら点の無いまとまり（理由つき）。"""

    def __init__(self, con: duckdb.DuckDBPyConnection, coefficients: PositionCoefficients,
                 plans: Sequence[TicketPlan] = RECOMMENDED_PLANS, model: PositionModel | None = None,
                 upsets: UpsetSource | None = None) -> None:
        self._con = con
        self._coefficients = coefficients
        self._plans = tuple(plans)
        self._model = model or PositionModel()
        self._upsets = upsets

    def recommend(self, rid: str, forecast: dict) -> RecommendationSet:
        horses = ForecastHorses().of(forecast, int(rid), f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}")
        notes: list[str] = []
        plans = self._by_upset(rid, self._by_heads(len(horses), notes), notes)
        if not plans:
            return RecommendationSet((), self._joined(notes))
        tables = RacePools(self._con).build(rid, horses)
        if tables.horses.empty:
            return RecommendationSet((), "オッズか予想の確率が欠けた馬がいるので推奨買目を出さない")
        combos = self._model.predict(tables, self._coefficients)
        probabilities = TicketProbabilities().of(combos, self._frames(rid))
        forms = ComboForms(horses)
        rows: list[Recommendation] = []
        for plan in plans:
            priced = self._priced(plan.ticket, probabilities[plan.ticket], combos, rid)
            if plan.form:
                priced = forms.attach(priced, TICKET_KEYS[plan.ticket])
            rows += self._rows(plan, plan.choose(priced))
        if rows:
            return RecommendationSet(tuple(rows), self._joined(notes))
        return RecommendationSet((), self._joined(["期待値が線に届く組が無い", *notes]))

    def _by_heads(self, heads: int, notes: list[str]) -> list[TicketPlan]:
        """頭数の線に届かない買い方を外し、理由を添える。"""
        skipped = [plan.ticket for plan in self._plans if not plan.applies(heads)]
        if skipped:
            notes.append(f"{heads}頭なので {'・'.join(skipped)} は推奨買目の対象外")
        return [plan for plan in self._plans if plan.applies(heads)]

    def _by_upset(self, rid: str, plans: list[TicketPlan], notes: list[str]) -> list[TicketPlan]:
        """荒れ具合の条件のある買い方を、そのレースの中荒れ以上の確率で残すか決める。予想が出せなければ、その買い方は対象外にして理由を添える。"""
        needed = [plan.ticket for plan in plans if plan.upset_min > 0]
        if not needed:
            return plans
        upsets = self._upset_probabilities(rid, needed, notes)
        kept: list[TicketPlan] = []
        for plan in plans:
            if plan.allows_upset(upsets.get(plan.ticket)):
                kept.append(plan)
            elif plan.ticket in upsets:
                notes.append(f"{plan.ticket}は中荒れ以上の確率 {upsets[plan.ticket]:.2f} が {plan.upset_min:g} 未満なので買わない")
        return kept

    def _upset_probabilities(self, rid: str, tickets: list[str], notes: list[str]) -> dict[str, float]:
        if self._upsets is None:
            notes.append(f"荒れ具合の予想が無いので {'・'.join(tickets)} は推奨買目の対象外")
            return {}
        try:
            return self._upsets.of(self._con, rid, tickets)
        except (FileNotFoundError, LookupError, ValueError) as error:
            notes.append(f"荒れ具合の予想が出せないので {'・'.join(tickets)} は推奨買目の対象外（{str(error).split('。')[0]}）")
            return {}

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

    @staticmethod
    def _joined(notes: list[str]) -> str:
        return "。".join(note for note in notes if note)
