"""段3 の確かめの部品（並べ方・確率の当たり具合・組の確率・抑えの買い目・危険な人気馬の表）を、架空の値で確かめる。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from 超荒れの展開と適性から大穴を当てる.analysis.scenario_evaluation.band_logloss_table import BandLoglossTable
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_evaluation.band_ranking_table import BandRankingTable
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_evaluation.danger_file_writer import COLUMNS, DangerFileWriter
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_evaluation.evaluation_frame import EXPLORE
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_evaluation.favorite_out_table import FavoriteOutTable
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_evaluation.hedge_settlement import HedgeSettlement
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_evaluation.hedge_table import HedgeTable
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_evaluation.hedge_tickets import HedgeTickets
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_evaluation.mark_ticket_file import MarkTicketFile
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_evaluation.pair_probability import PairProbability
from 超荒れの展開と適性から大穴を当てる.analysis.scenario_evaluation.popularity_band import LONGSHOT, MIDDLE


def _race(race_id: str = "r1") -> pd.DataFrame:
    """12頭のレース。人気 = 馬番。10・11番人気が 1・2着、3番人気が3着。展開の型ごとの確率はハイだけ大穴が高い。"""
    horses = np.arange(1, 13)
    finish = {10: 1, 11: 2, 3: 3}
    base = np.linspace(0.6, 0.05, 12)
    high = base.copy()
    high[9:11] = 0.55
    return pd.DataFrame({
        "race_id": race_id, "horse_no": horses, "popularity": horses.astype(float), "period": EXPLORE, "race_date": "2024-01-01",
        "y_top3": [1.0 if h in finish else 0.0 for h in horses], "y_win": [1.0 if finish.get(h) == 1 else 0.0 for h in horses],
        "m_top3": base, "m_win": base / base.sum(), "s_top3_0": base, "s_top3_1": base, "s_top3_2": high,
        "p_win_新": np.where(horses == 10, 0.05, 0.01), "p_win_古": np.where(horses == 12, 0.05, 0.01), "p_top3_新": base,
        "w_0": 0.0, "w_1": 0.0, "w_2": 1.0,
    })


def test_組の確率は展開の型で混ぜ_ハイの型で来やすい2頭がいちばん高い():
    races, pairs = PairProbability(("s_top3_0", "s_top3_1", "s_top3_2")).races(_race())
    assert races.loc[0, "pair"] == "10-11"
    assert bool(races.loc[0, "pair_hit"])
    assert races.loc[0, "actual"] == 2
    assert 0 < races.loc[0, "two_or_more"] < 1
    assert pairs["rank"].min() == 1 and pairs.loc[pairs["rank"] == 1, "hit"].item()
    market, _ = PairProbability(("m_top3", "m_top3", "m_top3")).races(_race())
    assert market.loc[0, "pair"] == "4-5"                           # 市場では4番人気以下で上の2頭


def test_並べ方の表は人気帯の勝ち馬を上位何頭に置けたか():
    table = BandRankingTable(LONGSHOT, ("新", "古")).build(_race(), "t")
    rows = {row[0]: row for row in table.rows}
    assert rows["新"][3] == "100.0%"                                 # 新しい予想は10番人気を1位に置いた
    assert rows["古"][3] == "0.0%"
    assert rows["新"][5] == "100.0%"                                 # 人気の順でも10番人気が大穴の中の1位
    assert BandRankingTable(MIDDLE, ("新",)).build(_race(), "t").rows == []   # 中穴は勝っていない


def test_確率の当たり具合は同じ行の市場と比べる():
    table = BandLoglossTable((LONGSHOT,), ("新",)).build(_race(), "top3", "t")
    assert table.rows[0][3] == 3
    assert table.rows[0][6] == "+0.00000"                           # 新しい予想は市場と同じ確率


def test_抑えは本線にある組と同じ馬の重なりを除く():
    races = pd.DataFrame({"race_id": ["r1"], "period": [EXPLORE], "pair": ["10-11"]})
    favorites = pd.Series({"r1": 1})
    popular = pd.Series({"r1": [1, 2, 10]})
    main = pd.DataFrame({"race_id": ["r1"], "ticket_type": ["3連複"], "combo": ["021011"]})
    first = HedgeTickets("◎−組").build(races, favorites, popular, main)
    assert first["combo"].tolist() == ["011011"]
    trio = HedgeTickets("組−人気上位3頭").build(races, favorites, popular, main)
    assert trio["combo"].tolist() == ["011011"]                      # 2番人気との組は本線にある・10番は組と重なる
    settled = HedgeSettlement(pd.DataFrame({"race_id": ["r1"], "combo": ["011011"], "yen": [12340]})).settle(first)
    assert settled["payout"].tolist() == [12340.0]
    main_settled = pd.DataFrame({"race_id": ["r1"], "period": [EXPLORE], "unit": [0.5], "payout": [0.0]})
    table = HedgeTable().build({"◎−組": settled}, main_settled, "t")
    hedge = next(row for row in table.rows if row[0] == "抑え ◎−組")
    assert hedge[3] == 1 and hedge[-1] == "12340.0%"


def test_印の成績の買い目から本線と本命を取り出す(tmp_path: Path):
    path = tmp_path / "marks.csv"
    pd.DataFrame({"レースID": ["r1", "r1", "r1", "r1"], "開催日": ["2024-01-01"] * 4, "区切り": "x", "期待度": "低",
                  "買い方": ["単勝", "3連複（◎−○▲☆−○▲△☆）", "3連複（◎軸の流し）", "馬単（組の期待値）"],
                  "券種": ["単勝", "3連複", "3連複", "馬単"], "組番": ["07", "010207", "070809", "0702"], "単位": 1.0, "期待値": None,
                  "組の確率": None, "確定オッズ": 1.0, "払戻（100円あたり）": 0.0, "外した理由": None}).to_csv(path, index=False, encoding="utf-8-sig")
    marks = MarkTicketFile(path)
    table = marks.frame()
    assert marks.main(table)["combo"].tolist() == ["010207"]
    assert marks.favorites(table).to_dict() == {"r1": 7}


def test_危険な人気馬の表は今の消と同じ馬だけを1から引いて残す():
    top3 = pd.DataFrame({"レースID": ["r1", "r1"], "開催日": ["2024-01-01"] * 2, "馬ID": ["a", "b"], "馬番": [1, 2], "LightGBM": [0.7, 0.2],
                         "CatBoost": [0.5, 0.2], "確率": [0.6, 0.2], "区切り": "x", "期間": "テスト", "区分": "全体"})
    current = pd.DataFrame({"レースID": ["r1"], "馬番": [1], "区切り": ["x"], "期間": ["テスト"]})
    table = DangerFileWriter(top3, current).build()
    assert table.columns.tolist() == list(COLUMNS)
    assert table["確率"].tolist() == [pytest.approx(0.4)]
    assert table["LightGBM"].tolist() == [pytest.approx(0.3)]


def test_人気馬の表は市場より負けやすいと見た上位1割の実際を並べる():
    frame = pd.DataFrame({"popularity": [1.0] * 10, "period": EXPLORE, "y_top3": [0.0] + [1.0] * 9, "m_top3": [0.6] * 10,
                          "out_new": [0.9] + [0.3] * 9})
    table = FavoriteOutTable().build(frame, {"新": "out_new"}, "t")
    assert table.rows[0][5] == 1 and table.rows[0][6] == "100.0%"
