"""詳しく見る日の部品（まとまり・理由の文・表）を、架空の値で確かめる。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from 超荒れの展開と適性から大穴を当てる.analysis.focus_day.focus_day_report import FocusDayReport
from 超荒れの展開と適性から大穴を当てる.analysis.focus_day.focus_day_runner import FocusDayRunner
from 超荒れの展開と適性から大穴を当てる.analysis.focus_day.material_groups import DEVELOPMENT, FORM, HANDICAP, TRACK, MaterialGroups
from 超荒れの展開と適性から大穴を当てる.analysis.focus_day.reason_writer import ReasonWriter


def test_列名からまとまりを決める():
    groups = MaterialGroups()
    assert groups.of("斤量の前走との差") == HANDICAP
    assert groups.of("先のレースの内の傾き") == TRACK
    assert groups.of("展開の予想_ハイペースの確率") == DEVELOPMENT
    assert groups.of("能力指数") == FORM


def test_理由の文は寄与の大きい順に得か損かと事実を書く():
    row = pd.Series({DEVELOPMENT: -0.3, HANDICAP: 0.1, TRACK: 0.01, FORM: 0.0, "予想_スロー": 0.1, "予想_平均": 0.2, "予想_ハイ": 0.7,
                     "位置_前": 0.8, "位置_後ろ": 0.05, "ハンデ戦か": 1.0, "トップとの差": -3.0, "斤量の前走との差": -2.0, "昇級か": 1.0,
                     "先のレースの内の傾き": np.nan, "馬番の位置": 0.1})
    text = ReasonWriter().write(row)
    assert text.startswith("展開で損（ハイペース予想（0.70）で前の見込み。前が苦しい展開）")
    assert "ハンデで得（ハンデ戦でトップより 3.0kg 軽い・前走より 2.0kg 軽い・昇級）" in text
    assert "馬場" not in text                                       # 寄与が小さいまとまりは書かない
    assert ReasonWriter().write(pd.Series({DEVELOPMENT: 0.0})) == "展開・馬場・ハンデの上げ下げは小さい"


def test_順位と荒れる前提の確率は人気帯の中で決める():
    frame = pd.DataFrame({"レースID": ["r"] * 4, "馬番": [1, 2, 3, 4], "popularity": [1.0, 2.0, 10.0, 11.0], "p_win": [0.5, 0.3, 0.15, 0.05],
                          "p_top3": [0.8, 0.6, 0.4, 0.2], "m_top3": [0.7, 0.6, 0.3, 0.2]})
    current = pd.DataFrame({"レースID": ["r"] * 4, "馬番": [1, 2, 3, 4], "今のモデルの1着": [0.4, 0.4, 0.1, 0.1]})
    ranked = FocusDayRunner({}).ranks(frame, current).set_index("馬番")
    assert ranked.loc[3, "人気帯"] == "大穴"
    assert round(ranked.loc[3, "荒れる前提の確率"], 6) == 0.75
    assert ranked.loc[4, "人気帯の中の順位"] == 2
    assert round(ranked.loc[1, "4着以下の市場との差"], 2) == -0.1
    horses = ranked.reset_index().assign(horse_name=["a", "b", "c", "d"], finish=[3.0, 4.0, 1.0, 2.0], final_popularity=[1, 2, 10, 11],
                                         race_name="", 理由="小さい", m_win=[0.4, 0.3, 0.2, 0.1])
    pairs = pd.DataFrame({"race_id": ["r"], "pair": ["3-4"], "pair_probability": [0.05], "two_or_more": [0.2]})
    report = FocusDayReport(horses, pairs)
    focus = report.focus([("試し", "r", 3)], "t")
    assert focus.rows[0][5] == "1" and focus.rows[0][6] == "3 / 4"
    races = report.races("t")
    assert races.rows[0][5] == "3-4（0.050）" and races.rows[0][7] == "3（10人）−4（11人）−1（1人）"
