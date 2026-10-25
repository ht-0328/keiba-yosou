"""組の期待値で組を選ぶ券種のルール（研究「複勝以外の回収率100超」の docs/04・05）。"""

from __future__ import annotations

from dataclasses import dataclass

from yosou.shared.betting import BracketTicket, TicketType
from yosou.shared.win_value import HIGH

from 今週の予想.race_condition import RaceCondition

#: 対象。全レース、◎の期待値 1.00 以上（◎ の単勝の期待値が線以上。``yosou.shared.win_value`` の ``HIGH``）のレースだけ、
#: ◎ を含む組だけ（着順を区別する券種は ◎ が1着の組だけ）、◎の期待値 1.00 以上のレースの ◎ を含む組だけ。
ALL_RACES, TOP_COMBOS = "全レース", "◎ を含む組"
HIGH_RACES, HIGH_TOP_COMBOS = f"◎の期待値 {HIGH}のレース", f"◎の期待値 {HIGH}のレースの ◎ を含む組"


@dataclass(frozen=True)
class ComboValueRule:
    """その券種の全部の組から、組の期待値（``ComboBlend``。市場とモデルを重みで合わせた組の確率 × 確定オッズ）が ``value_line`` 以上で、
    オッズが ``odds_cap`` 倍以下の組を買うルール。``scope`` は対象（``ALL_RACES``・``HIGH_RACES``・``TOP_COMBOS``）。
    ``max_points`` があれば、1レースで組の期待値の高い順にその点数までにする（無ければ条件に合う組を全部）。

    ``adopted`` は、まだ見ていない年で採用の基準を満たして実際に買うか（偽は比べるための行で、道具「印の成績」にだけ出す）。
    ``rolling`` は、組の確率の重みを直前1年で推定し直す券種か（研究 docs/05。真なら、道具「印の成績」で区切りごとの重みを渡したとき、それを使う。
    偽の券種は、どの区切りでも combo_blend.json の重みのまま）。
    ``stake_units`` は 08 の 2 の単位（合計には入らないので、表の列を埋めるためだけ）。
    ``race_conditions`` があれば、その条件の全部に合うレースだけ買う（研究「レースの種類ごとの買い方」の docs/03・04。券種ごとに向いたレースの中身）。
    例: ワイド・◎の期待値 1.00 以上のレース・線 1.0・上限 300倍・3点なら、◎ の単勝の期待値が 1.00 以上のレースで、組の期待値が 1.0 以上で 300倍以下のワイドを、期待値の高い順に3点まで買う。
    """

    ticket_type: TicketType | BracketTicket
    scope: str
    value_line: float
    odds_cap: float
    adopted: bool
    max_points: int | None = None
    rolling: bool = False
    stake_units: float = 0.5
    race_conditions: tuple[RaceCondition, ...] = ()

    @property
    def label(self) -> str:
        """表に出す買い方の名前。例: ``馬連（組の期待値）``。"""
        return f"{self.ticket_type.label}（組の期待値）"

    @property
    def condition(self) -> str:
        """人が読む決まり。例: ``全レース・期待値 1.1 以上・100倍以下``。"""
        points = f"・1レース {self.max_points}点まで" if self.max_points else ""
        race = f"・{'・'.join(condition.text for condition in self.race_conditions)}のレースだけ" if self.race_conditions else ""
        return f"{self.scope}・期待値 {self.value_line:.1f} 以上・{self.odds_cap:,.0f}倍以下{points}{race}"
