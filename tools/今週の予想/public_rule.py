"""的中実績の公開ルール: 当日の予想で、◎ の単勝の期待値が線以上・単勝オッズが上限以下のレースだけ、◎ の単勝を 100円買う。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from 今週の予想.forecast_columns import HORSE_NO, MARK, WIN_ODDS, WIN_VALUE

#: 見出しのことば。
LABEL = "公開ルール（◎ の単勝）"
#: ◎ の単勝の期待値（1着になる確率 × 単勝オッズ）の線。これ以上のレースだけ買う。
VALUE_LINE = 1.00
#: ◎ の単勝オッズの上限（倍）。これ以下のレースだけ買う。
ODDS_CAP = 6.0
#: 1レースに買う金額（円）。
STAKE_YEN = 100
#: 買う券種の名前（払戻を引くときの名前）。
TICKET_TYPE = "単勝"
#: 買う時点（予想の JSON の timing）。
_RACE_DAY = "当日"
_TOP_MARK = "◎"


@dataclass(frozen=True)
class PublicRule:
    """1レースの公開ルールの判定。``horse_no`` は買う ◎ の馬番（買わなければ None）、``reason`` は買わない理由（買うなら空）。

    決まり（研究「的中実績の公開ルール」）: 当日の予想で、◎ の単勝の期待値が ``VALUE_LINE`` 以上、かつ ◎ の単勝オッズが ``ODDS_CAP`` 倍以下なら、
    ◎ の単勝を ``STAKE_YEN`` 円買う。◎ は印の決まりのとおり（単勝 30倍以下で単勝の期待値がいちばん高い馬）。
    1レースの文・発走前の通知（``RaceMessage``）・その日の結果（``RaceResult``）が同じ判定を使う。

    例: ◎ が 5番で、期待値 1.04・単勝 4.2倍なら買う（``line`` は ``公開ルール（◎ の単勝）: 単勝 5 100円``）。
    単勝 7.5倍なら買わない（理由は ``◎ の単勝が 6倍を超える``）。
    """

    horse_no: int | None
    reason: str

    @classmethod
    def of(cls, forecast: dict[str, Any]) -> PublicRule:
        if forecast.get("timing") != _RACE_DAY:
            return cls(None, "当日の予想で判定する")
        top = next((horse for horse in forecast.get("horses") or [] if horse.get(MARK) == _TOP_MARK), None)
        if top is None:
            return cls(None, "◎ がいない")
        return cls._judge(top)

    @classmethod
    def _judge(cls, top: dict[str, Any]) -> PublicRule:
        value, odds = top.get(WIN_VALUE), top.get(WIN_ODDS)
        if not _is_number(value) or not _is_number(odds):
            return cls(None, "◎ の単勝オッズが無い")
        if value < VALUE_LINE:
            return cls(None, f"◎ の単勝の期待値が {VALUE_LINE:.2f} 未満")
        if odds > ODDS_CAP:
            return cls(None, f"◎ の単勝が {ODDS_CAP:g}倍を超える")
        return cls(int(top[HORSE_NO]), "")

    @property
    def buys(self) -> bool:
        return self.horse_no is not None

    def line(self) -> str:
        """通知・1レースの文の1行。買うなら馬番と金額、買わないなら「なし（理由）」。"""
        if self.horse_no is None:
            return f"{LABEL}: なし（{self.reason}）"
        return f"{LABEL}: {TICKET_TYPE} {self.horse_no} {STAKE_YEN:,}円"

    def stakes(self) -> list[tuple[str, str, int]]:
        """精算に使う、（券種の名前, 馬番（2桁）, 金額）の並び。買わなければ空。"""
        if self.horse_no is None:
            return []
        return [(TICKET_TYPE, f"{self.horse_no:02d}", STAKE_YEN)]


def _is_number(value: Any) -> bool:
    """欠損値でない数か。"""
    return isinstance(value, (int, float)) and value == value
