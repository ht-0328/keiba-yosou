"""どの出走について記録を読むか。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from 共通 import facts, keys


@dataclass(frozen=True)
class TargetScope:
    """記録を読む対象の出走。学習では「ある日以降の全部の出走」、予測では「1レースの出走馬」。

    ``relation`` は SQL の FROM に置ける関係（表の名前か、かっこで包んだ SELECT）。事実表と同じ列を持つ。
    リポジトリの SQL はこの関係を参照するので、学習と予測で同じ SQL を使える。
    """

    relation: str

    @classmethod
    def since(cls, first_day: date) -> TargetScope:
        """事実表のうち、開催日が ``first_day`` 以降の出走。"""
        day = first_day.isoformat()
        return cls(f"(SELECT * FROM {facts.FACTS_TABLE} WHERE race_date >= '{day}')")

    @classmethod
    def of_table(cls, table: str) -> TargetScope:
        """一時表 ``table`` の出走。"""
        return cls(keys.q(table))
