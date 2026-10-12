"""第1段: 選んだレースに、帯がどれだけ集まったかを数える（docs/01 の 4.3）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_DATE, RACE_ID

from .day_bootstrap import DayBootstrap
from .obi_rules import BIG, OBI
from .race_frame import PAYOUT_CLASS

#: 日ごとの量の列の名前。
_PICKED, _PICKED_OBI, _PICKED_WILD, _ALL, _ALL_OBI, _ALL_WILD = "選んだ", "選んだ帯", "選んだ荒れ", "全部", "全部の帯", "全部の荒れ"


class SelectionSummary:
    """選んだレース（``picked``）と、同じ期間の全レース（``races``）から、レース選びの物差しを1行にまとめる。

    - 帯の集まり方 = 選んだレースの帯の割合 ÷ 全レースの帯の割合（と、その 90% の幅）。
    - 帯の拾い方 = 全レースの帯のうち、選んだレースに入っていた割合。
    - 大荒れ以上（10万円以上）の集まり方も並べる。
    """

    def __init__(self, bootstrap: DayBootstrap | None = None) -> None:
        self._bootstrap = bootstrap or DayBootstrap()

    def row(self, picked: pd.DataFrame, races: pd.DataFrame) -> dict[str, object]:
        per_day = self._per_day(picked, races)
        totals = per_day.sum()
        low, high = self._bootstrap.interval(per_day, _obi_lift)
        years = races[RACE_DATE].dt.year.nunique()
        return {
            "選んだレース": int(totals[_PICKED]), "1年あたり": round(totals[_PICKED] / max(years, 1), 1),
            "選んだうちの帯": int(totals[_PICKED_OBI]), "選んだうちの大荒れ以上": int(totals[_PICKED_WILD]),
            "帯の割合": round(totals[_PICKED_OBI] / totals[_PICKED], 4), "全レースの帯の割合": round(totals[_ALL_OBI] / totals[_ALL], 4),
            "帯の集まり方": round(_obi_lift(totals), 2), "90%の幅（下）": round(low, 2), "90%の幅（上）": round(high, 2),
            "帯の拾い方": round(totals[_PICKED_OBI] / totals[_ALL_OBI], 3) if totals[_ALL_OBI] else float("nan"),
            "大荒れ以上の集まり方": round(_wild_lift(totals), 2),
        }

    def _per_day(self, picked: pd.DataFrame, races: pd.DataFrame) -> pd.DataFrame:
        flags = races[[RACE_DATE, RACE_ID]].assign(**{
            _PICKED: races[RACE_ID].isin(picked[RACE_ID]),
            _ALL_OBI: races[PAYOUT_CLASS].eq(OBI), _ALL_WILD: races[PAYOUT_CLASS].isin([OBI, BIG]), _ALL: True,
        })
        flags[_PICKED_OBI] = flags[_PICKED] & flags[_ALL_OBI]
        flags[_PICKED_WILD] = flags[_PICKED] & flags[_ALL_WILD]
        columns = [_PICKED, _PICKED_OBI, _PICKED_WILD, _ALL, _ALL_OBI, _ALL_WILD]
        return flags.groupby(RACE_DATE)[columns].sum().astype(float)


def _obi_lift(totals: pd.Series) -> float:
    picked_rate = totals[_PICKED_OBI] / totals[_PICKED] if totals[_PICKED] else float("nan")
    all_rate = totals[_ALL_OBI] / totals[_ALL] if totals[_ALL] else float("nan")
    return picked_rate / all_rate if all_rate else float("nan")


def _wild_lift(totals: pd.Series) -> float:
    picked_rate = totals[_PICKED_WILD] / totals[_PICKED] if totals[_PICKED] else float("nan")
    all_rate = totals[_ALL_WILD] / totals[_ALL] if totals[_ALL] else float("nan")
    return picked_rate / all_rate if all_rate else float("nan")
