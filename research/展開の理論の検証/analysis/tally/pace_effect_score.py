"""ペースによって、前と後ろの有利・不利がどれだけ入れ替わるか（展開の効き目）。"""

from __future__ import annotations

import pandas as pd

from ..pace import HIGH, MIDDLE, SLOW
from .performance_tally import PerformanceTally
from .style_variant import StyleVariant

#: 出力の列。
COLUMNS: tuple[str, ...] = (
    "前−後ろ 複勝率 スロー", "前−後ろ 複勝率 ミドル", "前−後ろ 複勝率 ハイ", "効き目（複勝率）",
    "前−後ろ オッズとの差 スロー", "前−後ろ オッズとの差 ハイ", "効き目（オッズとの差）",
)


class PaceEffectScore:
    """区分の列 ``pace_column`` と脚質の分け方 ``variant`` について、前と後ろの差がペースでどれだけ変わるかを出す。

    - 前−後ろ 複勝率: 前（``variant.front``）の複勝率 − 後ろ（``variant.back``）の複勝率（ポイント）。
    - 効き目（複勝率）= スローでの差 − ハイでの差。理論どおりならプラスで、大きいほどペースが有利・不利を分けている。
      例: スローで前が 20ポイント上、ハイで 10ポイント上なら、効き目は 10。
    - オッズとの差の版は、勝率 − オッズから見た勝率 で同じことをする（馬の力の違いを差し引いた見方）。
    """

    def __init__(self) -> None:
        self._tally = PerformanceTally()

    def score(self, runners: pd.DataFrame, pace_column: str, variant: StyleVariant) -> dict[str, float]:
        side = pd.Series(pd.NA, index=runners.index, dtype="string")
        side = side.mask(runners[variant.name].isin(variant.front), "前").mask(runners[variant.name].isin(variant.back), "後ろ")
        table = self._tally.tally(runners.assign(_side=side), [pace_column, "_side"])
        place = table["複勝率"].unstack("_side").reindex(columns=["前", "後ろ"])
        market = table["勝率とオッズの差"].unstack("_side").reindex(columns=["前", "後ろ"])
        place_gap = (place["前"] - place["後ろ"]).reindex([SLOW, MIDDLE, HIGH])
        market_gap = (market["前"] - market["後ろ"]).reindex([SLOW, MIDDLE, HIGH])
        values = (place_gap[SLOW], place_gap[MIDDLE], place_gap[HIGH], place_gap[SLOW] - place_gap[HIGH],
                  market_gap[SLOW], market_gap[HIGH], market_gap[SLOW] - market_gap[HIGH])
        return dict(zip(COLUMNS, values))
