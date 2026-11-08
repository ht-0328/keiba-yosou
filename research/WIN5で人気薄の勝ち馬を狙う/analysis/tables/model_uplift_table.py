"""今のモデルが人気薄をどう見ていたかの表: 上乗せの帯ごとの勝った数と、市場・今のモデルが見た数、勝った人気薄のモデルの中の順位。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from 共通.render import Table

from .cells import percent, ratio

_UPLIFT_EDGES = [0.0, 0.6, 0.8, 1.0, 1.2, 1.5, 100.0]
_UPLIFT_LABELS = ["〜0.6", "0.6〜0.8", "0.8〜1.0", "1.0〜1.2", "1.2〜1.5", "1.5〜"]
_RANK_EDGES = [0, 3, 5, 8, 12, 18]
_RANK_LABELS = ["1〜3位", "4〜5位", "6〜8位", "9〜12位", "13位〜"]


@dataclass(frozen=True)
class ModelUpliftTable:
    """``longshots`` は人気薄の馬の行（今のモデルの予測のある行だけを使う）。"""

    def build(self, longshots: pd.DataFrame, scope: str) -> list[Table]:
        known = longshots.loc[longshots["model"].notna()]
        return [self._uplift(known, scope), self._rank(known, scope)]

    def _uplift(self, known: pd.DataFrame, scope: str) -> Table:
        band = pd.cut(known["uplift"], _UPLIFT_EDGES, labels=_UPLIFT_LABELS)
        grouped = known.assign(band=band, won=known["finish"] == 1).groupby("band", observed=True)
        summary = grouped.agg(n=("won", "size"), won=("won", "sum"), market=("market", "sum"), model=("model", "sum"))
        rows = [[str(label), int(r.n), int(r.won), f"{r.market:.1f}", f"{r.model:.1f}", ratio(r.won, r.market), ratio(r.won, r.model)]
                for label, r in summary.iterrows()]
        return Table(["上乗せ（今のモデル ÷ オッズから見た勝率）", "頭数", "勝った", "市場が見た数", "今のモデルが見た数", "実際 ÷ 市場", "実際 ÷ 今のモデル"],
                     rows, title=f"今のモデルの上乗せの帯ごとの人気薄の勝ち（{scope}）")

    def _rank(self, known: pd.DataFrame, scope: str) -> Table:
        winners = known.loc[known["finish"] == 1]
        band = pd.cut(winners["model_rank"], _RANK_EDGES, labels=_RANK_LABELS)
        counts = band.value_counts().reindex(_RANK_LABELS, fill_value=0)
        rows = [[label, int(n), percent(n, len(winners))] for label, n in counts.items()]
        return Table(["今のモデルの1着の確率のレースの中の順位", "勝った人気薄の数", "割合"], rows,
                     title=f"勝った人気薄に今のモデルが付けた順位（{scope}）")
