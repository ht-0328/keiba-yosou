"""学習の表（確定オッズ）を、締め切り前の断面のオッズの時点の表に置き換える。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from yosou.shared.win_correction import QUINELLA_TOP2, QuinellaTop2

from 的中実績の公開ルール.analysis.snapshot_probability import SnapshotProbability


@dataclass(frozen=True)
class SnapshotTable:
    """``final`` は ``TrainingTable.build`` の表（確定オッズ）、``boards`` は締め切り前の断面の板（``PreDeadlineBoardRepository`` の
    ``単勝``・``複勝最低``・``複勝最高``・``馬連``）。

    ``build`` は、全頭の単勝・複勝（最低）のオッズと馬連の板がそろうレースだけを残し、単勝・複勝のオッズと馬連から見た率を断面の値に、
    1着の確率を断面の時点の近似（``SnapshotProbability``。出発点だけを差し替える）に置き換えた表。3着以内の確率と事実表の列はそのまま。
    """

    final: pd.DataFrame
    boards: dict[str, pd.DataFrame]

    def build(self) -> pd.DataFrame:
        table = self.final
        for name, column in (("単勝", "snapshot_win"), ("複勝最低", "snapshot_place_low"), ("複勝最高", "snapshot_place_high")):
            table = table.merge(_by_horse(self.boards[name], column), on=["race_id", "horse_no"], how="left")
        quinella = QuinellaTop2().of(self.boards["馬連"].assign(race_id=self.boards["馬連"]["race_id"].astype(str)))
        table = table.merge(quinella.rename(columns={QUINELLA_TOP2: "snapshot_quinella"}), on=["race_id", "horse_no"], how="left")
        complete = table.groupby("race_id")[["snapshot_win", "snapshot_place_low", "snapshot_quinella"]].transform(lambda v: v.notna().all()).all(axis=1)
        table = table[complete].copy()
        shifted = SnapshotProbability().of(pd.DataFrame({"race_id": table["race_id"], "p": table["win_probability"],
                                                         "odds": table["win_odds"], "snapshot_odds": table["snapshot_win"]}))
        table = table.assign(win_probability=shifted, win_odds=table["snapshot_win"], place_odds_low=table["snapshot_place_low"],
                             place_odds_high=table["snapshot_place_high"], **{QUINELLA_TOP2: table["snapshot_quinella"]})
        return table.drop(columns=["snapshot_win", "snapshot_place_low", "snapshot_place_high", "snapshot_quinella"]).reset_index(drop=True)


def _by_horse(board: pd.DataFrame, name: str) -> pd.DataFrame:
    """馬番の板を、列 ``race_id``・``horse_no``・``name`` にする。"""
    return pd.DataFrame({"race_id": board["race_id"].astype(str), "horse_no": board["combo"].astype(int), name: board["odds"].astype(float)})
