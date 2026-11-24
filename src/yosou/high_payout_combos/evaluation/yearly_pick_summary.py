"""買い目の決まりで選んだ組の、年ごとの成績。"""

from __future__ import annotations

import pandas as pd

from ..betting import HighPayoutRule
from ..dataset.column_names import HIT, PAYOUT, RACE_DATE, RACE_ID

#: 出す列。点数（買った組の数）・的中数・買ったレースの数・回収率（%）。
YEAR, POINTS, HITS, RACES, RETURN_RATE = "年", "点数", "的中数", "買ったレース", "回収率%"
COLUMNS: tuple[str, ...] = (YEAR, POINTS, HITS, RACES, RETURN_RATE)
#: 全部の年を合わせた行の、年の欄。
ALL_YEARS = "合計"
#: 1点の金額（円）。払戻は 100円あたりで持っている。
_STAKE_YEN = 100


class YearlyPickSummary:
    """年ごとの予測（``PredictionStore.load``）から、買い目の決まりで選んだ組を全部 100円ずつ買ったときの成績を、年ごとに数える。

    回収率 = 払戻の合計 ÷（点数 × 100円）× 100。例: 200点買って払戻の合計が 21,000円なら 105%。
    戻り値は1行 = 1年（古い順）と、最後に合計の行。列は ``COLUMNS``。
    """

    def __init__(self, rule: HighPayoutRule) -> None:
        self._rule = rule

    def summarize(self, predictions: pd.DataFrame) -> pd.DataFrame:
        picked = self._rule.pick(predictions)
        years = pd.to_datetime(picked[RACE_DATE]).dt.year.rename(YEAR)
        by_year = [self._row(year, rows) for year, rows in picked.groupby(years)]
        return pd.DataFrame([*by_year, self._row(ALL_YEARS, picked)], columns=list(COLUMNS))

    def _row(self, year: int | str, picked: pd.DataFrame) -> dict[str, object]:
        points = len(picked)
        return_rate = picked[PAYOUT].sum() / (points * _STAKE_YEN) * 100 if points else float("nan")
        return {
            YEAR: year, POINTS: points, HITS: int(picked[HIT].sum()), RACES: int(picked[RACE_ID].nunique()),
            RETURN_RATE: round(float(return_rate), 1),
        }
