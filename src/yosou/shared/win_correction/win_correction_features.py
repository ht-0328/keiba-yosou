"""確率の直しの材料（券種どうしのずれ・人気と順位・レースの中身と馬の事情）を、1頭1行の表にする。"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: 入力の列（1頭1行）。
RACE_ID, HORSE_NO = "race_id", "horse_no"
WIN_PROBABILITY, TOP3_PROBABILITY = "win_probability", "probability"
WIN_ODDS, PLACE_ODDS_LOW, PLACE_ODDS_HIGH = "win_odds", "place_odds_low", "place_odds_high"
QUINELLA_TOP2 = "quinella_top2"
#: 事実表（``共通.facts``）から写す列。発走前に分かり、本番の当日の予想でも同じ値になるものだけ（馬場状態と馬体重の増減は、
#: 発表が予想の時刻に間に合わないことがあるので使わない。文字の列も使わない）。
FACT_COLUMNS: tuple[str, ...] = ("surface_order", "distance_m", "class_order", "venue_code", "month", "age", "carried", "interval_days",
                                 "prev_popularity", "prev_finish", "runs_before", "sex_order")
#: 出発点（今の1着の確率のロジット）の列。
BASE = "base"
#: 材料の列の並び（学習と予測で同じ）。
FEATURES: tuple[str, ...] = ("p_vs_win", "p3_vs_place", "place_vs_win", "quinella_vs_win", "place_spread", "log_odds", "popularity",
                             "win_rank", "top3_rank", "field", "top_market", *FACT_COLUMNS)
#: 確率のロジットを取るときの端。
_EDGE = 1e-4


class WinCorrectionFeatures:
    """1頭1行の表（列 ``race_id``・``horse_no``・``win_probability``（今の1着の確率）・``probability``（今の3着以内の確率）・``win_odds``・
    ``place_odds_low``・``place_odds_high``・``quinella_top2``（馬連から見た2着以内率。``QuinellaTop2``）と ``FACT_COLUMNS``）から、
    出発点 ``base`` と材料 ``FEATURES`` の表を作る。並びと index は入力と同じ。

    - 1着の確率はレースの中で合計 1 にそろえてから使う。単勝から見た勝率は単勝オッズの逆数をレースで合計 1、
      複勝から見た3着以内率は複勝の最低オッズの逆数をレースで合計 3 にそろえたもの。
    - ずれは log の比（例 ``p_vs_win`` = log(1着の確率 ÷ 単勝から見た勝率)、``place_vs_win`` = log(複勝から見た3着以内率 ÷ (3 × 単勝から見た勝率))）。
    - ``place_spread`` は log(複勝の最高オッズ × 複勝から見た3着以内率 ÷ 3)（最高オッズが無ければ 0）。順位は 1 が上。
    - 事実表の列は数にする（数にならない値は欠損値。LightGBM は欠損値のまま扱う）。
    """

    def frame(self, horses: pd.DataFrame) -> pd.DataFrame:
        race = horses[RACE_ID].astype(str)
        p = _per_race(horses[WIN_PROBABILITY].astype(float), race, 1.0)
        market_win = _per_race(1.0 / horses[WIN_ODDS].astype(float), race, 1.0)
        market_place = _per_race(1.0 / horses[PLACE_ODDS_LOW].astype(float), race, 3.0).clip(lower=_EDGE)
        p3 = horses[TOP3_PROBABILITY].astype(float)
        high = pd.to_numeric(horses[PLACE_ODDS_HIGH], errors="coerce")
        out = pd.DataFrame(index=horses.index)
        out[BASE] = _logit(p)
        out["p_vs_win"] = np.log(p / market_win)
        out["p3_vs_place"] = np.log(p3 / market_place)
        out["place_vs_win"] = np.log(market_place / (3 * market_win))
        out["quinella_vs_win"] = np.log(horses[QUINELLA_TOP2].astype(float) / (2 * market_win))
        out["place_spread"] = np.log((high * market_place / 3).clip(lower=1e-3)).fillna(0.0)
        out["log_odds"] = np.log(horses[WIN_ODDS].astype(float))
        out["popularity"] = horses[WIN_ODDS].astype(float).groupby(race).rank(method="first")
        out["win_rank"] = p.groupby(race).rank(ascending=False, method="first")
        out["top3_rank"] = p3.groupby(race).rank(ascending=False, method="first")
        out["field"] = race.groupby(race).transform("size").astype(float)
        out["top_market"] = market_win.groupby(race).transform("max")
        for column in FACT_COLUMNS:
            out[column] = pd.to_numeric(horses[column], errors="coerce") if column in horses.columns else np.nan
        return out


def _per_race(values: pd.Series, race: pd.Series, total: float) -> pd.Series:
    """レースの中で合計 ``total`` にそろえる。"""
    return total * values / values.groupby(race).transform("sum")


def _logit(p: pd.Series) -> pd.Series:
    clipped = p.clip(_EDGE, 1 - _EDGE)
    return np.log(clipped / (1 - clipped))
