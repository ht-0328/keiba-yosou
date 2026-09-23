"""読む期間（開催日の範囲）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from 共通 import keys


@dataclass(frozen=True)
class RaceDayRange:
    """開催日の範囲（両端を含む）。レース単位の表（``hr``・``o1``〜``o6``）の 開催年・開催月日 で絞る条件を作る。"""

    first_day: date
    last_day: date

    def __post_init__(self) -> None:
        if self.last_day < self.first_day:
            raise ValueError(f"期間の終わり（{self.last_day}）は始まり（{self.first_day}）以降の日にしてください")

    def condition(self, alias: str = "") -> str:
        """``(開催年 || 開催月日) BETWEEN ? AND ?`` の形の条件。引数は ``params``。"""
        return f"({keys.col('開催年', alias)} || {keys.col('開催月日', alias)}) BETWEEN ? AND ?"

    @property
    def params(self) -> list[str]:
        """``condition`` の引数（``YYYYMMDD`` の2つ）。"""
        return [self.first_day.strftime("%Y%m%d"), self.last_day.strftime("%Y%m%d")]
