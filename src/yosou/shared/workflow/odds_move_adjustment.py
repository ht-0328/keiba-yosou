"""当日の予測の流れで、オッズの動きの直しを1レースの予測に掛ける。"""

from __future__ import annotations

from collections.abc import Callable

import pandas as pd

from ..dataset import PredictionData
from ..dataset.column_names import HORSE_NO, RACE_ID, WIN_ODDS
from ..odds_move import OddsMoveCorrection

#: レースID → 前日の最後の単勝オッズ（列 ``horse_no``・``eve_odds``。``EveOddsRepository.read``）。
EveOddsReader = Callable[[str], pd.DataFrame]


class OddsMoveAdjustment:
    """予測用データ（ID と単勝オッズ）と前日の最後の単勝オッズから、3着以内と1着の確率を直す（``OddsMoveCorrection``）。

    今の単勝オッズは予測に使ったオッズ（予測用データの特徴量の単勝オッズ。無ければ ``market`` の単勝オッズ）。
    単勝オッズの無い予測用データ（木曜）は直さない。
    """

    def __init__(self, correction: OddsMoveCorrection, eve_odds: EveOddsReader) -> None:
        self._correction = correction
        self._eve_odds = eve_odds

    def top3(self, probability: pd.Series, data: PredictionData) -> pd.Series:
        inputs = self._inputs(data)
        return probability if inputs is None else self._correction.top3(probability, *inputs)

    def win(self, probability: pd.Series, data: PredictionData) -> pd.Series:
        inputs = self._inputs(data)
        return probability if inputs is None else self._correction.win(probability, *inputs)

    def _inputs(self, data: PredictionData) -> tuple[pd.Series, pd.Series] | None:
        """今の単勝オッズと前日の最後の単勝オッズ（どちらも ``data.ids`` と同じ index）。単勝オッズが無ければ None。"""
        if WIN_ODDS in data.features.columns:
            win_odds = data.features[WIN_ODDS]
        elif data.market is not None and WIN_ODDS in data.market.columns:
            win_odds = data.market[WIN_ODDS]
        else:
            return None
        if data.ids.empty:
            return None
        eve = self._eve_odds(str(data.ids[RACE_ID].iloc[0]))
        by_horse = dict(zip(eve["horse_no"], eve["eve_odds"])) if not eve.empty else {}
        horse_no = pd.to_numeric(data.ids[HORSE_NO], errors="coerce")
        eve_odds = pd.Series([by_horse.get(int(no)) if pd.notna(no) else None for no in horse_no], index=data.ids.index, dtype=float)
        return pd.Series(win_odds.to_numpy(), index=data.ids.index), eve_odds
