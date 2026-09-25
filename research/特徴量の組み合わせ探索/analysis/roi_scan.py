"""区分 × 馬の条件 × 人気帯 × 期間ごとに、全頭を単勝・複勝1点100円で買った結果を数える。"""

import numpy as np
import pandas as pd

from yosou.shared.feature.value_types import as_numbers

from .condition_bins import ConditionBins
from .popularity_bands import PopularityBands
from .race_segments import RaceSegments

#: 馬の条件を付けない（区分と人気帯だけの）行の条件名。
NO_CONDITION = "（馬の条件なし）"
PERIODS = ("見つける", "確かめる", "テスト")


class RoiScan:
    """段の組み合わせごとに groupby して、点数・払戻の合計・払戻の2乗の合計（ばらつきの計算用）を数える。"""

    def __init__(self, rows: pd.DataFrame, periods: pd.Series, segments: RaceSegments,
                 bands: PopularityBands) -> None:
        self._period = pd.Categorical(periods, categories=PERIODS).codes
        self._segments = segments
        self._bands = bands
        self._win = as_numbers(rows["win_payout"]).fillna(0).to_numpy() / 100
        self._place = as_numbers(rows["place_payout"]).fillna(0).to_numpy() / 100

    def run(self, conditions: list[ConditionBins]) -> pd.DataFrame:
        everyone = ConditionBins(NO_CONDITION, np.zeros(len(self._win), dtype=np.int64), {0: (NO_CONDITION, None)})
        tables = [
            self._count(segment_level, band_level, condition)
            for segment_level in self._segments.codes
            for band_level in ("全人気", "人気帯")
            for condition in (everyone, *conditions)
        ]
        return pd.concat(tables, ignore_index=True)

    def _count(self, segment_level: str, band_level: str, condition: ConditionBins) -> pd.DataFrame:
        frame = pd.DataFrame({
            "segment": self._segments.codes[segment_level], "band": self._bands.codes(band_level),
            "condition": condition.codes, "period": self._period,
            "win": self._win, "win_sq": self._win ** 2, "win_hit": self._win > 0,
            "place": self._place, "place_sq": self._place ** 2, "place_hit": self._place > 0,
        })
        frame = frame[(frame["band"] >= 0) & (frame["condition"] >= 0) & (frame["period"] >= 0)]
        sums = frame.groupby(["segment", "band", "condition", "period"], sort=False).agg(
            点数=("win", "size"), 単勝払戻=("win", "sum"), 単勝払戻2乗=("win_sq", "sum"), 単勝的中=("win_hit", "sum"),
            複勝払戻=("place", "sum"), 複勝払戻2乗=("place_sq", "sum"), 複勝的中=("place_hit", "sum"),
        ).reset_index()
        segment_labels = self._segments.labels[segment_level]
        band_labels = PopularityBands.labels(band_level)
        sums["区分の段"] = segment_level
        sums["区分"] = sums["segment"].map(lambda code: segment_labels[code][0])
        sums["区分の条件"] = sums["segment"].map(lambda code: segment_labels[code][1])
        sums["人気帯"] = sums["band"].map(lambda code: band_labels[code][0])
        sums["人気の範囲"] = sums["band"].map(lambda code: band_labels[code][1])
        sums["特徴量"] = condition.name
        sums["馬の条件"] = sums["condition"].map(lambda code: condition.labels[code][0])
        sums["馬の条件の値"] = sums["condition"].map(lambda code: condition.labels[code][1])
        sums["期間"] = sums["period"].map(dict(enumerate(PERIODS)))
        return sums.drop(columns=["segment", "band", "condition", "period"])
