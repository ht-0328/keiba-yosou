"""道具「印の成績」の買い目の表どうしを、券種ごと・期間ごとの的中率と回収率で並べる表（消の決め方を替えたときの比べ）。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from 共通.render import Table

from ..tables.cells import percent
from .evaluation_frame import CONFIRM, CONFIRM_FROM, EXPLORE
from .mark_ticket_file import MarkTicketFile

_NOTE = ("1点 100円 × 単位で数える（単位は道具「印の成績」の買い目の表のまま。トリガミなどで外した点は数えない）。的中率 = 1点でも当たったレース ÷ 買ったレース。"
         "「消を使う買い方」は、買い方の名前に「消」を含むもの（消を除いて組む 3連複）。印（◎○▲△☆注）も消の馬を外して付くので、どの買い方も消の決め方で変わりうる。")


@dataclass(frozen=True)
class MarkComparisonTable:
    """``files`` は（消の決め方の名前 → 買い目の csv）。券種ごと・消を使う買い方・全部の合計の行を、期間ごとに並べる。"""

    files: dict[str, Path]

    def build(self, title: str) -> Table:
        frames = {name: self._prepared(path) for name, path in self.files.items()}
        groups = ["単勝", "複勝", "枠連", "馬連", "馬単", "ワイド", "3連複", "3連単", "消を使う買い方", "全部の合計"]
        rows = []
        for group in groups:
            for period in (EXPLORE, CONFIRM):
                cells = []
                for frame in frames.values():
                    part = frame.loc[(frame["period"] == period) & self._mask(frame, group)]
                    cells.extend(self._cells(part))
                rows.append([group, period, *cells])
        columns = ["券種・買い方", "期間"]
        for name in frames:
            columns.extend([f"{name} 買ったレース", f"{name} 的中率", f"{name} 回収率"])
        return Table(columns, rows, title=title, note=_NOTE)

    @staticmethod
    def _prepared(path: Path) -> pd.DataFrame:
        frame = MarkTicketFile(path).frame()
        frame["period"] = np.where(pd.to_datetime(frame["race_date"]) >= CONFIRM_FROM, CONFIRM, EXPLORE)
        return frame

    @staticmethod
    def _mask(frame: pd.DataFrame, group: str) -> pd.Series:
        if group == "全部の合計":
            return pd.Series(True, index=frame.index)
        if group == "消を使う買い方":
            return frame["rule"].str.contains("消", regex=False)
        return frame["ticket_type"] == group

    @staticmethod
    def _cells(part: pd.DataFrame) -> list[object]:
        if part.empty:
            return [0, "", ""]
        stake = float((part["unit"] * 100).sum())
        paid = float((part["unit"] * part["payout"]).sum())
        races = part["race_id"].nunique()
        hits = part.loc[part["payout"] > 0, "race_id"].nunique()
        return [races, percent(hits, races), percent(paid, stake)]
