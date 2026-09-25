"""判定ごとの成績の1行を作る。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from yosou.shared.dataset.column_names import PLACE_PAYOUT, WIN_PAYOUT

from ..dataset import IN_THE_MONEY, OUT_OF_THE_MONEY, WIN
from .rates import rate

#: 払戻は 100円あたりの金額。
_PAYOUT_UNIT = 100
#: 判定ごとの成績の列。
KIND_COLUMNS: tuple[str, ...] = ("判定", "頭数", "勝率", "複勝率", "馬券外率", "単勝回収率", "複勝回収率")


class KindSummary:
    """判定ごとの成績（勝率・複勝率・馬券外率と、単勝・複勝を 100円ずつ買ったとみなした回収率）の1行。

    判定がどれだけ着順を分けられているかを見るためのもので、掛け金の配分（``StakePlan``）は使わない。
    """

    def summarize(self, kind: str, rows: pd.DataFrame) -> list[Any]:
        return [kind, len(rows), rate(rows[WIN]), rate(rows[IN_THE_MONEY]), rate(rows[OUT_OF_THE_MONEY]),
                rate(rows[WIN_PAYOUT] / _PAYOUT_UNIT), rate(rows[PLACE_PAYOUT] / _PAYOUT_UNIT)]
