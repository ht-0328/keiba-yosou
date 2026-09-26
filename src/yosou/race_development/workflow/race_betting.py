"""1レースの着順の確率から、印と買い目を作る。"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from yosou.shared.betting import TicketType

from ..betting import (
    POPULARITY_MARK_RULE,
    ExpectedValueTicketRule,
    MarkAssigner,
    MarkTicketRule,
    PopularityMarkAssigner,
    TicketProbability,
)
from ..betting import column_names as bet
from ..ml_model import OrderProbability


class RaceBetting:
    """1レースの各馬の1着の確率から、3連単の確率の表を作り、印（モデルと人気順）と、3つの買い方の買い目を作る（設計書 16 の 8.）。

    買い方は「印どおり（モデル）」「期待値 1.0 以上（モデル）」「印どおり（人気順）」。取消・除外の馬は、渡される表に
    入っていない（出走した馬だけ）ので、買い目にも入らない。
    """

    def __init__(self) -> None:
        self._order = OrderProbability()
        self._ticket_probability = TicketProbability()
        self._marks = MarkAssigner()
        self._popularity_marks = PopularityMarkAssigner()
        self._model_rule = MarkTicketRule()
        self._popularity_rule = MarkTicketRule(POPULARITY_MARK_RULE)
        self._value_rule = ExpectedValueTicketRule()

    def tickets(self, race_id: str, race: pd.DataFrame, order_lambda: float,
                odds: Mapping[TicketType, pd.DataFrame]) -> pd.DataFrame:
        """``race`` は1行 = 1頭（列 ``horse_no``・``win_probability``・``win_odds``・``leader_probability``）。
        ``odds`` は券種 → そのレースの確定オッズ（列 ``race_id``・``combo``・``odds``）。戻り値は3つの買い方の買い目の表。
        """
        trifecta = self._trifecta(race, order_lambda)
        marked = self._marks.assign(race)
        by_popularity = self._popularity_marks.assign(race)
        parts = [self._tickets_of(race_id, len(race), trifecta, marked, by_popularity, ticket_type, odds.get(ticket_type))
                 for ticket_type in TicketType]
        return pd.concat(parts, ignore_index=True)

    def marks(self, race: pd.DataFrame) -> pd.DataFrame:
        """印を付けた表（``MarkAssigner.assign`` の戻り値）。"""
        return self._marks.assign(race)

    def _trifecta(self, race: pd.DataFrame, order_lambda: float) -> pd.DataFrame:
        """3連単の全部の並びと確率（列 ``first``・``second``・``third`` は馬番）。"""
        horse_no = race[bet.HORSE_NO].to_numpy()
        orders, probability = self._order.trifecta(race[bet.WIN_PROBABILITY].to_numpy(), order_lambda)
        return pd.DataFrame({
            bet.FIRST: horse_no[orders[:, 0]], bet.SECOND: horse_no[orders[:, 1]], bet.THIRD: horse_no[orders[:, 2]],
            bet.PROBABILITY: probability,
        })

    def _tickets_of(self, race_id: str, field_size: int, trifecta: pd.DataFrame, marked: pd.DataFrame,
                    by_popularity: pd.DataFrame, ticket_type: TicketType, odds: pd.DataFrame | None) -> pd.DataFrame:
        """1つの券種の、3つの買い方の買い目。"""
        parts = [
            self._model_rule.tickets(race_id, marked, ticket_type),
            self._popularity_rule.tickets(race_id, by_popularity, ticket_type),
        ]
        if odds is not None and not trifecta.empty:
            probabilities = self._ticket_probability.of(trifecta, ticket_type, field_size).assign(**{bet.RACE_ID: race_id})
            parts.append(self._value_rule.tickets(probabilities, odds, ticket_type))
        return pd.concat(parts, ignore_index=True)
