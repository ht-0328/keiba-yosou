"""②③の予測の表から、消（1レース1頭）と穴（中穴3頭・大穴3頭）の決め方ごとの精度を年ごとに数える。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .band_data import FAVORITE_LAST, MIDDLE_LAST

#: 予測の表の列（``BandStudy`` が書く）。
RACE_ID, RACE_DATE, HORSE_ID, HORSE_NO = "race_id", "race_date", "horse_id", "horse_no"
POPULARITY, FINISH, PLACE_PAYOUT, WIN_ODDS = "popularity", "finish", "place_payout", "win_odds"
P_MODEL, P_MARKET, P3_FORM, MARKET_TOP3 = "p_model", "p_market", "p3_form", "market_top3"
PREDICTION_COLUMNS: tuple[str, ...] = (RACE_ID, RACE_DATE, HORSE_ID, HORSE_NO, POPULARITY, FINISH, PLACE_PAYOUT, WIN_ODDS,
                                       P_MODEL, P_MARKET, P3_FORM, MARKET_TOP3)
#: 表の列。
YEAR, RULE, COUNT = "年", "決め方", "頭数"
OUT_RATE, PLACE_RATE, PLACE_RETURN = "馬券外率", "3着以内率", "複勝回収率"
ALL_OUT_RATE, ALL_PLACE_RATE, ALL_PLACE_RETURN = "帯全体の馬券外率", "帯全体の3着以内率", "帯全体の複勝回収率"
BAND, MIDDLE, LONGSHOT = "帯", "中穴", "大穴"
#: 決め方の名前。
FORM_EDGE_MIN = "①の確率と市場の差が最低の1頭"
MODEL_EDGE_MAX = "②の確率と市場の差が最大の1頭"
MODEL_P_MAX = "②の確率が最大の1頭"
FORM_EDGE_TOP3 = "①の差の上位3頭"
MODEL_EDGE_TOP3 = "③の差の上位3頭"
MODEL_P_TOP3 = "③の確率の上位3頭"
#: 穴で帯から選ぶ頭数。
PICKS = 3


def _year(table: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(table[RACE_DATE]).dt.year


def _out(table: pd.DataFrame) -> pd.Series:
    finish = pd.to_numeric(table[FINISH], errors="coerce")
    return finish.isna() | (finish > 3)


def _place_return(table: pd.DataFrame) -> float:
    if table.empty:
        return float("nan")
    return float(pd.to_numeric(table[PLACE_PAYOUT], errors="coerce").fillna(0.0).sum() / (len(table) * 100.0))


class DangerPrecision:
    """② 1〜3番人気の予測の表から、消の決め方ごと・年ごとに、消にした馬の馬券外率と複勝回収率を、1〜3番人気全体と並べる。
    消が当たっているなら、馬券外率は全体より高く、複勝回収率は全体より低い。"""

    def __init__(self, lines: tuple[float, ...] = (0.05, 0.10)) -> None:
        self._lines = tuple(lines)

    def table(self, predictions: pd.DataFrame) -> pd.DataFrame:
        table = predictions.assign(**{YEAR: _year(predictions), "_out": _out(predictions),
                                      "_form_edge": predictions[P3_FORM] - predictions[MARKET_TOP3],
                                      "_model_edge": predictions[P_MODEL] - predictions[P_MARKET]})
        rules = [(FORM_EDGE_MIN, self._pick_min(table, "_form_edge")), (MODEL_EDGE_MAX, self._pick_max(table, "_model_edge")),
                 (MODEL_P_MAX, self._pick_max(table, P_MODEL))]
        rules += [(f"{MODEL_EDGE_MAX}（差 {line:.2f} 以上）", self._pick_max(table, "_model_edge", line)) for line in self._lines]
        rows = []
        for year, whole in table.groupby(YEAR, sort=True):
            for name, chosen in rules:
                picked = chosen[chosen[YEAR] == year]
                rows.append({YEAR: int(year), RULE: name, COUNT: len(picked), OUT_RATE: float(picked["_out"].mean()) if len(picked) else np.nan,
                             PLACE_RETURN: _place_return(picked), ALL_OUT_RATE: float(whole["_out"].mean()), ALL_PLACE_RETURN: _place_return(whole)})
        return pd.DataFrame(rows, columns=[YEAR, RULE, COUNT, OUT_RATE, PLACE_RETURN, ALL_OUT_RATE, ALL_PLACE_RETURN])

    def _pick_min(self, table: pd.DataFrame, column: str) -> pd.DataFrame:
        known = table[table[column].notna()]
        return known.loc[known.groupby(RACE_ID)[column].idxmin()]

    def _pick_max(self, table: pd.DataFrame, column: str, line: float | None = None) -> pd.DataFrame:
        known = table[table[column].notna()]
        picked = known.loc[known.groupby(RACE_ID)[column].idxmax()]
        return picked if line is None else picked[picked[column] >= line]


class LongshotPrecision:
    """③ 4番人気以下の予測の表から、中穴（4〜7番人気）・大穴（8番人気以下）ごとに、選び方ごと・年ごとの3着以内率と複勝回収率を、
    帯全体と並べる。選ぶのは1レースに帯ごと ``PICKS`` 頭まで。穴が当たっているなら、どちらも帯全体より高い。"""

    def __init__(self, lines: tuple[float, ...] = (0.03, 0.05)) -> None:
        self._lines = tuple(lines)

    def table(self, predictions: pd.DataFrame) -> pd.DataFrame:
        popularity = pd.to_numeric(predictions[POPULARITY], errors="coerce")
        table = predictions.assign(**{YEAR: _year(predictions), "_in": ~_out(predictions),
                                      BAND: np.where(popularity <= MIDDLE_LAST, MIDDLE, LONGSHOT),
                                      "_form_edge": predictions[P3_FORM] - predictions[MARKET_TOP3],
                                      "_model_edge": predictions[P_MODEL] - predictions[P_MARKET]})
        table = table[popularity > FAVORITE_LAST]
        rules = [(FORM_EDGE_TOP3, "_form_edge", None), (MODEL_EDGE_TOP3, "_model_edge", None), (MODEL_P_TOP3, P_MODEL, None)]
        rules += [(f"{MODEL_EDGE_TOP3}（差 {line:.2f} 以上）", "_model_edge", line) for line in self._lines]
        rows = []
        for (year, band), whole in table.groupby([YEAR, BAND], sort=True):
            for name, column, line in rules:
                picked = self._top(whole, column, line)
                rows.append({YEAR: int(year), BAND: band, RULE: name, COUNT: len(picked),
                             PLACE_RATE: float(picked["_in"].mean()) if len(picked) else np.nan, PLACE_RETURN: _place_return(picked),
                             ALL_PLACE_RATE: float(whole["_in"].mean()), ALL_PLACE_RETURN: _place_return(whole)})
        return pd.DataFrame(rows, columns=[YEAR, BAND, RULE, COUNT, PLACE_RATE, PLACE_RETURN, ALL_PLACE_RATE, ALL_PLACE_RETURN])

    def _top(self, table: pd.DataFrame, column: str, line: float | None) -> pd.DataFrame:
        known = table[table[column].notna()].sort_values([RACE_ID, column], ascending=[True, False], kind="stable")
        picked = known.groupby(RACE_ID).head(PICKS)
        return picked if line is None else picked[picked[column] >= line]
