"""対象レース1つの予測の結果。"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pandas as pd

from yosou.shared.dataset import HORSE_NAME, HORSE_NO
from yosou.shared.feature.group import WIN_ODDS
from yosou.shared.workflow import WIN_PROBABILITY

from ..leg import EDGE, MARKET, SHARE, LegModelChoice

#: 記録に残す馬ごとの列。
_RECORDED: tuple[str, ...] = (HORSE_NO, HORSE_NAME, WIN_ODDS, WIN_PROBABILITY, SHARE, MARKET, EDGE)


@dataclass(frozen=True)
class LegForecast:
    """対象レースのレースID・使った確率と理由（``LegModelChoice``）・全頭の確率の表（``RaceWinShare`` の結果）。"""

    race_id: str
    choice: LegModelChoice
    table: pd.DataFrame

    def to_dict(self, picks: tuple[int, ...]) -> dict[str, Any]:
        """記録の形。``picks`` はこのレースの買い目の馬番。"""
        horses = [self._horse(row, picks) for row in self.table[list(_RECORDED)].to_dict("records")]
        return {
            "レースID": self.race_id, "使った確率": self.choice.model.label, "理由": self.choice.reason,
            "オッズの断面": self.choice.odds_announced_at, "買い目": list(picks), "馬": horses,
        }

    def _horse(self, row: dict[str, Any], picks: tuple[int, ...]) -> dict[str, Any]:
        values = {name: self._plain(value) for name, value in row.items()}
        return {**values, "買い目に入れたか": int(values[HORSE_NO]) in picks}

    def _plain(self, value: Any) -> Any:
        """JSON に書ける値（numpy の数は Python の数に、欠損値は None に）。"""
        plain = value.item() if hasattr(value, "item") else value
        return None if isinstance(plain, float) and math.isnan(plain) else plain
