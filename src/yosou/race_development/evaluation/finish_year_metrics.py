"""着順の予想（⑦）の、年ごとの当たり具合。"""

from __future__ import annotations

import pandas as pd

from ..dataset import label_names as names
from ..feature import PLAIN_WIN_PROBABILITY, WIN_PROBABILITY
from .race_metrics import RaceMetrics

#: 入力の列（1行 = 1頭）。
YEAR, WIN_ODDS, POPULARITY = "年", "win_odds", "popularity"


class FinishYearMetrics:
    """⑦ の年ごとの当たり具合（設計書 16 の 7 の表3）。1着のレースごとのログ損失を、前半・後半を入れないモデル・全馬に同じ確率・
    単勝オッズ（参考）と並べ、◎（1着の確率が 1位の馬）の勝率・3着以内率と、1番人気の勝率（参考）を出す。

    ``horses`` は1行 = 1頭（列 ``年``・``race_id``・``1着``・``確定着順``・``p_win``・``p_win_plain``・``win_odds``・``popularity``）。
    ログ損失は、1着が1頭に決まるレースだけで測る。
    """

    def __init__(self) -> None:
        self._metrics = RaceMetrics()

    def table(self, horses: pd.DataFrame, training_rows: dict[str, int]) -> pd.DataFrame:
        """1行 = 1年。``training_rows`` は 年 → その年の ⑦ のモデルの学習データの行数。"""
        rows = [self._year_row(str(year), part, training_rows.get(str(year))) for year, part in horses.groupby(YEAR)]
        return pd.DataFrame(rows)

    def _year_row(self, year: str, horses: pd.DataFrame, training_rows: int | None) -> dict[str, object]:
        metrics, race = self._metrics, horses["race_id"]
        labeled = horses[horses[names.WINNER].notna()]
        field = labeled.groupby("race_id")["race_id"].transform("size")
        implied = 1.0 / labeled[WIN_ODDS]
        market = implied / implied.groupby(labeled["race_id"]).transform("sum")
        best = horses[WIN_PROBABILITY].eq(horses[WIN_PROBABILITY].groupby(race).transform("max"))
        first_best = best & ~best.groupby(race).cumsum().gt(1)
        finish = horses[names.FINISH]
        return {
            "年": year,
            "レース数": int(race.nunique()),
            "着順のモデルの学習データの行数": training_rows,
            "1着のログ損失（モデル）": metrics.race_log_loss(labeled[WIN_PROBABILITY], labeled[names.WINNER]),
            "同（前半・後半を入れないモデル）": metrics.race_log_loss(labeled[PLAIN_WIN_PROBABILITY], labeled[names.WINNER]),
            "同（全馬に同じ確率）": metrics.race_log_loss(1.0 / field, labeled[names.WINNER]),
            "同（参考: 単勝オッズ）": metrics.race_log_loss(market, labeled[names.WINNER]),
            "◎の勝率": float(finish[first_best].eq(1).mean()),
            "◎の3着以内率": float(finish[first_best].le(3).mean()),
            "1番人気の勝率（参考）": float(finish[horses[POPULARITY].eq(1)].eq(1).mean()),
        }
