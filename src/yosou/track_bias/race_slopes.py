"""終わったレースごとに、内の傾きと前の傾きを出す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.shared.feature import as_numbers
from yosou.shared.feature.odds import TOP3_RATE, MarketPlaces

from . import names
from .positions import Positions

#: 3着以内とみなす着順（7頭以下のレースも3着以内で数える。展開スコアと同じ）。
_PLACES = 3


class RaceSlopes:
    """``BiasRunRepository`` が読んだ出走の表から、レースごとの傾きを出す（設計書「買うレースと買い目を決める」06 の 1）。

    - 残差 e = 3着以内（1 か 0）− 市場から見た3着以内率（単勝オッズから Harville の式で。全頭の予想の出発点と同じ物差し）
    - 内の傾き = Σ(e × u) ÷ Σ(u × u)、前の傾き = Σ(e × v) ÷ Σ(v × v)。正なら内（前）が市場の見立てより来ている

    市場の見立てを差し引くので、強い人気馬がたまたま内にいただけでは傾きにならない。4コーナーの順位の無いレース（直線のコースなど）は
    前の傾きが欠損値。着順の無い馬（競走中止）は数えない。
    例（架空）: 16頭立てで、内の馬ほど市場の見立てより来ていれば、内の傾きは正になる。
    """

    def __init__(self) -> None:
        self._positions = Positions()
        self._market = MarketPlaces()

    def of(self, runs: pd.DataFrame) -> pd.DataFrame:
        """1行 = 1レース。列は ``race_id``・``race_date``・``venue_code``・``surface``・``track_code``・``meeting_day``・``condition_code``・
        ``race_no``・``内の傾き``・``前の傾き``。開催日・レースID の順。"""
        finish = as_numbers(runs["finish"])
        top3 = (finish <= _PLACES).astype("float64").where(finish.notna())
        residual = top3 - self._market.of(runs)[TOP3_RATE]
        inner = self._positions.innerness(runs["horse_no"], runs["field_size"])
        front = self._positions.frontness_of_rank(runs["corner4"], runs["field_size"])
        table = runs.assign(**{
            "_eu": residual * inner, "_uu": inner * inner, "_ev": residual * front, "_vv": front * front,
        })
        grouped = table.groupby(names.RACE_ID, sort=False)
        sums = grouped[["_eu", "_uu", "_ev", "_vv"]].sum(min_count=1)
        slopes = pd.DataFrame({
            names.INNER_SLOPE: self._ratio(sums["_eu"], sums["_uu"]),
            names.FRONT_SLOPE: self._ratio(sums["_ev"], sums["_vv"]),
        })
        races = grouped[[names.RACE_DATE, names.VENUE_CODE, names.SURFACE, names.TRACK_CODE, names.CONDITION_CODE, names.RACE_NO]].first()
        races[names.MEETING_DAY] = meeting_day_of(races.index.to_series())
        return (races.join(slopes).reset_index().sort_values([names.RACE_DATE, names.RACE_ID], kind="stable")
                .reset_index(drop=True))

    def _ratio(self, numerator: pd.Series, denominator: pd.Series) -> pd.Series:
        return (numerator / denominator.where(denominator > 0)).replace([np.inf, -np.inf], np.nan)


def meeting_day_of(race_ids: pd.Series) -> pd.Series:
    """rid（開催年4・開催月日4・競馬場2・開催回2・開催日目2・レース番号2 の順。開催日目は 13〜14桁目）から、開催の何日目かを読む。"""
    return as_numbers(race_ids.astype(str).str.slice(12, 14))
