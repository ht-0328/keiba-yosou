"""道具「印の成績」が書いた買い目の表（1行 = 1点）を読み、本線の買い目と ◎ を取り出す。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

#: 本線として数える券種（抑えを足す 3連複と 3連単）。
MAIN_TYPES: tuple[str, ...] = ("3連複", "3連単")


@dataclass(frozen=True)
class MarkTicketFile:
    """``path`` は ``reports/…/印の成績/…/買い目/<名前>.csv``（列 レースID・開催日・区切り・買い方・券種・組番・単位・払戻（100円あたり） …）。

    ``main`` は 3連複・3連単の元の買い目（買い方の名前が「（◎」で始まる括弧を持つもの。組の期待値の買い方や ◎軸・軸馬の足し分を除く）、
    ``favorites`` はレースごとの ◎ の馬番（買い方「単勝」の組番）。トリガミなどで外した点（外した理由のある行）は読まない。"""

    path: Path

    def frame(self) -> pd.DataFrame:
        table = pd.read_csv(self.path, dtype={"レースID": str, "組番": str}, encoding="utf-8-sig")
        if "外した理由" in table:
            table = table.loc[table["外した理由"].isna()]
        return table.rename(columns={"レースID": "race_id", "開催日": "race_date", "券種": "ticket_type", "買い方": "rule", "組番": "combo",
                                     "単位": "unit", "払戻（100円あたり）": "payout"})

    def main(self, table: pd.DataFrame) -> pd.DataFrame:
        original = table["rule"].str.contains("（◎", regex=False) & ~table["rule"].str.contains("軸", regex=False)
        return table.loc[table["ticket_type"].isin(MAIN_TYPES) & original]

    @staticmethod
    def favorites(table: pd.DataFrame) -> pd.Series:
        win = table.loc[table["rule"] == "単勝"].drop_duplicates("race_id")
        return win.set_index("race_id")["combo"].astype(int)
