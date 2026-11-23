"""買った馬（軸と相手）に、単勝・馬単・3連単の払戻を当てて、1頭1行の成績の表にする。"""

from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

from .late_pick import LatePick

#: 成績の表の列。金額は 1点 100円で買ったときの円。
COLUMNS: tuple[str, ...] = ("race_id", "day", "horse_no", "win_cost", "win_back", "exacta_cost", "exacta_back", "trifecta_cost", "trifecta_back")
STAKE = 100


class LateSettlement:
    """``wins`` は単勝の払戻（``race_id``・``horse_no``・``payout``）、``exactas`` は馬単の払戻（``race_id``・``first``・``second``・``payout``）、
    ``trifectas`` は 3連単の払戻（``race_id``・``first``・``second``・``third``・``payout``）。
    払戻は 100円あたりの円。払戻の表に無いレース（まだ結果が無い・中止）の馬は、``settle`` の表に入れない。"""

    def __init__(self, wins: pd.DataFrame, exactas: pd.DataFrame, trifectas: pd.DataFrame) -> None:
        self._wins = {(str(row.race_id), int(row.horse_no)): float(row.payout) for row in wins.itertuples()}
        self._exactas = {(str(row.race_id), int(row.first), int(row.second)): float(row.payout) for row in exactas.itertuples()}
        self._trifectas = {(str(row.race_id), int(row.first), int(row.second), int(row.third)): float(row.payout) for row in trifectas.itertuples()}
        self._settled = {str(race_id) for race_id in wins["race_id"]}

    def settle(self, picks: Iterable[tuple[str, LatePick]]) -> pd.DataFrame:
        """``picks`` は（レースID, 買った馬）の並び。開催日はレースID の頭 8 桁から。"""
        rows = [self._row(rid, pick) for rid, pick in picks if rid in self._settled]
        return pd.DataFrame(rows, columns=list(COLUMNS))

    def _row(self, rid: str, pick: LatePick) -> tuple:
        exactas = pick.exactas()
        exacta_back = sum(self._exactas.get((rid, *combo), 0.0) for combo in exactas)
        combos = pick.trifectas()
        back = sum(self._trifectas.get((rid, *combo), 0.0) for combo in combos)
        day = pd.Timestamp(f"{rid[:4]}-{rid[4:6]}-{rid[6:8]}")
        return (rid, day, pick.horse_no, STAKE, self._wins.get((rid, pick.horse_no), 0.0), STAKE * len(exactas), exacta_back,
                STAKE * len(combos), back)
