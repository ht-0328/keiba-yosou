"""票の表を作る: 出走の行（全頭の予想の確率つき）と、3連単・馬単・3連複・複勝の確定オッズ、3連単の払戻から ``PoolTables`` を組む。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .pool_tables import COMBO_COLUMNS, HORSE_COLUMNS, PAIR_COLUMNS, PoolTables

_FLOOR = 1e-9
_NOT_PLACED = 99.0


def group_key(*columns: np.ndarray) -> np.ndarray:
    """複数の列を1つの整数の鍵にする（race_id は 16桁なので、馬番 2桁ずつを下に足す）。"""
    key = columns[0].astype(np.int64)
    for c in columns[1:]:
        key = key * 100 + c.astype(np.int64)
    return key


@dataclass(frozen=True)
class PoolTablesBuilder:
    """``build`` の引数:

    - ``horses``: 出走の行。``race_id``（整数）・``race_date``・``horse_no``・``popularity``・``win_odds``・``finish``・``p1``・``p1_lgb``・``p1_cat``・``p3``・``p3_lgb``・``p3_cat``。
    - ``trifecta``: 3連単の全部の組の確定オッズ（``race_id``・``first``・``second``・``third``・``odds``）と払戻（``payout``。外れは 0。発走前は列ごと無くてよい）。
    - ``exacta``: 馬単の確定オッズ（``race_id``・``a``・``b``・``odds``）。
    - ``trio``: 3連複の確定オッズ（``race_id``・``a``・``b``・``c``（馬番の小さい順）・``odds``）。
    - ``place``: 複勝の確定オッズ（``race_id``・``a``・``odds_lo``・``odds_hi``）。

    票から見た割合はレース内の softmax で使うので、レース内で共通の定数（合計で割ること）は要らない。1/オッズ の合計で代用する。
    どれかの確率やオッズが欠けたレースは落とす。
    """

    def build(self, horses: pd.DataFrame, trifecta: pd.DataFrame, exacta: pd.DataFrame, trio: pd.DataFrame, place: pd.DataFrame) -> PoolTables:
        h = self._horses(horses)
        c = self._combos(trifecta[trifecta["race_id"].isin(h["race_id"])], trio)
        pairs = self._pairs(c, exacta, trio)
        h = self._with_pools(h, c, exacta, trio, place)
        keep = self._complete_races(h)
        return PoolTables(
            horses=h[h["race_id"].isin(keep)].reset_index(drop=True)[list(HORSE_COLUMNS)],
            pairs=pairs[pairs["race_id"].isin(keep)].reset_index(drop=True)[list(PAIR_COLUMNS)],
            combos=c[c["race_id"].isin(keep)].reset_index(drop=True)[list(COMBO_COLUMNS)],
        )

    def _horses(self, horses: pd.DataFrame) -> pd.DataFrame:
        h = horses.copy()
        for col in ("popularity", "win_odds", "finish", "p1", "p1_lgb", "p1_cat", "p3", "p3_lgb", "p3_cat"):
            h[col] = pd.to_numeric(h[col], errors="coerce").astype(float)
        h["finish"] = h["finish"].fillna(_NOT_PLACED)
        h = h.sort_values(["race_id", "horse_no"]).reset_index(drop=True)
        inverse = 1.0 / h["win_odds"].replace(0, np.nan)
        h["s"] = inverse / inverse.groupby(h["race_id"]).transform("sum")
        return h

    def _combos(self, trifecta: pd.DataFrame, trio: pd.DataFrame) -> pd.DataFrame:
        c = trifecta.sort_values(["race_id", "first", "second", "third"]).reset_index(drop=True)
        inverse = 1.0 / c["odds"].to_numpy(dtype=np.float64)
        race = c["race_id"].to_numpy()
        m = inverse / pd.Series(inverse).groupby(race).transform("sum").to_numpy()
        key_ab = group_key(race, c["first"].to_numpy(), c["second"].to_numpy())
        m_ab = pd.Series(m).groupby(key_ab).transform("sum").to_numpy()
        c["m"] = m
        c["m3"] = m / m_ab
        c["key_ab"] = key_ab
        sorted_numbers = np.sort(c[["first", "second", "third"]].to_numpy(), axis=1)
        key = pd.DataFrame({"race_id": race, "a": sorted_numbers[:, 0], "b": sorted_numbers[:, 1], "c": sorted_numbers[:, 2]})
        trio_inverse = trio.assign(m3t=1.0 / trio["odds"].astype(float))[["race_id", "a", "b", "c", "m3t"]]
        c["m3t"] = self._filled(key.merge(trio_inverse, on=["race_id", "a", "b", "c"], how="left")["m3t"].to_numpy())
        c["payout"] = c["payout"].fillna(0).astype(int) if "payout" in c.columns else 0   # 発走前（本番）は払戻が無い
        return c

    def _pairs(self, combos: pd.DataFrame, exacta: pd.DataFrame, trio: pd.DataFrame) -> pd.DataFrame:
        race = combos["race_id"].to_numpy()
        key_a = group_key(race, combos["first"].to_numpy())
        m_a = pd.Series(combos["m"].to_numpy()).groupby(key_a).transform("sum").to_numpy()
        m_ab = combos["m"].to_numpy() / combos["m3"].to_numpy()
        pairs = pd.DataFrame({"race_id": race, "first": combos["first"].to_numpy(), "second": combos["second"].to_numpy(), "m2": m_ab / m_a})
        pairs = pairs.drop_duplicates(["race_id", "first", "second"]).reset_index(drop=True)
        ex = exacta.assign(m2x=1.0 / exacta["odds"].astype(float)).rename(columns={"a": "first", "b": "second"})[["race_id", "first", "second", "m2x"]]
        tr = trio.assign(inv=1.0 / trio["odds"].astype(float))
        both = pd.concat([tr[["race_id", "a", "b", "inv"]], tr[["race_id", "a", "c", "inv"]].rename(columns={"c": "b"}),
                          tr[["race_id", "b", "c", "inv"]].rename(columns={"b": "a", "c": "b"})])
        both = both.groupby(["race_id", "a", "b"], as_index=False)["inv"].sum()
        both = pd.concat([both, both.rename(columns={"a": "b", "b": "a"})]).rename(columns={"a": "first", "b": "second", "inv": "m2t"})
        pairs = pairs.merge(ex, on=["race_id", "first", "second"], how="left").merge(both, on=["race_id", "first", "second"], how="left")
        for col in ("m2x", "m2t"):
            pairs[col] = self._filled(pairs[col].to_numpy())
        return pairs

    def _with_pools(self, h: pd.DataFrame, combos: pd.DataFrame, exacta: pd.DataFrame, trio: pd.DataFrame, place: pd.DataFrame) -> pd.DataFrame:
        race = combos["race_id"].to_numpy()
        first = pd.DataFrame({"race_id": race, "horse_no": combos["first"].to_numpy(), "m_a": combos["m"].to_numpy()})
        m_a = first.groupby(["race_id", "horse_no"], as_index=False)["m_a"].sum()
        ex = exacta.assign(inv=1.0 / exacta["odds"].astype(float)).groupby(["race_id", "a"], as_index=False)["inv"].sum()
        m_ax = ex.rename(columns={"a": "horse_no", "inv": "m_ax"})
        tr = trio.assign(inv=1.0 / trio["odds"].astype(float))
        m1t = pd.concat([tr[["race_id", "a", "inv"]].rename(columns={"a": "horse_no"}), tr[["race_id", "b", "inv"]].rename(columns={"b": "horse_no"}),
                         tr[["race_id", "c", "inv"]].rename(columns={"c": "horse_no"})]).groupby(["race_id", "horse_no"], as_index=False)["inv"].sum()
        m1t = m1t.rename(columns={"inv": "m1t"})
        px = place.assign(px=2.0 / (place["odds_lo"].astype(float) + place["odds_hi"].astype(float))).rename(columns={"a": "horse_no"})[["race_id", "horse_no", "px"]]
        h = h.merge(m_a, on=["race_id", "horse_no"], how="left").merge(m_ax, on=["race_id", "horse_no"], how="left")
        h = h.merge(m1t, on=["race_id", "horse_no"], how="left").merge(px, on=["race_id", "horse_no"], how="left")
        for col in ("m_ax", "m1t", "px"):
            h[col] = self._filled(h[col].to_numpy())
        return h

    def _complete_races(self, h: pd.DataFrame) -> pd.Index:
        """確率・支持率・3連単の票のどれかが欠けた馬のいるレースは外す。"""
        incomplete = h.groupby("race_id")[["p1", "p3", "s", "m_a"]].apply(lambda t: bool(t.isna().any().any()))
        return incomplete[~incomplete].index

    def _filled(self, values: np.ndarray) -> np.ndarray:
        """発売の無い組（値が無い）は、その表の最小の値で埋める（0 にしない）。"""
        values = values.astype(np.float64)
        if np.isnan(values).all():
            return np.full_like(values, _FLOOR)
        return np.clip(np.where(np.isnan(values), np.nanmin(values), values), _FLOOR, None)
