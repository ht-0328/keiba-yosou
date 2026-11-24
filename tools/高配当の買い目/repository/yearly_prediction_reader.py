"""年ごとの予測を、1年ぶんずつ、成績を数えるのに要る列だけ読む。"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pandas as pd

from yosou.shared.betting import TicketType

from 高配当の買い目.pick_columns import PICK_COLUMNS, RACE_ID


class YearlyPredictionReader:
    """予想のパッケージの年ごとの予測の置き場（``store``。``PredictionStore``。``years(券種)`` と ``path(券種, 年)`` を使う）から、
    1つの券種の予測を1年ぶんずつ読む。

    3連単は1年で数百万行あるので、全部の年を一度につながず（``PredictionStore.load`` はつないで返す）、1年ずつ・``PICK_COLUMNS`` の列だけ読む。
    1年も無ければ ``FileNotFoundError``（先に予想のパッケージの walk で作る）。
    """

    def __init__(self, store: Any) -> None:
        self._store = store

    def years(self, ticket_type: TicketType) -> list[int]:
        """その券種の予測のある年（古い順）。"""
        return list(self._store.years(ticket_type))

    def read(self, ticket_type: TicketType) -> Iterator[pd.DataFrame]:
        years = self.years(ticket_type)
        if not years:
            raise FileNotFoundError(f"{ticket_type.label}の年ごとの予測がありません（先に python -m yosou.high_payout_combos walk で作ってください）")
        for year in years:
            table = pd.read_parquet(self._store.path(ticket_type, year), columns=list(PICK_COLUMNS))
            yield table.assign(**{RACE_ID: table[RACE_ID].astype(str)})
