"""どの出走について記録を読むか。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from 共通 import facts, keys

#: 材料の締めの日の列の名前（関係に持たせるとき）。
AS_OF_COLUMN = "as_of_date"


@dataclass(frozen=True)
class TargetScope:
    """記録を読む対象の出走。学習では「ある日以降の全部の出走」、予測では「1レースの出走馬」。

    ``relation`` は SQL の FROM に置ける関係（表の名前か、かっこで包んだ SELECT）。事実表と同じ列を持つ。
    リポジトリの SQL はこの関係を参照するので、学習と予測で同じ SQL を使える。

    ``as_of_column`` は、関係にある「材料の締めの日」の列の名前（日付で区切って数える材料を、その日までの記録で数える。
    特別登録の予想の設計書 11 の 6）。None なら列は無く、締めの日は今までどおり開催日の前日になる。
    """

    relation: str
    as_of_column: str | None = None

    @classmethod
    def since(cls, first_day: date, as_of_sql: str | None = None) -> TargetScope:
        """事実表のうち、開催日が ``first_day`` 以降の出走。

        ``as_of_sql`` は、事実表の列（``race_date`` など）から材料の締めの日を作る SQL の式。渡すと、関係に
        ``as_of_date`` の列が付く。
        """
        day = first_day.isoformat()
        if as_of_sql is None:
            return cls(f"(SELECT * FROM {facts.FACTS_TABLE} WHERE race_date >= '{day}')")
        return cls(f"(SELECT *, {as_of_sql} AS {AS_OF_COLUMN} FROM {facts.FACTS_TABLE} WHERE race_date >= '{day}')",
                   AS_OF_COLUMN)

    @classmethod
    def of_table(cls, table: str, as_of_column: str | None = None) -> TargetScope:
        """一時表 ``table`` の出走。``as_of_column`` は、その表にある材料の締めの日の列の名前（無ければ None）。"""
        return cls(keys.q(table), as_of_column)

    def as_of_expr(self, alias: str = "") -> str:
        """材料の締めの日の式（日付型）。列が無ければ NULL（締めの日は開催日の前日のまま）。"""
        if self.as_of_column is None:
            return "NULL::DATE"
        return f"CAST({keys.col(self.as_of_column, alias)} AS DATE)"
