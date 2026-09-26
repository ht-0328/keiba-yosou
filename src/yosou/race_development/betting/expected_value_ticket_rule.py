"""期待値が線以上の買い目を作る。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.betting import TicketType

from .column_names import COMBO, EXPECTED_VALUE, ODDS, PROBABILITY, RACE_ID, RULE, STAKE, STAKE_YEN, TICKET_TYPE
from .ticket import TICKET_COLUMNS

#: 期待値の線の既定。
EXPECTED_VALUE_LINE = 1.0


class ExpectedValueTicketRule:
    """券種ごとに、当たる確率 × 確定オッズ が線（既定 1.0）以上の買い目を全部作る（設計書 16 の 8.）。1点 100円。

    複勝・ワイドは、確定オッズの表の ``odds``（最低オッズ）で計算する（``odds_high`` は使わない）。
    確定オッズの無い買い目（取消・除外の馬を含む組、無投票の組）は、突き合わせで落ちるので買わない。
    線以上の買い目が無いレースは、その券種を買わない（表に行が無い）。
    確定オッズで計算するので、実際より少し良く出るおそれがある（設計書 11 の決まり 13）。
    """

    def __init__(self, line: float = EXPECTED_VALUE_LINE, name: str | None = None, stake: int = STAKE_YEN) -> None:
        self._line = line
        self._name = name or f"期待値 {line:.1f} 以上（モデル）"
        self._stake = stake

    def tickets(self, probabilities: pd.DataFrame, odds: pd.DataFrame, ticket_type: TicketType) -> pd.DataFrame:
        """``probabilities`` は列 ``race_id``・``combo``・``probability``（``TicketProbability.of`` の戻り値に ``race_id`` を足したもの。
        何レースぶんでもよい）、``odds`` はその券種の確定オッズ（``FinalOddsRepository.read`` の戻り値。列 ``race_id``・``combo``・``odds``）。

        戻り値は買い目の表（列 ``race_id``・``ticket_type``・``combo``・``stake``・``rule``）に、``probability``・``odds``・
        ``expected_value`` を足したもの。
        """
        priced = probabilities[[RACE_ID, COMBO, PROBABILITY]].merge(odds[[RACE_ID, COMBO, ODDS]], on=[RACE_ID, COMBO], how="inner")
        priced[EXPECTED_VALUE] = priced[PROBABILITY] * priced[ODDS]
        chosen = priced[priced[EXPECTED_VALUE] >= self._line].reset_index(drop=True)
        chosen = chosen.assign(**{TICKET_TYPE: ticket_type.key, STAKE: self._stake, RULE: self._name})
        return chosen[[*TICKET_COLUMNS, PROBABILITY, ODDS, EXPECTED_VALUE]]
