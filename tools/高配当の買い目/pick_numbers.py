"""買い目の集まりの成績の数字を出す。"""

from __future__ import annotations

import pandas as pd

from 共通.bootstrap_interval import BootstrapInterval
from 今週の予想.ticket_rules import POINT_YEN

from 高配当の買い目.pick_columns import HIT, PAYOUT, RACE_DATE, RACE_ID

#: 払戻の列の単位（100円あたり）。
_PAYOUT_UNIT = 100


class PickNumbers:
    """買い目の表（1行 = 1点。列 ``race_id``・``race_date``・``payout``（100円あたりの払戻。外れは 0）・``hit``）を、全部 1点 ``POINT_YEN`` 円で
    買ったときの成績の数字を出す。同じレースに何券種の点があってもよい（レースの数はレースIDで数える）。

    例: 3点（100円あたりの払戻が 0・0・2,500）なら、投資 300円・払戻 2,500円・回収率 8.33・的中数 1。
    """

    def __init__(self, picks: pd.DataFrame) -> None:
        self._picks = picks

    @property
    def points(self) -> int:
        return len(self._picks)

    @property
    def hits(self) -> int:
        return int(self._picks[HIT].sum())

    @property
    def races(self) -> int:
        """買ったレースの数。"""
        return int(self._picks[RACE_ID].nunique())

    @property
    def hit_races(self) -> int:
        """1点以上当たったレースの数。"""
        return int(self._picks.loc[self._picks[HIT] > 0, RACE_ID].nunique())

    @property
    def stake(self) -> int:
        """投資（円）。"""
        return POINT_YEN * self.points

    @property
    def payout(self) -> float:
        """払戻（円）。"""
        return float(self._picks[PAYOUT].sum()) * POINT_YEN / _PAYOUT_UNIT

    @property
    def rate(self) -> float:
        """回収率（払戻 ÷ 投資）。買った点が無ければ欠損値。"""
        return self.payout / self.stake if self.stake else float("nan")

    @property
    def points_per_race(self) -> float:
        """買ったレース1つあたりの点数。"""
        return self.points / self.races if self.races else float("nan")

    @property
    def hit_race_share(self) -> float:
        """買ったレースのうち、1点以上当たったレースの割合。"""
        return self.hit_races / self.races if self.races else float("nan")

    @property
    def median_multiple(self) -> float:
        """当たった点の配当（倍）の中央。当たりが無ければ欠損値。"""
        hit = self._picks.loc[self._picks[HIT] > 0, PAYOUT]
        return float(hit.median()) / _PAYOUT_UNIT if len(hit) else float("nan")

    def interval(self) -> tuple[float, float]:
        """回収率の 90% の幅（開催日を単位にしたブートストラップ。``BootstrapInterval``）。買った点が無ければ欠損値。"""
        if self._picks.empty:
            return float("nan"), float("nan")
        stake = pd.Series(float(POINT_YEN), index=self._picks.index)
        return BootstrapInterval().of(self._picks[RACE_DATE], stake, self._picks[PAYOUT] * POINT_YEN / _PAYOUT_UNIT)

    def by_day(self) -> pd.DataFrame:
        """開催日ごと（古い順）の、点数 ``points``・払戻 ``payout``（円）・的中数 ``hits``・収支 ``profit``（円）。買った開催日だけ。"""
        days = pd.to_datetime(self._picks[RACE_DATE]).rename("day")
        table = self._picks.groupby(days).agg(points=(HIT, "size"), payout=(PAYOUT, "sum"), hits=(HIT, "sum")).sort_index()
        table["payout"] = table["payout"] * POINT_YEN / _PAYOUT_UNIT
        return table.assign(profit=table["payout"] - table["points"] * POINT_YEN)

    def hit_days(self) -> int:
        """1点以上当たった開催日の数。"""
        return int((self.by_day()["hits"] > 0).sum())

    def drawdown(self) -> float:
        """いちばん深い落ち込み（円）。開催日ごとの収支を古い順に足していき、それまでのいちばん高い所（始めの 0 円も含む）から
        いちばん大きく下がった幅。例: 収支が −300・+1,000・−500・−400 の順なら、700 まで上がってから 900 下がるので 900。"""
        running = self.by_day()["profit"].cumsum()
        if running.empty:
            return 0.0
        peak = running.cummax().clip(lower=0.0)
        return float((peak - running).max())

    def longest_miss(self) -> int:
        """外れが続いた最長のレース数。買ったレースを開催日・レースIDの順に並べ、1点も当たらなかったレースが続いた数のいちばん長いもの。"""
        if self._picks.empty:
            return 0
        races = self._picks.groupby(RACE_ID).agg(day=(RACE_DATE, "first"), hits=(HIT, "sum")).reset_index().sort_values(["day", RACE_ID])
        missed = pd.Series((races["hits"] <= 0).to_numpy())
        # 当たりのたびに番号が変わる組に分け、組ごとの外れの数のいちばん大きいもの
        return int(missed.groupby((~missed).cumsum()).sum().max())
