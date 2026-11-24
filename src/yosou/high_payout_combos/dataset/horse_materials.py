"""馬ごとの表から、馬ごとの材料を作る。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from yosou.longshots_in_top3.feature import PlaceMarketRate
from yosou.shared.feature import as_numbers

from ..feature import material_names as m
from ..feature.column_names import HORSE_NO, RACE_ID
from ..repository import horse_table_columns as source
from .trifecta_pool_win import POOL_WIN

#: 印の番号。表に無い印（欠損を含む）は、印なし（－）と同じ 6 にする。
MARK_NUMBERS: dict[str, int] = {"◎": 0, "○": 1, "▲": 2, "△": 3, "☆": 4, "注": 5, "－": 6, "消": 7}
NO_MARK_NUMBER = MARK_NUMBERS["－"]
#: オッズの対数を取る前の下限（1倍未満は 1倍として扱う）。
_MIN_ODDS = 1.0


class HorseMaterials:
    """馬ごとの表（列は ``horse_table_columns.MATERIAL_COLUMNS``）と、3連単の板から見た勝率（``TrifectaPoolWin.of``）から、
    馬ごとの材料（``material_names.HORSE_MATERIALS`` の 22個）を作る。

    1行 = 1頭で、行の並びは ``horses`` と同じ。列は ``race_id``・``horse_no`` と材料。材料の意味は ``material_names.py`` の表。
    例: 予想の3着以内の確率 0.40・複勝オッズから見た3着以内率 0.30 の馬は、e3 が 0.10、rpm が log(0.40 ÷ 0.30) ≒ 0.29。
    3連単の板に無い馬の ``psup`` は欠損値。
    """

    def __init__(self) -> None:
        self._place_market = PlaceMarketRate()

    def of(self, horses: pd.DataFrame, pool_win: pd.DataFrame) -> pd.DataFrame:
        race_id = horses[source.RACE_ID].astype(str).reset_index(drop=True)
        horse_no = as_numbers(horses[source.HORSE_NO]).astype(int).reset_index(drop=True)
        table = pd.DataFrame({
            RACE_ID: race_id, HORSE_NO: horse_no, **self._probabilities(horses), **self._odds(horses), **self._marks(horses),
        })
        table = table.assign(**self._gaps(table), **self._shares(table))
        table[m.PSUP] = self._pool_support(table, pool_win)
        return table[[RACE_ID, HORSE_NO, *m.HORSE_MATERIALS]]

    def _probabilities(self, horses: pd.DataFrame) -> dict[str, np.ndarray]:
        """予想の確率（pw・p3）と、市場の確率（mw・m3・pm）。"""
        place_market = self._place_market.of(horses.assign(**{source.RACE_ID: horses[source.RACE_ID].astype(str)}))
        return {
            m.PW: self._numbers(horses, source.WIN_PROBABILITY), m.P3: self._numbers(horses, source.TOP3_PROBABILITY),
            m.MW: self._numbers(horses, source.MARKET_WIN), m.M3: self._numbers(horses, source.MARKET_TOP3),
            m.PM: place_market.to_numpy(dtype=float),
        }

    def _odds(self, horses: pd.DataFrame) -> dict[str, np.ndarray]:
        """単勝オッズと、複勝オッズの真ん中の対数（lwo・lpo）。"""
        place_middle = (self._numbers(horses, source.PLACE_ODDS_LOW) + self._numbers(horses, source.PLACE_ODDS_HIGH)) / 2.0
        return {
            m.LWO: np.log(np.clip(self._numbers(horses, source.WIN_ODDS), _MIN_ODDS, None)),
            m.LPO: np.log(np.clip(place_middle, _MIN_ODDS, None)),
        }

    def _marks(self, horses: pd.DataFrame) -> dict[str, np.ndarray]:
        """人気・順位・危険な人気馬・印・上げ下げ・期待値（pop・rk・dg・ds・mk・updown・wv・pv）。"""
        is_danger = horses[source.IS_DANGER].astype("boolean").fillna(False)
        mark_number = horses[source.MARK].map(MARK_NUMBERS).astype(float).fillna(NO_MARK_NUMBER)
        return {
            m.POP: self._numbers(horses, source.POPULARITY), m.RK: self._numbers(horses, source.RANK),
            m.DG: is_danger.to_numpy(dtype=float), m.DS: np.nan_to_num(self._numbers(horses, source.DANGER_SCORE), nan=0.0),
            m.MK: mark_number.to_numpy(dtype=float), m.UPDOWN: self._numbers(horses, source.UPDOWN),
            m.WV: self._numbers(horses, source.WIN_VALUE), m.PV: self._numbers(horses, source.PLACE_VALUE),
        }

    def _gaps(self, table: pd.DataFrame) -> dict[str, pd.Series]:
        """予想と市場の差（e3）と、比の対数（r3・rw・rpm）。"""
        top3, win = table[m.P3].clip(lower=m.FLOOR), table[m.PW].clip(lower=m.FLOOR)
        return {
            m.E3: table[m.P3] - table[m.PM],
            m.R3: np.log(top3 / table[m.M3].clip(lower=m.FLOOR)),
            m.RW: np.log(win / table[m.MW].clip(lower=m.FLOOR)),
            m.RPM: np.log(top3 / table[m.PM].clip(lower=m.FLOOR)),
        }

    def _shares(self, table: pd.DataFrame) -> dict[str, pd.Series]:
        """予想の1着の確率と、単勝オッズから見た勝率を、レースで合計 1 にそろえた値（pwn・mwn）。"""
        races = table[RACE_ID]
        return {
            m.WIN_SHARE: table[m.PW] / table[m.PW].groupby(races).transform("sum"),
            m.MARKET_WIN_SHARE: table[m.MW] / table[m.MW].groupby(races).transform("sum"),
        }

    def _pool_support(self, table: pd.DataFrame, pool_win: pd.DataFrame) -> np.ndarray:
        """3連単の板から見た勝率 ÷ 単勝オッズから見た勝率（psup）。"""
        found = table[[RACE_ID, HORSE_NO]].merge(pool_win, on=[RACE_ID, HORSE_NO], how="left")
        market_win = table[m.MW].where(table[m.MW] > 0)
        return found[POOL_WIN].to_numpy(dtype=float) / market_win.to_numpy(dtype=float)

    def _numbers(self, horses: pd.DataFrame, column: str) -> np.ndarray:
        return as_numbers(horses[column]).to_numpy(dtype=float)
