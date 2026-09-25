"""判定した1番人気の束から、まとめの1行を作る。"""

from __future__ import annotations

from typing import Any

import pandas as pd

from yosou.shared.dataset.column_names import PLACE_PAYOUT, WIN_PAYOUT

from ..dataset import OUT_OF_THE_MONEY, WIN
from ..decision import DECISION, FADE, PLACE_ONLY, WIN_AND_PLACE
from .rates import percent, rate
from .stake_plan import StakePlan

#: まとめの列（設計書 16 の「3つの比べ方」）。
COLUMNS: tuple[str, ...] = (
    "1番人気", "消した数", "消した馬の馬券外率", "全体の馬券外率",
    "単勝も買った数", "単勝も買った馬の勝率", "全体の勝率",
    "買い分けの投資", "買い分けの回収率", "全部を単勝と複勝で買った回収率", "全部を複勝だけで買った回収率",
)


class DecisionSummary:
    """判定した1番人気の束（1年ぶん・1つの単位ぶん など）を、まとめの1行にする。

    - 消した1番人気の馬券外率が、全体の馬券外率より高いか（消しが当たっているか）。
    - 単勝も買った1番人気の勝率が、全体の勝率より高いか（単勝を足すのが当たっているか）。
    - 買い分けた回収率が、全部を同じ買い方で買った回収率より高いか。掛け金は ``StakePlan``。
    """

    def __init__(self, plan: StakePlan) -> None:
        self._plan = plan

    def summarize(self, rows: pd.DataFrame) -> dict[str, Any]:
        decisions = rows[DECISION]
        faded = rows[decisions == FADE]
        with_win = rows[decisions == WIN_AND_PLACE]
        invested = self._plan.invested(decisions).sum()
        return dict(zip(COLUMNS, (
            len(rows), len(faded), rate(faded[OUT_OF_THE_MONEY]), rate(rows[OUT_OF_THE_MONEY]),
            len(with_win), rate(with_win[WIN]), rate(rows[WIN]),
            f"{int(invested):,}円", self._recovery(decisions, rows),
            self._recovery(_all(decisions, WIN_AND_PLACE), rows), self._recovery(_all(decisions, PLACE_ONLY), rows),
        )))

    def _recovery(self, decisions: pd.Series, rows: pd.DataFrame) -> str:
        invested = self._plan.invested(decisions).sum()
        returned = self._plan.returned(decisions, rows[[WIN_PAYOUT, PLACE_PAYOUT]]).sum()
        return percent(returned / invested) if invested else ""


def _all(decisions: pd.Series, kind: str) -> pd.Series:
    """全部の行を同じ判定にした並び（比べる相手の買い方）。"""
    return pd.Series(kind, index=decisions.index)


