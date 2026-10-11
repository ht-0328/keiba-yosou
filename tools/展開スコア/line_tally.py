"""展開スコアを付けた過去の出走を、線・年・分位・人気帯で数える。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.development_score import names

#: 確かめる線（3着以内の確率のポイント）。
CANDIDATE_LINES: tuple[float, ...] = (0.01, 0.015, 0.02, 0.03, 0.04, 0.05)
#: 分位の数。
DECILES = 10
#: 人気帯（下限, 上限）。
POPULARITY_BANDS: tuple[tuple[int, int], ...] = ((1, 3), (4, 6), (7, 9), (10, 18))
#: 数えた表の列。
GAP, PLACE_PAYBACK, WIN_PAYBACK = "差", "複勝回収率", "単勝回収率"


class LineTally:
    """1行 = 1頭の表（``展開スコア``・``3着以内``・``市場から見た3着以内率``・``popularity``・``place_payout``・``win_payout``・``race_date``）を数える。

    「差」= 実際の3着以内率 − 市場から見た3着以内率（ポイント）。プラスなら、市場の見立てより来ている。
    回収率は 100円ずつ買ったときの払戻の割合（%）。どれも展開スコアの無い行は数えない。
    """

    def __init__(self, scored: pd.DataFrame) -> None:
        self._rows = scored[scored[names.SCORE].notna()].reset_index(drop=True)

    def __len__(self) -> int:
        return len(self._rows)

    def correlation(self) -> float:
        """展開スコアと「3着以内 − 市場から見た3着以内率」の相関。"""
        rows = self._rows
        return float(rows[names.SCORE].corr(rows[names.TOP3] - rows[names.MARKET_TOP3]))

    def by_line(self) -> pd.DataFrame:
        """線ごとの、展開有利（線以上）と展開不利（−線以下）の頭数・差・複勝回収率と、差の向きが合っていた年の数。"""
        return pd.DataFrame([{"線": f"±{line:g}", **self._side("有利", self._rows[names.SCORE] >= line, positive=True),
                              **self._side("不利", self._rows[names.SCORE] <= -line, positive=False)} for line in CANDIDATE_LINES])

    def by_year(self, line: float) -> pd.DataFrame:
        """``line`` での、年ごとの頭数・差・複勝回収率。"""
        years = self._rows["race_date"].dt.year
        rows = []
        for year in sorted(years.unique()):
            rows.append({"年": int(year), "頭数": int((years == year).sum()),
                         **self._side("有利", (years == year) & (self._rows[names.SCORE] >= line)),
                         **self._side("不利", (years == year) & (self._rows[names.SCORE] <= -line))})
        return pd.DataFrame(rows)

    def by_decile(self) -> pd.DataFrame:
        """展開スコアの 10分位ごとの頭数・平均・3着以内率・市場・差・回収率（分位 1 がいちばん低い）。"""
        rows = self._rows
        decile = pd.qcut(rows[names.SCORE].rank(method="first"), DECILES, labels=range(1, DECILES + 1))
        grouped = rows.groupby(decile, observed=True)
        return pd.DataFrame({
            "分位": grouped.size().index.astype(int), "頭数": grouped.size().to_numpy(),
            "展開スコアの平均": grouped[names.SCORE].mean().round(4).to_numpy(),
            "展開スコアの最小": grouped[names.SCORE].min().round(4).to_numpy(),
            "3着以内率": (grouped[names.TOP3].mean() * 100).round(1).to_numpy(),
            "市場から見た3着以内率": (grouped[names.MARKET_TOP3].mean() * 100).round(1).to_numpy(),
            GAP: ((grouped[names.TOP3].mean() - grouped[names.MARKET_TOP3].mean()) * 100).round(2).to_numpy(),
            PLACE_PAYBACK: grouped["place_payout"].mean().round(1).to_numpy(),
            WIN_PAYBACK: grouped["win_payout"].mean().round(1).to_numpy(),
        })

    def by_popularity(self, line: float) -> pd.DataFrame:
        """``line`` での、人気帯ごとの頭数・差・複勝回収率。"""
        popularity = pd.to_numeric(self._rows["popularity"], errors="coerce")
        rows = []
        for low, high in POPULARITY_BANDS:
            band = (popularity >= low) & (popularity <= high)
            rows.append({"人気": f"{low}〜{high}番人気", "頭数": int(band.sum()),
                         **self._side("有利", band & (self._rows[names.SCORE] >= line)),
                         **self._side("不利", band & (self._rows[names.SCORE] <= -line))})
        return pd.DataFrame(rows)

    def _side(self, name: str, picked: pd.Series, positive: bool | None = None) -> dict[str, object]:
        rows = self._rows[picked]
        count = len(rows)
        gap = (rows[names.TOP3].mean() - rows[names.MARKET_TOP3].mean()) * 100 if count else np.nan
        values = {f"{name}_頭数": count, f"{name}_3着以内率": round(rows[names.TOP3].mean() * 100, 1) if count else np.nan,
                  f"{name}_市場": round(rows[names.MARKET_TOP3].mean() * 100, 1) if count else np.nan,
                  f"{name}_{GAP}": round(gap, 2) if count else np.nan,
                  f"{name}_{PLACE_PAYBACK}": round(rows["place_payout"].mean(), 1) if count else np.nan}
        if positive is not None:
            values[f"{name}_向きの合った年"] = self._years_with_sign(rows, positive)
        return values

    def _years_with_sign(self, rows: pd.DataFrame, positive: bool) -> str:
        """年ごとの差の向きが、期待した向き（有利はプラス・不利はマイナス）だった年の数 / 年の数。"""
        if rows.empty:
            return "0 / 0"
        yearly = rows.groupby(rows["race_date"].dt.year).apply(lambda part: part[names.TOP3].mean() - part[names.MARKET_TOP3].mean())
        matched = int((yearly > 0).sum() if positive else (yearly < 0).sum())
        return f"{matched} / {len(yearly)}"
