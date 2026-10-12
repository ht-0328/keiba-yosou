"""第3段: 精算した買い目から、買い方ごとの成績を1行にまとめる（docs/01 の 9）。"""

from __future__ import annotations

import pandas as pd

from yosou.shared.dataset import RACE_DATE, RACE_ID

from .day_bootstrap import DayBootstrap
from .obi_rules import OBI_YEN
from .ticket_maker import STAKE
from .ticket_settler import HIT, PAYOUT

#: 日ごとの量の列の名前。
_INVEST, _RETURN = "投資", "払戻"


class BettingSummary:
    """1つの買い方の精算した買い目（1行 = 1点）から、成績を1行の辞書にする。

    - 回収率と、その 90% の幅（開催日のブートストラップ）。
    - 帯の回数（1点の払戻が 100万円以上だった的中の数）と、最初の帯までの平均のレース数（買ったレース ÷ 帯の回数）。
    - いちばん大きい当たりを除いた回収率（数回の大当たりで回収率が大きく動くため。docs/01 の 8）。
    - いちばん深い落ち込み（通算の損益のいちばん高いところからの下がり幅）と、最大の連敗（払戻の無いレースが続いた数）。
    """

    def __init__(self, bootstrap: DayBootstrap | None = None) -> None:
        self._bootstrap = bootstrap or DayBootstrap()

    def row(self, settled: pd.DataFrame, years: int) -> dict[str, object]:
        if settled.empty:
            return {"買ったレース": 0}
        per_race = settled.groupby([RACE_DATE, RACE_ID]).agg(点数=(STAKE, "size"), 投資=(STAKE, "sum"), 払戻=(PAYOUT, "sum"),
                                                              的中=(HIT, "any")).reset_index()
        invest, payout = per_race[_INVEST].sum(), per_race[_RETURN].sum()
        obi_hits = int(settled[PAYOUT].ge(OBI_YEN).sum())
        low, high = self._bootstrap.interval(per_race.groupby(RACE_DATE)[[_INVEST, _RETURN]].sum(), _payback)
        races = len(per_race)
        return {
            "買ったレース": races, "1年あたりのレース": round(races / max(years, 1), 1),
            "1レースの点数（平均）": round(per_race["点数"].mean(), 1), "1レースの金額（平均）": round(per_race[_INVEST].mean()),
            "点数": int(per_race["点数"].sum()), "的中したレース": int(per_race["的中"].sum()),
            "的中率（レース）": round(per_race["的中"].mean(), 3), "投資": int(invest), "払戻": int(payout),
            "回収率": round(payout / invest, 3), "90%の幅（下）": round(low, 3), "90%の幅（上）": round(high, 3),
            "帯の回数": obi_hits, "最初の帯までの平均レース": round(races / obi_hits, 1) if obi_hits else float("nan"),
            "いちばん大きい当たりを除いた回収率": round((payout - per_race[_RETURN].max()) / invest, 3),
            "1年の投資": int(invest / max(years, 1)), "いちばん深い落ち込み": int(_drawdown(per_race)),
            "最大の連敗": _losing_streak(per_race),
        }


def _payback(totals: pd.Series) -> float:
    return totals[_RETURN] / totals[_INVEST] if totals[_INVEST] else float("nan")


def _drawdown(per_race: pd.DataFrame) -> float:
    """通算の損益のいちばん高いところから、いちばん下がった幅（円）。レースの順（開催日・レースID）に足していく。"""
    profit = (per_race[_RETURN] - per_race[_INVEST]).cumsum()
    return float((profit.cummax().clip(lower=0) - profit).max())


def _losing_streak(per_race: pd.DataFrame) -> int:
    """払戻の無いレースが続いた、いちばん長い数。"""
    lost = per_race[_RETURN].eq(0)
    runs = lost.groupby((~lost).cumsum()).sum()
    return int(runs.max()) if len(runs) else 0
