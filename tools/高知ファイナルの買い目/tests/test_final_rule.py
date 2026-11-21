"""FinalRule（予想の付いた表 → 印と買い目）と FinalBets・FinalBetFile のテスト。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 高知ファイナルの買い目 import final_columns as c
from 高知ファイナルの買い目.final_bet_file import FinalBetFile
from 高知ファイナルの買い目.final_bets import EXACTA, PLACE, QUINELLA, TRIFECTA, TRIO, WIDE, WIN_BET, FinalBets
from 高知ファイナルの買い目.final_rule import FinalRule


def _scored(place_low: float = 3.0, heads: int = 10) -> pd.DataFrame:
    """馬番 = そのときの人気。割安さは 5番がいちばん高く、1番人気（1番）も高い。3着以内の確率は馬番の小さい順に高い。"""
    numbers = list(range(1, heads + 1))
    value = {1: 1.5, 5: 1.4}
    return pd.DataFrame({c.HORSE_NO: numbers, c.POPULARITY_NOW: [float(no) for no in numbers], c.VALUE: [value.get(no, 0.9) for no in numbers],
                         c.TOP3: [0.6 - 0.05 * no for no in numbers], c.PLACE_LOW: place_low})


def test_本命は1番人気以外でいちばん割安な馬_相手は3着以内の確率の高い順() -> None:
    bets = FinalRule().decide(_scored(), "11222040")
    assert (bets.head, bets.favorite, bets.partners, bets.announced) == (5, 1, (1, 2, 3, 4, 6), "11222040")


def test_単勝_馬連_馬単_3連単は毎回買う() -> None:
    tickets = FinalRule().decide(_scored(place_low=1.0)).tickets
    assert tickets[WIN_BET] == ((5,),) and tickets[QUINELLA] == ((1, 5), (2, 5)) and tickets[EXACTA] == ((5, 1), (5, 2))
    trifectas = tickets[TRIFECTA]
    assert len(trifectas) == len(set(trifectas)) and all(combo[0] == 5 for combo in trifectas)
    assert (5, 1, 2) in trifectas and (5, 2, 6) in trifectas and (5, 6, 1) in trifectas and (5, 3, 4) not in trifectas


def test_複勝_ワイド_3連複は_本命の複勝の見込みが線以上のレースだけ() -> None:
    low = FinalRule().decide(_scored(place_low=1.0))                    # 0.35 × 1.0
    assert not {PLACE, WIDE, TRIO} & set(low.tickets) and round(low.place_value, 2) == 0.35
    assert "複勝・ワイド・3連複: 見送り" in low.lines()[-1]
    high = FinalRule().decide(_scored(place_low=3.0))                   # 0.35 × 3.0
    assert high.tickets[PLACE] == ((5,),) and high.tickets[WIDE] == ((1, 5), (2, 5))
    assert len(high.tickets[TRIO]) == 7 and all(5 in combo and {1, 2} & set(combo) for combo in high.tickets[TRIO])


def test_頭数が足りなければ_理由つきのなし() -> None:
    bets = FinalRule().decide(_scored(heads=6))
    assert bets.empty and "6 頭" in bets.reason and bets.lines() == []


def test_通知の行は_印と券種ごとの組_ファイルに書いて読み戻せる(tmp_path: Path) -> None:
    bets = FinalRule().decide(_scored(), "11222040")
    lines = bets.lines()
    assert lines[0] == "◎5 ○1 ▲2 △3,4,6（1番人気 1 は ◎ にしない）"
    assert lines[1] == "単勝 5（1点 100円）" and lines[2] == "馬連 1−5 / 2−5（2点 200円）" and lines[3] == "馬単 5→1 / 5→2（2点 200円）"
    assert bets.yen == 100 * bets.points
    file, path = FinalBetFile(), tmp_path / "x.高知ファイナル.json"
    assert file.read(path) is None
    file.write(path, bets)
    assert file.read(path) == bets
    file.write(path, FinalBets.none("時系列オッズの断面がまだ無い"))
    assert file.read(path).reason == "時系列オッズの断面がまだ無い"
    file.clear(path)
    assert file.read(path) is None
