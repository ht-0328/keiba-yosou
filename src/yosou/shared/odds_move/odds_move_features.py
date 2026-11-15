"""オッズの動きの直しの材料。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: オッズの動き（log(今のオッズ ÷ 前日のオッズ)）の上下の端。大きな動きに引っぱられすぎないように切る。
MOVE_LIMIT = 1.5
#: log(オッズ) を取るときのオッズの下限と上限（倍）。
ODDS_FLOOR, ODDS_CAP = 1.0, 300.0


class OddsMoveFeatures:
    """1頭ごとの直しの材料を、列の並び（オッズの動き・オッズの動き × log(今のオッズ)・前日のオッズがあるか）の行列にする。

    オッズの動き = log(今の単勝オッズ ÷ 前日の最後の単勝オッズ)（下がれば負）。±``MOVE_LIMIT`` で切る。
    前日のオッズが無い馬（前日に発売が無かったレース・途中のオッズが DB に無い期間）は、動きを 0、「前日のオッズがあるか」を 0 にする。
    """

    def matrix(self, win_odds: pd.Series, eve_odds: pd.Series) -> np.ndarray:
        """``win_odds`` は今の単勝オッズ、``eve_odds`` は前日の最後の単勝オッズ（無ければ欠損値）。並びは同じ。"""
        now = pd.to_numeric(win_odds, errors="coerce").astype(float).to_numpy()
        eve = pd.to_numeric(eve_odds, errors="coerce").astype(float).to_numpy()
        with np.errstate(divide="ignore", invalid="ignore"):
            move = np.log(now / np.where(eve > 0, eve, np.nan))
        has = np.isfinite(move).astype(float)
        move = np.where(np.isfinite(move), np.clip(move, -MOVE_LIMIT, MOVE_LIMIT), 0.0)
        log_odds = np.log(np.clip(np.nan_to_num(now, nan=ODDS_FLOOR), ODDS_FLOOR, ODDS_CAP))
        return np.column_stack([move, move * log_odds, has])
