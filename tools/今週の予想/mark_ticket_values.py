"""全レースで出す印の買い目に、1点ごとの期待値を付ける。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.betting import TicketType
from yosou.shared.combo_value import ComboBlendWeights
from yosou.shared.combo_value.combo_blend import VALUE as BLEND_VALUE

from 今週の予想.combo_value_picker import ComboValuePicker
from 今週の予想.forecast_columns import HORSE_NO, WIN_VALUE
from 今週の予想.mark_tickets import RULE, VALUE
from 今週の予想.ticket_rules import MARK_VALUE_LABELS, MARK_VALUE_RULES

#: 単勝の買い方の名前（期待値は馬ごとの単勝の期待値）。
_WIN = TicketType.WIN.label


class MarkTicketValues:
    """買い目（1行 = 1点。列は ``MarkTickets`` の ``COLUMNS``）のうち、全部のレースで出す印の買い目（``MARK_VALUE_LABELS``）の期待値の列を埋める。

    馬連・馬単・3連単は、組の期待値の買い目と同じ出し方（3連単の板から市場とモデルの Harville を作り、その券種の板と馬ごとの比と合わせて
    重みで1つにした組の確率 × オッズ。``ComboValuePicker.candidates``）。単勝は、その馬の単勝の期待値（1着の確率 × 単勝オッズ）。
    板か重みの無い券種の組は欠損値のまま。今週の予想（締め切り前のオッズの板）と道具「印の成績」（確定オッズの板）が同じ部品で付ける。
    """

    def __init__(self, weights: dict[TicketType, ComboBlendWeights]) -> None:
        self._picker = ComboValuePicker(MARK_VALUE_RULES, weights)

    def needed(self) -> tuple[TicketType, ...]:
        """読むオッズの板の券種（重みのある券種と3連単）。"""
        return self._picker.needed()

    def attach(self, tickets: pd.DataFrame, marked: pd.DataFrame, boards: dict[TicketType, pd.DataFrame]) -> pd.DataFrame:
        """``marked`` は印を付けた表（1行 = 1頭。``race_id``・馬番・確率・市場の見立て・単勝の期待値）、``boards`` は券種 → 板
        （列 ``race_id``・``combo``・``odds``）。印の買い目の行の期待値を埋めた ``tickets`` を返す（ほかの行はそのまま）。"""
        mine = tickets[RULE].isin(MARK_VALUE_LABELS)
        if not mine.any():
            return tickets
        lookup = {**self._win_values(marked), **self._combo_values(marked, boards)}
        keys = list(zip(tickets.loc[mine, "race_id"].astype(str), tickets.loc[mine, "ticket_type"], tickets.loc[mine, "combo"].astype(str)))
        out = tickets.copy()
        out[VALUE] = pd.to_numeric(out[VALUE], errors="coerce").astype(float)
        out.loc[mine, VALUE] = pd.Series([lookup.get(key) for key in keys], index=out.index[mine], dtype=float)
        return out

    @staticmethod
    def _win_values(marked: pd.DataFrame) -> dict[tuple[str, str, str], float]:
        if WIN_VALUE not in marked.columns:
            return {}
        rows = marked.dropna(subset=[HORSE_NO, WIN_VALUE])
        return {(str(race), _WIN, f"{int(no):02d}"): float(value)
                for race, no, value in zip(rows["race_id"], rows[HORSE_NO], rows[WIN_VALUE], strict=True)}

    def _combo_values(self, marked: pd.DataFrame, boards: dict[TicketType, pd.DataFrame]) -> dict[tuple[str, str, str], float]:
        lookup: dict[tuple[str, str, str], float] = {}
        for rule, valued in zip(self._picker.rules, self._picker.candidates(marked, boards), strict=False):
            if valued.empty:
                continue
            label = rule.ticket_type.label
            lookup.update({(str(race), label, str(combo)): float(value)
                           for race, combo, value in zip(valued["race_id"], valued["combo"], valued[BLEND_VALUE], strict=True)})
        return lookup
