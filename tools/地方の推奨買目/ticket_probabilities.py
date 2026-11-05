"""券種ごとの組の確率: 3連単の全部の組の確率から、単勝・複勝・枠連・馬連・ワイド・馬単・3連複の組の確率を足し合わせて出す。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .position_model import PROBABILITY

#: 券種の名前と、組の列（馬番か枠番）。
TICKETS: tuple[str, ...] = ("単勝", "複勝", "枠連", "馬連", "ワイド", "馬単", "3連複", "3連単")
TICKET_KEYS: dict[str, tuple[str, ...]] = {"単勝": ("a",), "複勝": ("a",), "枠連": ("a", "b"), "馬連": ("a", "b"), "ワイド": ("a", "b"),
                                           "馬単": ("a", "b"), "3連複": ("a", "b", "c"), "3連単": ("a", "b", "c")}


@dataclass(frozen=True)
class TicketProbabilities:
    """``of(combos, frames)`` は、``combos``（``race_id``・``first``・``second``・``third``・``P``）と ``frames``（``race_id``・``horse_no``・``frame_no``）から、
    券種 → 組の表（``race_id``・``a``（・``b``・``c``）・``P``）を返す。馬連・3連複・ワイド・枠連の組は番号の小さい順。"""

    def of(self, combos: pd.DataFrame, frames: pd.DataFrame) -> dict[str, pd.DataFrame]:
        c = combos[["race_id", "first", "second", "third", PROBABILITY]]
        out: dict[str, pd.DataFrame] = {}
        out["3連単"] = c.rename(columns={"first": "a", "second": "b", "third": "c"})
        exacta = c.groupby(["race_id", "first", "second"], as_index=False)[PROBABILITY].sum().rename(columns={"first": "a", "second": "b"})
        out["馬単"] = exacta
        out["単勝"] = c.groupby(["race_id", "first"], as_index=False)[PROBABILITY].sum().rename(columns={"first": "a"})
        out["馬連"] = self._unordered(exacta, ("a", "b"))
        trio = self._unordered(out["3連単"], ("a", "b", "c"))
        out["3連複"] = trio
        place = pd.concat([trio[["race_id", name, PROBABILITY]].rename(columns={name: "a"}) for name in ("a", "b", "c")])
        out["複勝"] = place.groupby(["race_id", "a"], as_index=False)[PROBABILITY].sum()
        wide = pd.concat([trio[["race_id", "a", "b", PROBABILITY]], trio[["race_id", "a", "c", PROBABILITY]].rename(columns={"c": "b"}),
                          trio[["race_id", "b", "c", PROBABILITY]].rename(columns={"b": "a", "c": "b"})])
        out["ワイド"] = wide.groupby(["race_id", "a", "b"], as_index=False)[PROBABILITY].sum()
        out["枠連"] = self._bracket(out["馬連"], frames)
        return out

    def _unordered(self, table: pd.DataFrame, columns: tuple[str, ...]) -> pd.DataFrame:
        numbers = np.sort(table[list(columns)].to_numpy(), axis=1)
        keyed = pd.DataFrame({"race_id": table["race_id"].to_numpy(), **{name: numbers[:, i] for i, name in enumerate(columns)}, PROBABILITY: table[PROBABILITY].to_numpy()})
        return keyed.groupby(["race_id", *columns], as_index=False)[PROBABILITY].sum()

    def _bracket(self, quinella: pd.DataFrame, frames: pd.DataFrame) -> pd.DataFrame:
        f = frames.assign(frame_no=pd.to_numeric(frames["frame_no"], errors="coerce"))[["race_id", "horse_no", "frame_no"]]
        table = quinella.merge(f.rename(columns={"horse_no": "a", "frame_no": "fa"}), on=["race_id", "a"], how="inner")
        table = table.merge(f.rename(columns={"horse_no": "b", "frame_no": "fb"}), on=["race_id", "b"], how="inner")
        table = table.assign(a=np.minimum(table["fa"], table["fb"]).astype(int), b=np.maximum(table["fa"], table["fb"]).astype(int))
        return table.groupby(["race_id", "a", "b"], as_index=False)[PROBABILITY].sum()
