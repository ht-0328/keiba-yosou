"""段ごとの予想（②消・③穴・④荒れ具合）で買い目を決める口。手で作った表と、一時フォルダの予測の表で確かめる。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from 地方の万馬券.analysis.payout_band import BIG, HUGE, MEDIUM, SOLID
from 地方の万馬券.analysis.popularity_band import FAVORITE, LONGSHOT, MIDDLE
from 地方の万馬券.analysis.trifecta.harville_combos import HarvilleCombos
from 地方の万馬券.analysis.trifecta.race_market import EDGE, MARKET_UPSET
from 地方の万馬券.analysis.trifecta.stage_predictions import (
    BIG_OR_MORE,
    DANGER_EDGE,
    DANGER_FILE,
    LONGSHOT_EDGE,
    LONGSHOT_FILE,
    MID_OR_MORE,
    STAGE_UPSET,
    TRIFECTA_KEY,
    UPSET_FILES,
    StagePredictions,
    upset_column,
)
from 地方の万馬券.analysis.trifecta.strategy import EDGE_DANGER, EDGE_LONGSHOT, UPSET_STAGE, Strategy
from 地方の万馬券.analysis.trifecta.strategy_catalog import STAGE_STRATEGIES, STRATEGIES
from 地方の万馬券.analysis.trifecta.ticket_plan import TicketPlan


def _runners() -> pd.DataFrame:
    """1レース 8頭。①の差では 3番人気が最低・7番人気が大穴の1位だが、②は 1番人気が危険、③は 8番人気が上。④は大荒れ（確率 0.3）。"""
    return pd.DataFrame({
        "race_id": [1] * 8, "horse_no": range(1, 9), "popularity": range(1, 9),
        "band": [FAVORITE] * 3 + [MIDDLE] * 3 + [LONGSHOT] * 2,
        EDGE: [0.05, 0.02, -0.10, 0.03, 0.01, -0.02, 0.04, -0.01], MARKET_UPSET: [SOLID] * 8,
        DANGER_EDGE: [0.20, 0.00, -0.05, np.nan, np.nan, np.nan, np.nan, np.nan],
        LONGSHOT_EDGE: [np.nan, np.nan, np.nan, 0.01, 0.02, 0.03, -0.02, 0.05],
        upset_column(BIG_OR_MORE, TRIFECTA_KEY): [0.3] * 8, upset_column(MID_OR_MORE, TRIFECTA_KEY): [0.8] * 8,
        upset_column(STAGE_UPSET, TRIFECTA_KEY): [BIG] * 8,
    })


def _combos_and_odds() -> tuple[pd.DataFrame, pd.DataFrame]:
    combos = HarvilleCombos().all_races(pd.DataFrame({"race_id": [1] * 8, "horse_no": range(1, 9), "strength": [0.3, 0.2, 0.15, 0.1, 0.1, 0.05, 0.05, 0.05]}))
    odds = combos[["race_id", "first", "second", "third"]].copy()
    odds["odds"] = 2.0 / combos["probability"]
    return combos, odds


def test_消を2で決めると_2の差が最大の人気馬を消し_穴を3で決めると_3の差の順に選ぶ():
    combos, odds = _combos_and_odds()
    plain = TicketPlan(Strategy("t", {SOLID: ("人中大",)}, max_points=1000)).build(_runners(), combos, odds)
    assert set(plain["first"]) == {1, 2} and set(plain["third"]) == {7, 8}          # ①: 3番人気を消す
    staged = TicketPlan(Strategy("t", {SOLID: ("人中大",)}, max_points=1000, danger=EDGE_DANGER, longshot=EDGE_LONGSHOT)).build(_runners(), combos, odds)
    assert set(staged["first"]) == {2, 3}                                           # ②: 1番人気（差 0.20）を消す
    assert set(staged["third"]) == {7, 8} and set(staged["second"]) == {4, 5, 6}     # 大穴は2頭とも、中穴は3頭とも
    narrow = TicketPlan(Strategy("t", {SOLID: ("人中大",)}, max_points=1000, longshot=EDGE_LONGSHOT, longshots=1, middles=2)).build(_runners(), combos, odds)
    assert set(narrow["third"]) == {8} and set(narrow["second"]) == {5, 6}           # ③の差の高い順（8番・6番5番）


def test_消と穴の線は_線に届かないレースでは消さず_線未満の穴は使わない():
    combos, odds = _combos_and_odds()
    kept = TicketPlan(Strategy("t", {SOLID: ("人中大",)}, max_points=1000, danger=EDGE_DANGER, danger_min=0.30)).build(_runners(), combos, odds)
    assert set(kept["first"]) == {1, 2, 3}                                          # ②の差の最大 0.20 < 0.30 なので消さない
    cut = TicketPlan(Strategy("t", {SOLID: ("人中大",)}, max_points=1000, longshot=EDGE_LONGSHOT, longshot_min=0.025)).build(_runners(), combos, odds)
    assert set(cut["second"]) == {6} and set(cut["third"]) == {8}                   # ③の差 0.03 と 0.05 だけ


def test_2の値が無いレースは1の差で消す():
    combos, odds = _combos_and_odds()
    runners = _runners().assign(**{DANGER_EDGE: np.nan})
    staged = TicketPlan(Strategy("t", {SOLID: ("人中大",)}, max_points=1000, danger=EDGE_DANGER)).build(runners, combos, odds)
    assert set(staged["first"]) == {1, 2}


def test_4の線と型で_買うレースと型が決まる():
    combos, odds = _combos_and_odds()
    assert TicketPlan(Strategy("t", {SOLID: ("全",)}, big_min=0.4)).build(_runners(), combos, odds).empty          # 0.3 < 0.4
    some = TicketPlan(Strategy("t", {SOLID: ("全",)}, big_min=0.25, mid_min=0.5, max_points=5)).build(_runners(), combos, odds)
    assert len(some) == 5
    # 市場では固いが④は大荒れ: ④の型（大荒れ: 人中大）で買える
    by_stage = TicketPlan(Strategy("t", {BIG: ("人中大",)}, upset_source=UPSET_STAGE, max_points=1000)).build(_runners(), combos, odds)
    assert set(by_stage["pattern"]) == {"人中大"} and not by_stage.empty
    assert TicketPlan(Strategy("t", {BIG: ("人中大",)})).build(_runners(), combos, odds).empty                     # 市場の荒れ具合では固い
    # ④の列が無ければ、④で型を決める買い方は何も買わない
    without = _runners().drop(columns=[upset_column(STAGE_UPSET, TRIFECTA_KEY), upset_column(BIG_OR_MORE, TRIFECTA_KEY)])
    assert TicketPlan(Strategy("t", {BIG: ("全",)}, upset_source=UPSET_STAGE)).build(without, combos, odds).empty
    assert TicketPlan(Strategy("t", {SOLID: ("全",)}, big_min=0.1)).build(without, combos, odds).empty


def test_予測の表を読んで走者の表に差と荒れ具合を足す(tmp_path: Path):
    pd.DataFrame({"race_id": ["1", "1"], "horse_no": [1, 2], "p_model": [0.5, 0.3], "p_market": [0.3, 0.3]}).to_pickle(tmp_path / DANGER_FILE)
    pd.DataFrame({"race_id": ["1"], "horse_no": [8], "p_model": [0.2], "p_market": [0.1]}).to_pickle(tmp_path / LONGSHOT_FILE)
    pd.DataFrame({"race_id": ["1"], SOLID: [0.1], MEDIUM: [0.3], BIG: [0.5], HUGE: [0.1], "大荒れ以上の確率": [0.6], "中荒れ以上の確率": [0.9]}).to_pickle(
        tmp_path / UPSET_FILES[TRIFECTA_KEY])
    runners = pd.DataFrame({"race_id": [1, 1, 1, 2], "horse_no": [1, 2, 8, 1]})
    table = StagePredictions(tmp_path).attach(runners)
    assert table[DANGER_EDGE].round(3).tolist()[:2] == [0.2, 0.0] and np.isnan(table[DANGER_EDGE].iloc[3])
    assert abs(table[LONGSHOT_EDGE].iloc[2] - 0.1) < 1e-9 and np.isnan(table[LONGSHOT_EDGE].iloc[0])
    assert table[upset_column(BIG_OR_MORE, TRIFECTA_KEY)].tolist()[:3] == [0.6] * 3 and table[upset_column(STAGE_UPSET, TRIFECTA_KEY)].iloc[0] == BIG
    assert np.isnan(table[upset_column(BIG_OR_MORE, "trio")].iloc[0])             # 3連複の④のファイルは無い
    assert np.isnan(table[upset_column(BIG_OR_MORE, TRIFECTA_KEY)].iloc[3])       # 表に無いレース


def test_段の買い方は一覧に入り_名前が重ならない():
    names = [s.name.split(" ", 1)[0] for s in STRATEGIES]
    assert len(names) == len(set(names)) and all(s in STRATEGIES for s in STAGE_STRATEGIES)
