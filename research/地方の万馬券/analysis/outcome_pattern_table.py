"""決着の型の表: 3連単の配当の帯ごとに、1〜3着が人気馬・中穴・大穴のどの帯から来たか（型）の割合。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from .payout_band import PAYOUT_BANDS
from .popularity_band import FAVORITE, LONGSHOT, MIDDLE

#: レースの表に付ける列。
PATTERN_ORDERED = "型（1着→3着）"
PATTERN_COUNTS = "型（順不同）"
COLUMNS: tuple[str, ...] = ("配当の帯", "型", "レース数", "帯の中の割合", "配当の中央値")
#: 表に出す最小の割合（細かい型は省く）。
_MIN_SHARE = 0.03


@dataclass(frozen=True)
class OutcomePatternTable:
    """``placed``（1〜3着の馬の行。``race_id``・``finish``・``band`` を持つ）と ``races``（``race_id``・``payout_band``・``trifecta_payout``）から、
    帯 × 型 の表を作る。型は「人中大」（1着→3着の順）と「人1中1大1」（順不同）の2つ。
    """

    def patterns(self, placed: pd.DataFrame) -> pd.DataFrame:
        """レースごとの型（2つの列）。1〜3着がそろわないレースは出さない。"""
        ordered = placed.sort_values(["race_id", "finish"]).groupby("race_id")["band"].agg(lambda bands: "".join(str(b) for b in bands))
        complete = ordered[ordered.str.len() == 3]
        return pd.DataFrame({
            PATTERN_ORDERED: complete,
            PATTERN_COUNTS: complete.map(_counts_label),
        }).reset_index()

    def build(self, races: pd.DataFrame, pattern_column: str, *, title: str) -> Table:
        """``races`` は ``patterns`` を merge 済みのレースの表。"""
        rows = []
        for band in PAYOUT_BANDS:
            rows.extend(self._band_rows(races[races["payout_band"] == band], band, pattern_column))
        return Table.from_records(rows, COLUMNS, title=title,
                                  note=f"帯の中の割合が {_MIN_SHARE:.0%} 以上の型だけ。配当は 3連単の払戻（100円あたり）。")

    def _band_rows(self, in_band: pd.DataFrame, band: str, pattern_column: str) -> list[dict]:
        total = len(in_band)
        if total == 0:
            return []
        grouped = in_band.groupby(pattern_column)["trifecta_payout"].agg(["size", "median"]).sort_values("size", ascending=False)
        rows = [{"配当の帯": band, "型": "全部", "レース数": total, "帯の中の割合": "100%", "配当の中央値": int(in_band["trifecta_payout"].median())}]
        for pattern, row in grouped.iterrows():
            share = row["size"] / total
            if share < _MIN_SHARE:
                continue
            rows.append({"配当の帯": band, "型": pattern, "レース数": int(row["size"]), "帯の中の割合": f"{share:.1%}",
                         "配当の中央値": int(row["median"])})
        return rows


def _counts_label(bands: str) -> str:
    """「人中大」のような並び → 「人1中1大1」。"""
    return f"人{bands.count(FAVORITE)}中{bands.count(MIDDLE)}大{bands.count(LONGSHOT)}"
