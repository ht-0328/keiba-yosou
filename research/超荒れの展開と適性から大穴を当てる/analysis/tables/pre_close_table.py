"""確定の人気と締め切り前の人気で、大穴が1着のレースの数がどれだけ違うかの表（締め切り前の断面のある 2025年から）。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from .cells import percent

_NOTE = ("締め切り前の人気 = 元DB に残る締め切り前の単勝オッズ（データ区分 1〜3）のいちばん新しい断面の人気順。"
         "元DB に断面が残るのは 2025年からなので、それより前は数えられない。")


@dataclass(frozen=True)
class PreCloseTable:
    """``races``（``RaceTable``）のうち締め切り前の断面のあるレースで、確定の人気・締め切り前の人気それぞれで数えた大穴1着。"""

    def build(self, races: pd.DataFrame, title: str) -> Table:
        known = races.loc[races["pre_close_longshot_won"].notna()]
        final = known["longshot_won"].astype(bool)
        early = known["pre_close_longshot_won"].astype(bool)
        n = len(known)
        rows = [
            ["確定の人気で大穴が1着", int(final.sum()), percent(final.sum(), n)],
            ["締め切り前の人気で大穴が1着", int(early.sum()), percent(early.sum(), n)],
            ["両方で大穴が1着", int((final & early).sum()), percent((final & early).sum(), n)],
            ["確定だけで大穴（締め切り前は9番人気以内）", int((final & ~early).sum()), percent((final & ~early).sum(), n)],
            ["締め切り前だけで大穴（確定では9番人気以内）", int((~final & early).sum()), percent((~final & early).sum(), n)],
        ]
        return Table(["数え方", "レース数", f"割合（{n}レースのうち）"], rows, title=title, note=_NOTE)
