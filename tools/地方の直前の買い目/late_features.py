"""材料の表（1頭1行。オッズの断面と全頭の予想の確率）から、モデルが使う特徴量を作る。学ぶときも当てるときも同じ計算を通す。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .late_columns import (
    FEATURES,
    FIELD_SIZE,
    HORSE_NO,
    MATERIAL_COLUMNS,
    ODDS_A,
    ODDS_B,
    ODDS_FIRST,
    ODDS_NOW,
    PLACE_HIGH,
    PLACE_LOW,
    RACE_DATE,
    RACE_ID,
    TOP3_FREE,
    TOP3_MODEL,
    WIN_FREE,
    WIN_MODEL,
)

#: 確率の対数を取るときの下限。
_FLOOR = 1e-4


class LateFeatures:
    """レースの中で比べる特徴量（市場の見立て・人気順・予想と市場の差）は、渡した行のレースごとに計算する。
    今の単勝オッズと当日の予想の確率が無い馬は、取消などで買えないので行ごと外す（外した残りで市場の見立てを作る）。
    レースID は地方の 16 桁（9〜10 桁目が競馬場コード、15〜16 桁目がレース番号）。"""

    def build(self, material: pd.DataFrame) -> pd.DataFrame:
        """材料の列に ``FEATURES`` の列を足した表（行は買える馬だけ）。"""
        missing = [column for column in MATERIAL_COLUMNS if column not in material.columns]
        if missing:
            raise ValueError(f"材料の表に列が足りません: {'・'.join(missing)}")
        frame = material[(material[ODDS_NOW] > 0) & material[WIN_MODEL].notna()].copy()
        frame[RACE_ID] = frame[RACE_ID].astype(str)
        races = frame.groupby(RACE_ID)
        frame["lw"] = np.log(frame[ODDS_NOW])
        frame["over"] = races[ODDS_NOW].transform(lambda odds: (1 / odds).sum())
        frame["mkt"] = (1 / frame[ODDS_NOW]) / frame["over"]
        frame["rank"] = races[ODDS_NOW].rank(method="first")
        frame["lplo"] = self._log(frame[PLACE_LOW])
        frame["lphi"] = self._log(frame[PLACE_HIGH])
        for name, column in (("mom_a", ODDS_A), ("mom_b", ODDS_B), ("mom_first", ODDS_FIRST)):
            frame[name] = frame["lw"] - self._log(frame[column])
        frame["fav_lw"] = races["lw"].transform("min")
        frame["venue"] = frame[RACE_ID].str[8:10].astype(int)
        frame["race_no"] = frame[RACE_ID].str[14:16].astype(int)
        frame["field_size"] = frame[FIELD_SIZE].astype(float)
        frame["p1_thu"] = frame[WIN_FREE].astype(float)
        frame["p3_thu"] = frame[TOP3_FREE].astype(float)
        frame["p3_st"] = frame[TOP3_MODEL].astype(float)
        frame["p1_stn"] = frame[WIN_MODEL] / races[WIN_MODEL].transform("sum")
        market = np.log(frame["mkt"].clip(lower=_FLOOR))
        frame["st_gap"] = np.log(frame["p1_stn"].clip(lower=_FLOOR)) - market
        frame["thu_gap"] = np.log(frame["p1_thu"].clip(lower=_FLOOR)) - market
        frame["st_rank"] = races[WIN_MODEL].rank(ascending=False, method="first")
        frame["plc_gap"] = frame["lplo"] - frame["lw"]
        frame["dow"] = pd.to_datetime(frame[RACE_DATE]).dt.dayofweek
        frame["mkt2"] = frame.groupby(RACE_ID)["mkt"].transform(lambda share: share.nlargest(2).sum())
        frame["ent"] = frame.groupby(RACE_ID)["mkt"].transform(lambda share: -(share * np.log(share)).sum())
        return frame.sort_values([RACE_ID, HORSE_NO]).reset_index(drop=True)

    @staticmethod
    def matrix(features: pd.DataFrame) -> pd.DataFrame:
        """モデルに渡す特徴量だけの表（``FEATURES`` の並び）。"""
        return features[list(FEATURES)].astype(float)

    @staticmethod
    def _log(odds: pd.Series) -> pd.Series:
        """オッズの対数。無い・0 のオッズは欠損のまま（モデルは欠損を扱える）。"""
        values = pd.to_numeric(odds, errors="coerce").astype(float)
        return np.log(values.where(values > 0))
