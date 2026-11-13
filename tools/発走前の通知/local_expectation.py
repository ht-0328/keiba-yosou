"""地方の1レースの期待度（◎ の点数と S・A・B・C）。通知の文の見出しの下の1行と、表の画像の見出しの札に出す。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.shared.race_grade import EXPECTATION_LABEL, LocalExpectationScale

from 今週の予想.forecast_columns import MARK, WIN_PROBABILITY, WIN_VALUE
from 今週の予想.mark_rule import TOP_MARK

#: 出せないときの字と、理由。
NONE = "なし"
NO_VALUE_REASON = "◎ の単勝の期待値が無い"
NOT_RACE_DAY_REASON = "馬体重が届く前の前日の時点では出さない。当日の時点で出す"


@dataclass(frozen=True)
class LocalExpectation:
    """1レースの期待度（設計書「買うレースと買い目を決める」の 11）。点数は ◎ の1着の確率 ＋ 3 ×（単勝の期待値 − 1）（``LocalExpectationScale``）。
    当日の時点だけ出す（前日の時点の予想は、線を当てると大半が C になり、◎ の回収率も等級の順に上がらないので目安にならない）。
    ◎ がいないか、◎ の期待値が無い（オッズが無い）なら、点数も等級も None で ``reason`` に理由。買い目はこの値で変えない。"""

    score: float | None
    grade: str | None
    reason: str = ""

    @classmethod
    def of(cls, table: pd.DataFrame) -> LocalExpectation:
        """印を付けた表（``MarkRule.assign`` の列）から、◎ の行の 1着になる確率と単勝の期待値で出す。"""
        top = table[table[MARK] == TOP_MARK] if MARK in table.columns else table.iloc[0:0]
        if top.empty or WIN_PROBABILITY not in top.columns or WIN_VALUE not in top.columns:
            return cls(None, None, NO_VALUE_REASON)
        row = top.iloc[0]
        score = LocalExpectationScale.score(_number(row[WIN_PROBABILITY]), _number(row[WIN_VALUE]))
        if score is None:
            return cls(None, None, NO_VALUE_REASON)
        return cls(score, LocalExpectationScale().of(score))

    @classmethod
    def not_race_day(cls) -> LocalExpectation:
        """前日の時点（当日の時点で出す）。"""
        return cls(None, None, NOT_RACE_DAY_REASON)

    def text(self) -> str:
        """通知の文の1行。例 ``期待度 A（点数 0.21）``。出せなければ ``期待度 なし（理由）``。"""
        if self.grade is None or self.score is None:
            return f"{EXPECTATION_LABEL} {NONE}（{self.reason or NO_VALUE_REASON}）"
        return f"{EXPECTATION_LABEL} {self.grade}（点数 {self.score:.2f}）"

    def badge(self) -> str:
        """表の画像の見出しの札。例 ``期待度 A``。出せなければ空（札を描かない）。"""
        return f"{EXPECTATION_LABEL} {self.grade}" if self.grade is not None else ""


def _number(value: object) -> float | None:
    return None if value is None or pd.isna(value) else float(value)
