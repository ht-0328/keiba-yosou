"""道具「印の成績」（--scene 地方）が書いた買い目の表（1行 = 1点）から、印で組む買い方の組・確定オッズ・払戻を読む。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

#: 読む買い方（印の成績の「買い方」の列の値。中央の印の買い方 ``BET_RULES`` の元の6つ）。
MARK_RULES: tuple[str, ...] = ("単勝", "ワイド", "馬連", "馬単", "3連複（◎−○▲☆−○▲△☆）", "3連単（◎→○▲☆→○▲△☆）")
#: 表の列。``top_band`` は ◎ の単勝の期待値の帯（``1.00 以上`` か ``1.00 未満``）、``dropped`` はトリガミかオッズ無しで外した点。
COLUMNS: tuple[str, ...] = ("race_id", "race_date", "top_band", "rule", "ticket", "a", "b", "c", "odds", "payout", "dropped")
_SOURCE = {"レースID": "race_id", "開催日": "race_date", "◎の期待値": "top_band", "買い方": "rule", "券種": "ticket",
           "組番": "combo", "確定オッズ": "odds", "払戻（100円あたり）": "payout", "外した理由": "reason"}
_CHUNK = 2_000_000
#: 組番の馬の数（券種 → 頭数）。組番は馬番を 2桁ずつ並べた数（先頭の 0 は落ちる。例 3→1→4 は 30104）。
_HORSES = {"単勝": 1, "ワイド": 2, "馬連": 2, "馬単": 2, "3連複": 3, "3連単": 3}


@dataclass(frozen=True)
class MarkCombos:
    """``path`` の CSV（印の成績の ``買い目/<全頭の予想の名前>.csv``）を少しずつ読み、``MARK_RULES`` の行だけを ``COLUMNS`` の表にする。
    組の馬番は ``a``・``b``・``c``（足りない分は 0）。"""

    path: Path

    def load(self) -> pd.DataFrame:
        parts = [self._chunk(chunk) for chunk in pd.read_csv(self.path, usecols=list(_SOURCE), chunksize=_CHUNK, encoding="utf-8-sig")]
        return pd.concat(parts, ignore_index=True)

    @staticmethod
    def _chunk(chunk: pd.DataFrame) -> pd.DataFrame:
        table = chunk.rename(columns=_SOURCE)
        table = table[table["rule"].isin(MARK_RULES)]
        return split_combo(table)


def split_combo(table: pd.DataFrame) -> pd.DataFrame:
    """``combo``（組番の数）を券種の頭数に合わせて ``a``・``b``・``c`` に分け、``dropped`` を付けて ``COLUMNS`` の表にする。"""
    combo = pd.to_numeric(table["combo"], errors="coerce").fillna(0).astype(np.int64).to_numpy()
    horses = table["ticket"].map(_HORSES).fillna(1).astype(int).to_numpy()
    a = np.where(horses == 1, combo, np.where(horses == 2, combo // 100, combo // 10_000))
    b = np.where(horses == 1, 0, np.where(horses == 2, combo % 100, (combo // 100) % 100))
    c = np.where(horses == 3, combo % 100, 0)
    out = table.assign(race_id=table["race_id"].astype(np.int64), a=a, b=b, c=c, dropped=table["reason"].notna(),
                       payout=pd.to_numeric(table["payout"], errors="coerce").fillna(0.0))
    return out[list(COLUMNS)].reset_index(drop=True)
