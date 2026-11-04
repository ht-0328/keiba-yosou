"""3連単（1着→2着→3着の並び）と 3連複（3頭の組）の全部の組の確率を、馬ごとの勝つ力から Harville の式で出す。"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

_FLOOR = 1e-9
COMBO_COLUMNS: tuple[str, ...] = ("first", "second", "third", "probability")


@dataclass(frozen=True)
class HarvilleCombos:
    """1レースの勝つ力（勝率。合計 1 にそろえる）から、組の確率を出す。

    3連単: P(a, b, c) = w_a × w_b ÷ (1 − w_a) × w_c ÷ (1 − w_a − w_b)。
    3連複: 3頭の 6 通りの並びの確率の和。組は馬番の小さい順に並べる。
    ``horses`` に ``first_strength`` があれば、1着（w_a）だけその値を使い、2着・3着の条件つきの確率は ``strength`` で出す。
    """

    def combos(self, horses: pd.DataFrame) -> pd.DataFrame:
        """3連単。``horses`` は1レースぶん（``horse_no``・``strength``）。戻りは ``first``・``second``・``third``・``probability``。"""
        numbers = horses["horse_no"].to_numpy(dtype=int)
        w = horses["strength"].to_numpy(dtype=float)
        w = w / max(w.sum(), _FLOOR)
        n = len(w)
        if n < 3:
            return pd.DataFrame(columns=COMBO_COLUMNS)
        win = w if "first_strength" not in horses.columns else horses["first_strength"].to_numpy(dtype=float)
        win = win / max(win.sum(), _FLOOR)
        second = w[None, :] / np.clip(1.0 - w[:, None], _FLOOR, None)                 # [a, b]
        rest = np.clip(1.0 - w[:, None, None] - w[None, :, None], _FLOOR, None)       # [a, b, 1]
        prob = win[:, None, None] * second[:, :, None] * (w[None, None, :] / rest)    # [a, b, c]
        a, b, c = np.meshgrid(np.arange(n), np.arange(n), np.arange(n), indexing="ij")
        distinct = (a != b) & (b != c) & (a != c)
        return pd.DataFrame({
            "first": numbers[a[distinct]], "second": numbers[b[distinct]], "third": numbers[c[distinct]],
            "probability": prob[distinct],
        })

    def trios(self, horses: pd.DataFrame) -> pd.DataFrame:
        """3連複。3連単の並びを馬番の小さい順にそろえて足し合わせる。"""
        ordered = self.combos(horses)
        if ordered.empty:
            return ordered
        sorted_numbers = np.sort(ordered[["first", "second", "third"]].to_numpy(), axis=1)
        trio = pd.DataFrame({"first": sorted_numbers[:, 0], "second": sorted_numbers[:, 1], "third": sorted_numbers[:, 2],
                             "probability": ordered["probability"].to_numpy()})
        return trio.groupby(["first", "second", "third"], as_index=False)["probability"].sum()

    def all_races(self, horses: pd.DataFrame, *, trio: bool = False) -> pd.DataFrame:
        """``horses`` は複数レース（``race_id``・``horse_no``・``strength``）。レースごとに出してつなぐ。"""
        maker = self.trios if trio else self.combos
        parts = []
        for race_id, group in horses.groupby("race_id", sort=False):
            table = maker(group)
            table.insert(0, "race_id", race_id)
            parts.append(table)
        if not parts:
            return pd.DataFrame(columns=["race_id", *COMBO_COLUMNS])
        return pd.concat(parts, ignore_index=True)
