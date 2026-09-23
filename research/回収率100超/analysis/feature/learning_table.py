"""学習に渡す特徴量の列を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..market import SternProbabilities
from .market_excess_rate import MarketExcessRate
from .pool_features import PoolFeatures

#: 券種プールから取り出した、馬ごとの確率の列。
POOL_COLUMNS: tuple[str, ...] = (
    "3連単から見た勝率", "馬単から見た勝率", "3連複から見た3着以内率", "馬連から見た2着以内率",
    "複勝から見た3着以内率", "ワイドから見た3着以内率", "単勝票数の配分", "複勝票数の配分",
    "3連単の2着率", "3連単の3着率", "馬単の2着率",
)
#: 市場の基準になる2つの確率（単勝オッズだけから作る）。
WIN_BASELINE = "単勝から見た勝率"
PLACE_BASELINE = "単勝から見た複勝率"
#: JRA-VAN のマイニング予想から作る列。
MINING_COLUMNS: tuple[str, ...] = (
    "予想タイムの順位", "予想タイムの偏差", "対戦スコアの順位", "対戦スコアの偏差",
    "予想の信頼度＋", "予想の信頼度−",
)
#: 事実表から使う数値の列（馬の実力）。カテゴリはそのまま渡さない。
HORSE_COLUMNS: tuple[str, ...] = (
    "frame_no", "age", "carried", "body_weight", "weight_change", "distance_m", "class_order",
    "prev_finish", "prev_popularity", "interval_days", "prev_last3f", "prev_last3f_rank",
    "prev_time_diff", "prev_corner4", "prev_field_size", "prev_distance_m",
    "runs_before", "wins_before", "lead_runs_before", "course_runs_before", "course_wins_before",
    "best_time_unit", "best_time_unit_rank", "best_time_dist", "best_time_dist_rank",
)
#: 市場の期待に対する超過成績を作る区分（作る列名 → 元の列）。
EXCESS_GROUPS: dict[str, str] = {
    "騎手の超過複勝率": "jockey_code", "調教師の超過複勝率": "trainer_code",
    "父の超過複勝率": "sire", "母父の超過複勝率": "damsire",
}


class LearningTable:
    """出走の表に特徴量の列を足し、モデルに渡す列名を返す。

    モデルに渡すのは「市場が何と言っているか」と「馬の実力」の2つだけで、結果は渡さない。
    市場の側が主で、馬の実力は補いである。実測では、市場の列だけで市場に勝つ分の 8割が説明できた。
    """

    def __init__(self, stern: SternProbabilities) -> None:
        self._stern = stern

    def build(self, runners: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
        """（表, 特徴量の列名）を返す。"""
        table = self._add_market_place_rate(runners)
        table, market_columns = PoolFeatures(POOL_COLUMNS, WIN_BASELINE, PLACE_BASELINE).add_to(table)
        excess = MarketExcessRate()
        for name, column in EXCESS_GROUPS.items():
            if column in table.columns:
                table[name] = excess.build(table, column, "placed", PLACE_BASELINE)
        features = (market_columns + list(MINING_COLUMNS) + list(EXCESS_GROUPS)
                    + list(HORSE_COLUMNS) + ["field", "place_places"])
        return table, [column for column in features if column in table.columns]

    def _add_market_place_rate(self, runners: pd.DataFrame) -> pd.DataFrame:
        """単勝オッズだけから作った複勝率を足す（Stern 補正つき Harville）。

        複勝の対象着順は、5〜7頭立てなら2着まで、8頭以上なら3着までになる。
        頭数によらず3着以内で計算すると、少頭数のレースで確率を高く見積もりすぎる。
        """
        table = runners.sort_values(["rid", "horse_no"]).reset_index(drop=True)
        index = pd.factorize(table["rid"], sort=False)[0]
        starts = np.searchsorted(index, np.arange(index.max() + 1))
        ends = np.append(starts[1:], len(table))
        market = table[WIN_BASELINE].to_numpy()
        places = table["place_places"].to_numpy()
        rate = np.empty(len(table))
        for begin, end in zip(starts, ends, strict=True):
            probability = market[begin:end] / market[begin:end].sum()
            rate[begin:end] = (self._stern.top_three(probability) if places[begin] == 3
                               else self._stern.quinella(probability).sum(axis=1))
        table[PLACE_BASELINE] = np.clip(rate, 1e-9, 1.0)
        return table
