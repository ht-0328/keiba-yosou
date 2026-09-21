"""鍵と日付を持つ、過去の記録の表。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DatedRecords:
    """過去の記録の表と、その鍵の列・日付の列の名前。

    ``table`` は、同じ鍵・同じ日付の中で古い順に並べておく（``AsOfLookup`` は、いちばん下の行を新しい行として引く）。
    """

    table: pd.DataFrame
    key_column: str
    date_column: str
