"""人気帯ごとに、危険度が線以上の馬の成績を、人気帯の全体と比べる表を作る。"""

from __future__ import annotations

import pandas as pd

from yosou.favorites_out_of_top3.dataset import FavoriteBand

from 共通.perf import PERF_COLUMNS
from 共通.render import Table

from 印の成績.perf_rows import perf_row_of

#: 区切りごとに全体と比べる回収率（成績7つの列の名前と、払戻の列）。
_PAYOUTS: tuple[tuple[str, str], ...] = (("単勝回収率", "win_payout"), ("複勝回収率", "place_payout"))


def _cells(rows: pd.DataFrame) -> list[str]:
    """成績7つのセル。馬がいなければ、頭数 0 と空の成績。"""
    if rows.empty:
        return ["0", "0-0-0-0", *["—"] * (len(PERF_COLUMNS) - 2)]
    return perf_row_of(rows).cells()


class DangerBandReport:
    """印を付けた表（``BacktestMarker.mark``。人気馬の行に ``favorite_band``・``over_line`` 付き）から、人気帯ごとに
    「危険度が線以上の馬」「線未満の馬」「人気帯の全体」の成績を並べる表（表12）を作る。

    印に使うかどうか（``is_danger``）によらず、どの人気帯も線以上かで分ける。「全体を下回った区切り」は、7つの区切りのうち、
    線以上の馬の回収率がその区切りの人気帯の全体より低かった数。危険と判定した馬が「買う価値の低い馬」になっているかを見る
    （人気馬の予想の設計書 16 の 3）。
    """

    def table(self, marked: pd.DataFrame) -> Table:
        favorites = marked[marked["favorite_band"].notna()] if "favorite_band" in marked.columns else marked.iloc[0:0]
        headers = ["人気帯", "区分", *PERF_COLUMNS, *(f"{name}が全体を下回った区切り" for name, _ in _PAYOUTS)]
        rows = []
        for band in FavoriteBand:
            inside = favorites[favorites["favorite_band"] == band.label]
            if inside.empty:
                continue
            over = inside["over_line"].astype(bool)
            rows.append([band.label, "線以上（危険）", *_cells(inside[over]), *self._below_counts(inside)])
            rows.append([band.label, "線未満", *_cells(inside[~over]), "", ""])
            rows.append([band.label, "全体", *_cells(inside), "", ""])
        return Table(headers, rows, title="12. 人気帯ごとの、危険度が線以上の馬の成績",
                     note="危険度 = 人気馬の予想の4着以下の確率 − オッズから見た4着以下の確率。線は区切りごと・人気帯ごとに、その区切りの検証期間で決めた値。"
                          "印に使う人気帯（--danger-bands）によらず、どの人気帯も線以上かで分けた。回収率は確定オッズの払戻で数えた。")

    def _below_counts(self, inside: pd.DataFrame) -> list[str]:
        """回収率ごとに「線以上の馬が、その区切りの人気帯の全体を下回った区切りの数 / 区切りの数」。"""
        cells = []
        for _, payout in _PAYOUTS:
            below = folds = 0
            for _, group in inside.groupby("fold", sort=True):
                flagged = group[group["over_line"].astype(bool)]
                if flagged.empty:
                    continue
                folds += 1
                below += int(flagged[payout].mean() < group[payout].mean())
            cells.append(f"{below} / {folds}")
        return cells
