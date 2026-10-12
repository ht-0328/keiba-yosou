"""第1段: 点数ごとに、同じレース数を選んだときに実際に 1,000倍以上だった割合を並べる（docs/06 の 2）。"""

from __future__ import annotations

import pandas as pd
from sklearn.metrics import roc_auc_score

from yosou.shared.dataset import RACE_DATE

from .obi_rules import BIG_YEN
from .race_table_loader import TRIFECTA_YEN

#: 1開催日あたり何レース選ぶか（上から順に）。線で選ぶ本番の既定（0.40）は、およそ 2.5レース/日に当たる。
PER_DAY_COUNTS: tuple[float, ...] = (8.0, 5.0, 2.5, 1.0)
#: 表の列の名前。
SCORE = "点数"


class SelectionPrecision:
    """レースごとの点数の列（``columns``）ごとに、点数の高い順に「1開催日あたり n レース」ぶん選んだときの、
    実際に 3連単が 1,000倍以上で決まった割合を1行にまとめる。点数の並べ方の良さ（AUC）も添える。

    選ぶ数を同じにして比べるのは、線の値はモデルごとに意味が違い、同じ線では選ぶ数が変わって比べられないため。
    点数の無いレースは、その点数の行では数えない。
    """

    def __init__(self, per_day_counts: tuple[float, ...] = PER_DAY_COUNTS) -> None:
        self._per_day_counts = per_day_counts

    def table(self, races: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
        wild = races[TRIFECTA_YEN].ge(BIG_YEN)
        days = races[RACE_DATE].nunique()
        rows = [self._row(races.assign(**{"_wild": wild}), column, days) for column in columns if column in races.columns]
        return pd.DataFrame(rows)

    def _row(self, races: pd.DataFrame, column: str, days: int) -> dict[str, object]:
        scored = races[races[column].notna()].sort_values(column, ascending=False)
        row: dict[str, object] = {SCORE: column, "点数のあるレース": len(scored)}
        for per_day in self._per_day_counts:
            chosen = scored.head(int(per_day * days))
            row[f"{per_day:g}レース/日（{len(chosen)}）"] = round(float(chosen["_wild"].mean()), 3) if len(chosen) else float("nan")
        row["AUC"] = round(float(roc_auc_score(scored["_wild"], scored[column])), 4) if scored["_wild"].nunique() == 2 else float("nan")
        return row
