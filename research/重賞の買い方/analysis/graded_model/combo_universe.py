"""形の候補に出てくる全部の組の、確定オッズ・払戻・組の期待値の表を作る。"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import product

import duckdb
import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import ComboExpectedValue, HorseRatio
from yosou.shared.combo_value.horse_ratio import TOP3_RATIO

from 今週の予想.forecast_columns import MARKET_TOP3, MARKET_WIN, PLACE_VALUE, PROBABILITY, WIN_PROBABILITY, WIN_VALUE
from 印の成績.ticket_payouts import PAYOUT, TicketPayouts
from 今週の予想.mark_tickets import ODDS

from .graded_race_marker import FRAME_NO
from .race_horses import RaceHorses
from .ticket_shape import BRACKET, PLACE, WIN, TicketShape, combo_key

#: 表の列。
TICKET, COMBO, VALUE = "ticket", "combo", "value"
#: 枠連の払戻率（設計書「買うレースと買い目を決める」07 の 2 の馬連と同じ 77.5%）。
_BRACKET_RATE = 0.775
_COMBO_TYPES = {ticket_type.label: ticket_type for ticket_type in
                (TicketType.QUINELLA, TicketType.WIDE, TicketType.EXACTA, TicketType.TRIO, TicketType.TRIFECTA)}


class ComboUniverse:
    """重賞ごとに、形の候補（``shapes``）のどれかに出てくる組を全部集め、確定オッズ・100円あたりの払戻・組の期待値を付ける（1行 = 1つの組）。

    - 単勝・複勝: 印を付けた表の確定の単勝オッズ・最低の複勝オッズと払戻、単勝の期待値・複勝の期待値。
    - 馬連・ワイド・馬単・3連複・3連単: 元DB の確定オッズと払戻（``TicketPayouts``）。期待値は「市場が見た組の確率 × 各馬のモデル ÷ 市場の比」
      （``ComboExpectedValue``。設計書 16 の 6.1）。ワイドのオッズは最低オッズ。
    - 枠連: 元DB の確定オッズと払戻。期待値は、2つの枠の馬の組ごとの3着以内の比の積の平均 × 払戻率（目安。順位付けにだけ使う）。
    """

    def build(self, con: duckdb.DuckDBPyConnection, marked: pd.DataFrame, shapes: Sequence[TicketShape]) -> pd.DataFrame:
        singles, combos = [], []
        for race_id, race in marked.groupby("race_id", sort=False):
            horses = RaceHorses.of(race)
            ratios = self._ratios(race)
            race_date = race["race_date"].iloc[0]
            wanted: dict[str, set[tuple[int, ...]]] = {}
            for shape in shapes:
                wanted.setdefault(shape.ticket, set()).update(shape.combos(horses))
            for ticket, found in wanted.items():
                if ticket in (WIN, PLACE):
                    singles += self._singles(race_id, race_date, race, ticket, found)
                else:
                    combos += self._combos(race_id, race_date, ticket, found, ratios, race)
        table = pd.DataFrame(combos)
        priced = TicketPayouts(con).attach(table.rename(columns={TICKET: "ticket_type"})).rename(columns={"ticket_type": TICKET})
        return pd.concat([pd.DataFrame(singles), priced[["race_id", "race_date", TICKET, COMBO, ODDS, PAYOUT, VALUE]]], ignore_index=True)

    def _ratios(self, race: pd.DataFrame) -> pd.DataFrame:
        keyed = race.set_index("horse_no")
        return HorseRatio().of(keyed[PROBABILITY], keyed[MARKET_TOP3], keyed[WIN_PROBABILITY], keyed[MARKET_WIN])

    def _singles(self, race_id: str, race_date, race: pd.DataFrame, ticket: str, found) -> list[dict]:
        keyed = race.set_index("horse_no")
        rows = []
        for (horse,) in found:
            row = keyed.loc[horse]
            if ticket == WIN:
                odds, payout, value = row["win_odds"], row["win_payout"], row[WIN_VALUE]
            else:
                odds, payout, value = row["place_odds_low"], row["place_payout"], row[PLACE_VALUE]
            rows.append({"race_id": race_id, "race_date": race_date, TICKET: ticket, COMBO: combo_key(ticket, (horse,)),
                         ODDS: float(odds) if pd.notna(odds) else np.nan, PAYOUT: float(payout or 0.0),
                         VALUE: float(value) if pd.notna(value) else np.nan})
        return rows

    def _combos(self, race_id: str, race_date, ticket: str, found, ratios: pd.DataFrame, race: pd.DataFrame) -> list[dict]:
        ordered = sorted(found)
        if ticket == BRACKET:
            values = [self._bracket_value(combo, ratios, race) for combo in ordered]
        else:
            values = ComboExpectedValue().of(_COMBO_TYPES[ticket], ordered, ratios)
        return [{"race_id": race_id, "race_date": race_date, TICKET: ticket, COMBO: combo_key(ticket, combo), VALUE: float(value)}
                for combo, value in zip(ordered, values, strict=True)]

    def _bracket_value(self, frames: tuple[int, ...], ratios: pd.DataFrame, race: pd.DataFrame) -> float:
        by_frame = race.groupby(FRAME_NO)["horse_no"].apply(list).to_dict()
        first, second = by_frame.get(frames[0], []), by_frame.get(frames[1], [])
        pairs = [(a, b) for a, b in product(first, second) if a != b]
        if not pairs:
            return np.nan
        top3 = ratios[TOP3_RATIO]
        return float(_BRACKET_RATE * np.mean([top3.get(a, np.nan) * top3.get(b, np.nan) for a, b in pairs]))
