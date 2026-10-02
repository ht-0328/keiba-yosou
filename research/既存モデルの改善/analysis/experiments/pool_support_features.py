"""券種ごとのオッズから見た支持と、単勝から見た値との比。"""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import pandas as pd

from yosou.shared.feature.odds import TOP2_RATE, TOP3_RATE, WIN_RATE, MarketPlaces

#: 券種の支持の列 → 比べる単勝から見た値の列（勝率・2着以内率・3着以内率）。
_COUNTERPARTS: dict[str, str] = {
    "3連単から見た勝率": WIN_RATE, "馬単から見た勝率": WIN_RATE,
    "3連複から見た3着以内率": TOP3_RATE, "馬連から見た2着以内率": TOP2_RATE,
    "ワイドから見た3着以内率": TOP3_RATE, "複勝から見た3着以内率": TOP3_RATE,
}
#: log を取るときの下限。
_FLOOR = 1e-6


def ratio_name(column: str) -> str:
    """特徴量の名前（例: 3連複から見た3着以内率と単勝の比（log））。"""
    return f"{column}と単勝の比（log）"


NAMES: tuple[str, ...] = tuple(ratio_name(column) for column in _COUNTERPARTS)


class PoolSupportFeatures:
    """券種ごとの確定オッズから見た馬ごとの支持と、単勝オッズから見た値（Harville の式）との比の log。

    例: 単勝から見た3着以内率 0.20 の馬が、3連複から見ると 0.26 なら、log(0.26 ÷ 0.20) ≒ +0.26。売上の大きい券種で
    単勝より高く評価されている馬を表す（既存モデルの修正計画の 2「券種ごとのオッズ」）。オッズがそろうのは当日。
    ``runners`` は1頭ごとの表（race_id・horse_id・horse_no・win_odds）、``supports`` は券種ごとの支持の表の並び。
    """

    def build(self, runners: pd.DataFrame, supports: Sequence[pd.DataFrame]) -> pd.DataFrame:
        """列は race_id・horse_id と ``NAMES``。"""
        places = MarketPlaces().of(runners[["race_id", "win_odds"]])
        table = pd.concat([runners[["race_id", "horse_id", "horse_no"]], places], axis=1)
        merged = table
        for support in supports:
            merged = merged.merge(support, on=["race_id", "horse_no"], how="left")
        ratios = {ratio_name(column): self._log_ratio(merged, column, base) for column, base in _COUNTERPARTS.items()}
        return pd.DataFrame({"race_id": merged["race_id"], "horse_id": merged["horse_id"], **ratios})

    def _log_ratio(self, merged: pd.DataFrame, column: str, base: str) -> pd.Series:
        if column not in merged.columns:
            return pd.Series(np.nan, index=merged.index)
        return np.log(merged[column].clip(lower=_FLOOR) / merged[base].clip(lower=_FLOOR))
