"""組の期待値で組を選ぶ券種のルール（研究「複勝以外の回収率100超」の docs/04）。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.betting import TicketType

#: 対象のレース。全レースか、当日の期待度「高」のレースだけか。
ALL_RACES, HIGH_RACES = "全レース", "期待度「高」"


@dataclass(frozen=True)
class ComboValueRule:
    """その券種の全部の組から、組の期待値（``ComboBlend``。市場とモデルを重みで合わせた組の確率 × 確定オッズ）が ``value_line`` 以上で、
    オッズが ``odds_cap`` 倍以下の組を全部買うルール。``scope`` は対象のレース（``ALL_RACES``・``HIGH_RACES``）。

    ``adopted`` は、まだ見ていない年で採用の基準を満たして実際に買うか（偽は比べるための行で、道具「印の成績」にだけ出す）。
    ``stake_units`` は 08 の 2 の単位（合計には入らないので、表の列を埋めるためだけ）。
    例: 馬連・全レース・線 1.1・上限 100倍なら、組の期待値が 1.1 以上で 100倍以下の馬連を、そのレースで全部買う。
    """

    ticket_type: TicketType
    scope: str
    value_line: float
    odds_cap: float
    adopted: bool
    stake_units: float = 0.5

    @property
    def label(self) -> str:
        """表に出す買い方の名前。例: ``馬連（組の期待値）``。"""
        return f"{self.ticket_type.label}（組の期待値）"

    @property
    def condition(self) -> str:
        """人が読む決まり。例: ``全レース・期待値 1.1 以上・100倍以下``。"""
        return f"{self.scope}・期待値 {self.value_line:.1f} 以上・{self.odds_cap:,.0f}倍以下"
