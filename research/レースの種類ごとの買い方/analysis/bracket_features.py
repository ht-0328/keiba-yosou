"""馬連の組の表を枠の組に足し合わせ、枠連の組の確率のもとを付ける（docs/04 の 3）。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .race_kinds import KIND_DUMMIES, KIND_GROUP

#: 枠連の組の確率のもと（最初の列は推定の出発点に使う、その券種自身の市場）。
BRACKET_FEATURES: tuple[str, ...] = ("log_own", "log_quinella", "log_trifecta", "log_harville")
_FLOOR = 1e-9


class BracketFeatures:
    """馬連の組の表（``combos/quinella_<年>.parquet`` の列 ``rid``・``h1``・``h2``・``q``・``t``・``hv``・``payout`` 以外のレースの列）と、
    枠番（``BracketSource.frames``）・枠連の確定オッズと払戻（``BracketSource.odds``・``payouts``）から、1行 = 1つの枠の組の表を作る。

    - 馬連の組の q（馬連のオッズから見た市場）・t（3連単から見た市場）・hv（モデルの Harville）を、その2頭の枠の組（小さい枠が先）ごとに足す。
    - ``own`` は枠連のオッズの逆数をレースで合計 1 にそろえた値。オッズの無い組（無投票・発売なし）は落とす。
    - ``top`` は ◎ の馬の枠、``h1``・``h2`` は枠の組（``h1 ≦ h2``）。
    例: 1枠に 1・2番、8枠に 15・16番なら、枠の組 1-8 の q は、1-15・1-16・2-15・2-16 の q の和。
    """

    def build(self, quinella: pd.DataFrame, frames: pd.DataFrame, odds: pd.DataFrame, payouts: pd.DataFrame,
              kinds: pd.DataFrame) -> pd.DataFrame:
        frame_of = frames.assign(race_id=frames["race_id"].astype(str)).set_index(["race_id", "horse_no"])["frame"]
        pairs = quinella.assign(race_id=quinella["rid"].astype(str))
        one = frame_of.reindex(pd.MultiIndex.from_arrays([pairs["race_id"], pairs["h1"].astype(int)])).to_numpy()
        two = frame_of.reindex(pd.MultiIndex.from_arrays([pairs["race_id"], pairs["h2"].astype(int)])).to_numpy()
        top = frame_of.reindex(pd.MultiIndex.from_arrays([pairs["race_id"], pairs["top"].fillna(0).astype(int)])).to_numpy()
        pairs = pairs.assign(f1=np.fmin(one, two), f2=np.fmax(one, two), top_frame=top).dropna(subset=["f1", "f2"])
        grouped = pairs.groupby(["race_id", "f1", "f2"], as_index=False).agg(
            q=("q", "sum"), t=("t", "sum"), hv=("hv", "sum"), race_date=("race_date", "first"), fold=("fold", "first"),
            expectation=("expectation", "first"), top=("top_frame", "first"))
        grouped["combo"] = grouped["f1"].astype(int).astype(str) + grouped["f2"].astype(int).astype(str)
        board = odds.assign(race_id=odds["race_id"].astype(str))
        table = grouped.merge(board, on=["race_id", "combo"], how="inner")
        inverse = 1.0 / table["odds"]
        table["log_own"] = np.log((inverse / inverse.groupby(table["race_id"]).transform("sum")).clip(lower=_FLOOR))
        table["log_quinella"] = np.log(table["q"].clip(lower=_FLOOR))
        table["log_trifecta"] = np.log(table["t"].clip(lower=_FLOOR))
        table["log_harville"] = np.log(table["hv"].clip(lower=_FLOOR))
        paid = payouts.assign(race_id=payouts["race_id"].astype(str))[["race_id", "combo", "payout"]]
        table = table.merge(paid, on=["race_id", "combo"], how="left")
        table["payout"] = table["payout"].fillna(0.0).astype(float)
        table["hit"] = table["payout"] > 0
        table = table.rename(columns={"f1": "h1", "f2": "h2"}).astype({"h1": int, "h2": int})
        table = table.merge(kinds[["race_id", KIND_GROUP, *KIND_DUMMIES]], on="race_id", how="inner")
        columns = ["race_id", "race_date", "fold", "expectation", "top", "h1", "h2", "combo", "odds", "payout", "hit",
                   *BRACKET_FEATURES, KIND_GROUP, *KIND_DUMMIES]
        return table[columns].sort_values("race_id", kind="stable").reset_index(drop=True)
