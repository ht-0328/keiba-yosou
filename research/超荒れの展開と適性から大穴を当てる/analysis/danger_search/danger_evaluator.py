"""消の判定1つを受け取り、全券種の買い目を組んで成績を返す。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 今週の予想.torigami_filter import DROPPED, TorigamiFilter

from .combo_candidates import ComboCandidates
from .odds_cache import OddsCache
from .payout_table import PayoutTable
from .race_variant_cache import TICKET_COLUMNS, RaceVariantCache
from .search_inputs import SearchInputs
from .ticket_metrics import TicketMetrics

#: 消の馬の成績の列。
DANGER_SUMMARY_COLUMNS: tuple[str, ...] = ("区分", "消の頭数", "消の馬の4着以下", "同じ人気の馬全体の4着以下")
_FIRST = "1番人気"


@dataclass(frozen=True)
class Evaluation:
    """1つの消の決め方の結果。``metrics`` は ``TicketMetrics.of``、``dangers`` は消の馬の成績（``DANGER_SUMMARY_COLUMNS``。全部・1番人気・2〜5番人気）。"""

    metrics: pd.DataFrame
    dangers: pd.DataFrame
    computed_races: int

    def value(self, group: str, span: str, column: str) -> float:
        rows = self.metrics[(self.metrics["group"] == group) & (self.metrics["span"] == span)]
        return float(rows[column].iloc[0]) if len(rows) else float("nan")


class DangerEvaluator:
    """消の判定（列 race_id・horse_id・favorite_band・is_danger …）から、道具「印の成績」と同じ全券種の買い目を組み（印の買い目は
    ``RaceVariantCache``、組の期待値と枠連は ``ComboCandidates``）、払戻・オッズ・トリガミを付けて成績（``TicketMetrics``）を数える。
    消の馬の成績（頭数・4着以下の割合・同じ人気の馬全体の4着以下）も出す。"""

    def __init__(self, inputs: SearchInputs, cache: RaceVariantCache, combos: ComboCandidates, payouts: PayoutTable, odds: OddsCache) -> None:
        self._inputs = inputs
        self._cache = cache
        self._combos = combos
        self._payouts = payouts
        self._odds = odds
        self._filter = TorigamiFilter()
        self._metrics = TicketMetrics()
        self._lost_by_popularity = self._lost_rates()

    def evaluate(self, dangers: pd.DataFrame) -> Evaluation:
        computed = self._cache.ensure(dangers)
        marked, tickets = self._cache.assemble(dangers)
        extra = self._combos.tickets(marked)
        if not extra.empty:
            extra = self._filter.apply(self._odds.attach(self._payouts.attach(extra)))
            extra = extra[extra[DROPPED] == ""][list(TICKET_COLUMNS)]
            tickets = pd.concat([tickets, extra], ignore_index=True)
        return Evaluation(self._metrics.of(tickets), self._danger_summary(dangers), computed)

    def _lost_rates(self) -> pd.Series:
        """印を付けるレースの全頭の、人気ごとの4着以下の割合（同じ人気の馬全体の基準）。"""
        places = self._inputs.places
        rows = places[places["race_id"].isin(set(self._inputs.race_ids))]
        lost = ~(rows["finish"] <= 3)
        return lost.groupby(rows["popularity"]).mean()

    def _danger_summary(self, dangers: pd.DataFrame) -> pd.DataFrame:
        flagged = dangers[dangers["is_danger"].astype(bool)].merge(
            self._inputs.places[["race_id", "horse_id", "finish", "popularity"]], on=["race_id", "horse_id"], how="inner")
        flagged = flagged[flagged["race_id"].isin(set(self._inputs.race_ids))]
        rows = []
        for label, part in (("全部", flagged), (_FIRST, flagged[flagged["favorite_band"] == _FIRST]),
                            ("2〜5番人気", flagged[flagged["favorite_band"] != _FIRST])):
            if part.empty:
                rows.append([label, 0, float("nan"), float("nan")])
                continue
            lost = float((~(part["finish"] <= 3)).mean())
            weights = part["popularity"].value_counts(normalize=True)
            baseline = float(sum(self._lost_by_popularity.get(popularity, float("nan")) * weight for popularity, weight in weights.items()))
            rows.append([label, int(len(part)), lost, baseline])
        return pd.DataFrame(rows, columns=list(DANGER_SUMMARY_COLUMNS))
