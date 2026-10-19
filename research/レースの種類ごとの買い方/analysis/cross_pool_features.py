"""組の表に、ほかの券種の市場から見た確率のもとを足す（docs/04 の 10）。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from yosou.shared.betting import TicketType

#: 券種 → 足すもとの列（docs/04 の 10 の表の順）。
CROSS_FEATURES: dict[TicketType, tuple[str, ...]] = {
    TicketType.WIDE: ("log_trio_market", "log_quinella_market"),
    TicketType.EXACTA: ("log_quinella_market", "log_wide_market"),
    TicketType.TRIO: ("log_wide_pairs", "log_quinella_pairs"),
}
_FLOOR = 1e-9


class CrossPoolFeatures:
    """``combos/<券種>_<年>.parquet`` の「その券種自身の市場」（列 ``q``）から、2頭の対ごとの市場の確率（馬連・ワイド・3連複を対に足したもの）を作り、
    ``ComboFeatures`` の表に ``CROSS_FEATURES`` の列を足す。対は小さい馬番が先（馬単は着順を区別せずに引く）。対の値が無ければ下限 1e-9 の対数。

    例: ワイドの組 3-7 の log_trio_market は、3連複の組のうち 3番と 7番を両方含む組の q の和の対数。3連複の組 1-3-7 の log_wide_pairs は、
    ワイドの 1-3・1-7・3-7 の q の対数の和。
    """

    def __init__(self, folder: Path) -> None:
        self._folder = Path(folder)

    def add(self, ticket_type: TicketType, frame: pd.DataFrame, year: int) -> pd.DataFrame:
        pairs = self._pairs(year, need_trio=ticket_type is TicketType.WIDE)
        table = frame.copy()
        if ticket_type is TicketType.TRIO:
            for name, column in (("log_wide_pairs", "wide"), ("log_quinella_pairs", "quinella")):
                total = np.zeros(len(table))
                for one, two in (("h1", "h2"), ("h1", "h3"), ("h2", "h3")):
                    total += np.log(self._lookup(pairs, table, one, two, column))
                table[name] = total.astype(np.float32)
            return table
        columns = {"log_trio_market": "trio", "log_quinella_market": "quinella", "log_wide_market": "wide"}
        for name in CROSS_FEATURES[ticket_type]:
            table[name] = np.log(self._lookup(pairs, table, "h1", "h2", columns[name])).astype(np.float32)
        return table

    def _lookup(self, pairs: pd.DataFrame, table: pd.DataFrame, one: str, two: str, column: str) -> np.ndarray:
        low, high = np.minimum(table[one], table[two]), np.maximum(table[one], table[two])
        index = pd.MultiIndex.from_arrays([table["race_id"].astype(str), low.astype(int), high.astype(int)])
        return pairs[column].reindex(index).fillna(_FLOOR).clip(lower=_FLOOR).to_numpy(dtype=float)

    def _pairs(self, year: int, need_trio: bool) -> pd.DataFrame:
        """列 ``quinella``・``wide``（と ``trio``）の、(race_id, 小さい馬番, 大きい馬番) を鍵にした表。"""
        parts = {}
        for name in ("quinella", "wide"):
            raw = pd.read_parquet(self._folder / f"{name}_{year}.parquet", columns=["rid", "h1", "h2", "q"])
            parts[name] = self._keyed(raw, "h1", "h2")["q"]
        if need_trio:
            raw = pd.read_parquet(self._folder / f"trio_{year}.parquet", columns=["rid", "h1", "h2", "h3", "q"])
            stacked = pd.concat([self._keyed(raw, one, two) for one, two in (("h1", "h2"), ("h1", "h3"), ("h2", "h3"))])
            parts["trio"] = stacked.groupby(level=[0, 1, 2])["q"].sum()
        return pd.DataFrame(parts)

    @staticmethod
    def _keyed(raw: pd.DataFrame, one: str, two: str) -> pd.DataFrame:
        low, high = np.minimum(raw[one], raw[two]).astype(int), np.maximum(raw[one], raw[two]).astype(int)
        keyed = pd.DataFrame({"race_id": raw["rid"].astype(str), "a": low, "b": high, "q": raw["q"].astype(float)})
        return keyed.groupby(["race_id", "a", "b"])[["q"]].sum()
