"""LateRule（買う馬を選ぶ決まり）と LatePick（3連単の組）のテスト。"""

from __future__ import annotations

import pandas as pd

from 地方の直前の買い目 import late_columns as c
from 地方の直前の買い目.late_pick import LatePick
from 地方の直前の買い目.late_rule import LateRule


def _race() -> pd.DataFrame:
    return pd.DataFrame({c.HORSE_NO: [1, 2, 3, 4, 5, 6, 7], c.ODDS_NOW: [2.0, 4.0, 15.0, 6.0, 30.0, 8.0, 4.0],
                         c.LIKENESS: [0.1, 0.2, 0.5, 0.45, 0.39, 0.1, 0.1], c.PAYBACK: [0.8, 0.9, 1.1, 0.94, 1.3, 0.9, 0.9]})


def test_2つがそろって線以上の馬だけ_相手はその馬を除いた人気順() -> None:
    picks = LateRule().picks(_race())
    assert [pick.horse_no for pick in picks] == [3]            # 4番は戻りの見込み、5番は買う馬らしさが線に届かない
    assert picks[0].opponents == (1, 2, 7, 4, 6)               # 同じオッズは馬番の若い順。30倍の 5番は 6頭目なので入らない
    assert picks[0].odds == 15.0


def test_線を変えると買う馬が増え_買う馬らしさの高い順に並ぶ() -> None:
    picks = LateRule(likeness_line=0.3, payback_line=0.9).picks(_race())
    assert [pick.horse_no for pick in picks] == [3, 4, 5]


def test_3連単は_軸から相手2頭の並び_相手が5頭なら20点() -> None:
    pick = LateRule().picks(_race())[0]
    combos = pick.trifectas()
    assert len(combos) == 20 and all(combo[0] == 3 and combo[1] != combo[2] for combo in combos)
    assert LatePick(3, 15.0, 0.5, 1.1, (1,)).trifectas() == []


def test_線への近さは_馬ごとの小さいほうの比の_レースでいちばん大きい値() -> None:
    # 3番: min(0.5/0.4, 1.1/0.95) = 1.158、4番: min(1.125, 0.989) = 0.989、5番: min(0.975, 1.368) = 0.975
    assert round(LateRule().closeness(_race()), 3) == 1.158
    assert round(LateRule().closeness(_race()[lambda race: race[c.HORSE_NO] != 3]), 3) == 0.989   # 買う馬がいなければ 1 未満
    assert LateRule().closeness(_race().iloc[0:0]) is None


def test_辞書にして戻せる() -> None:
    pick = LateRule().picks(_race())[0]
    assert LatePick.from_dict(pick.to_dict()) == pick
