"""予想「高配当の組が当たるかを予想」の、確率を出す部品の偽物（テスト用。値は架空）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.betting import TicketType

#: 予想の結果（組の表）の列。
COMBO_COLUMNS = ["ticket_type", "combo", "horses", "odds", "probability", "value"]


class FakeHighPayoutPredictor:
    """実物（``HighPayoutPredictor``）と同じ呼び方の偽物。板にある組の全部に、組番ごとに決めた確率（無い組は 0）を付けて返す。
    3連単の板が無ければ、どの券種も返さない（板が足りないときの実物の動き）。受け取った馬ごとの表は ``horses`` に残す。"""

    def __init__(self, probabilities: dict[str, float]) -> None:
        self._probabilities = probabilities
        self.horses: pd.DataFrame | None = None

    def predict(self, horses: pd.DataFrame, boards: dict[TicketType, pd.DataFrame]) -> pd.DataFrame:
        self.horses = horses
        trifecta = boards.get(TicketType.TRIFECTA)
        if trifecta is None or trifecta.empty:
            return pd.DataFrame(columns=COMBO_COLUMNS)
        parts = [self._of_board(ticket_type, board) for ticket_type, board in boards.items()]
        return pd.concat(parts, ignore_index=True)

    def _of_board(self, ticket_type: TicketType, board: pd.DataFrame) -> pd.DataFrame:
        """1つの券種の板の全部の組（列 ``COMBO_COLUMNS``。``horses`` は馬番の並びのタプル。実物と同じ）。"""
        combo, odds = board["combo"].astype(str), board["odds"].astype(float)
        probability = combo.map(self._probabilities).fillna(0.0).astype(float)
        return pd.DataFrame({"ticket_type": ticket_type.label, "combo": combo, "horses": combo.map(_horses), "odds": odds,
                             "probability": probability, "value": probability * odds})[COMBO_COLUMNS]


def _horses(combo: str) -> tuple[int, ...]:
    """組番（馬番を2桁ずつ）→ 馬番の並び。例: ``0308`` → ``(3, 8)``。"""
    return tuple(int(combo[at:at + 2]) for at in range(0, len(combo), 2))
