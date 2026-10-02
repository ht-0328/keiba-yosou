"""結果として、どんな馬を買うことになるか（出走頭数・人気・単勝オッズの帯ごと）。"""

from __future__ import annotations

import pandas as pd

from .payback import STAKE

#: 出走頭数の帯（下限を含み、上限を含まない）。
FIELD_BANDS = [(0, 9, "8頭以下"), (9, 13, "9〜12頭"), (13, 16, "13〜15頭"), (16, 99, "16頭以上")]
#: 人気の帯。
POPULARITY_BANDS = [(1, 4, "1〜3番人気"), (4, 7, "4〜6番人気"), (7, 10, "7〜9番人気"), (10, 99, "10番人気以下")]
#: 単勝オッズの帯（倍）。
ODDS_BANDS = [(0, 10, "10倍未満"), (10, 30, "10〜30倍"), (30, 50, "30〜50倍"), (50, 100000, "50倍以上")]


class BoughtHorseProfile:
    """買った馬券を帯で分けた、点数・割合・的中率・回収率の表。

    入力: ``evaluated``（予測した全頭。列 rid・horse_no・win_odds）と ``bought``（買った馬券。列 rid・horse_no・place_payout）。
    出走頭数と人気は ``evaluated`` から数える（予測した全頭がそのレースの出走馬）。
    """

    def tables(self, evaluated: pd.DataFrame, bought: pd.DataFrame) -> dict[str, pd.DataFrame]:
        horses = self._with_field_and_popularity(evaluated)
        merged = bought[["rid", "horse_no", "place_payout"]].merge(horses, on=["rid", "horse_no"], how="left")
        return {
            "出走頭数": self._banded(merged, "field", FIELD_BANDS),
            "人気": self._banded(merged, "popularity", POPULARITY_BANDS),
            "単勝オッズ": self._banded(merged, "win_odds", ODDS_BANDS),
        }

    @staticmethod
    def _with_field_and_popularity(evaluated: pd.DataFrame) -> pd.DataFrame:
        horses = evaluated[["rid", "horse_no", "win_odds"]].copy()
        horses["field"] = horses.groupby("rid")["horse_no"].transform("size")
        horses["popularity"] = horses.groupby("rid")["win_odds"].rank(method="min")
        return horses

    @staticmethod
    def _banded(merged: pd.DataFrame, column: str, bands: list[tuple]) -> pd.DataFrame:
        labels = [label for _, _, label in bands]
        edges = [low for low, _, _ in bands] + [bands[-1][1]]
        band = pd.cut(merged[column], bins=edges, labels=labels, right=False)
        grouped = merged.groupby(band, observed=False)["place_payout"]
        bets = grouped.size()
        table = pd.DataFrame({
            "点数": bets,
            "割合": (bets / max(len(merged), 1)).round(3),
            "的中率": grouped.apply(lambda payout: (payout > 0).mean() if len(payout) else 0.0).round(3),
            "回収率": (grouped.sum() / (bets * STAKE).where(bets > 0)).round(3),
        })
        return table.reset_index().rename(columns={column: "帯"})
