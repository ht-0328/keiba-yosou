"""LatePredictor（材料 → 直前の買い目）と LateBets・LateBetFile のテスト。モデルは偽物。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from 地方の直前の買い目 import late_columns as c
from 地方の直前の買い目.late_bet_file import LateBetFile
from 地方の直前の買い目.late_bets import LateBets
from 地方の直前の買い目.late_predictor import LatePredictor

from 地方の直前の買い目.testing.fake_models import FakeModels

RID = "2026111844120105"


def _snapshot(heads: int = 7) -> pd.DataFrame:
    numbers = list(range(1, heads + 1))
    return pd.DataFrame({c.HORSE_NO: numbers, c.ODDS_NOW: [2.0 * no for no in numbers], c.ODDS_A: [2.2 * no for no in numbers],
                         c.ODDS_B: [2.4 * no for no in numbers], c.ODDS_FIRST: [1.8 * no for no in numbers],
                         c.PLACE_LOW: [1.1 * no for no in numbers], c.PLACE_HIGH: [1.5 * no for no in numbers], "announced": "11181530"})


def _probabilities(heads: int = 7) -> pd.DataFrame:
    numbers = list(range(1, heads + 1))
    return pd.DataFrame({c.HORSE_NO: numbers, c.WIN_MODEL: [1 / heads] * heads, c.TOP3_MODEL: [3 / heads] * heads,
                         c.WIN_FREE: [1 / heads] * heads, c.TOP3_FREE: [3 / heads] * heads})


def test_線を満たす馬の単勝と_その馬を1着に固定した馬単と3連単() -> None:
    bets = LatePredictor(FakeModels({6: 0.5}, {6: 1.2})).bets(RID, _snapshot(), _probabilities())
    assert [pick.horse_no for pick in bets.picks] == [6] and bets.picks[0].opponents == (1, 2, 3, 4, 5)
    assert bets.announced == "11181530" and not bets.empty
    assert bets.lines() == ["単勝 6（決めたときの単勝 12.0倍）100円", "馬単 6 → 1,2（2点 200円）",
                            "3連単 6 → 1,2,3,4,5 → 1,2,3,4,5（20点 2,000円）"]


def test_線を満たす馬がいなければ_理由つきのなし() -> None:
    bets = LatePredictor(FakeModels({6: 0.5}, {6: 0.5})).bets(RID, _snapshot(), _probabilities())
    assert bets.empty and "線以上の馬がいない" in bets.reason and bets.announced == "11181530"


def test_線への近さは_買う馬がいてもいなくても付く_出せなかったレースは_None() -> None:
    bought = LatePredictor(FakeModels({6: 0.5}, {6: 1.2})).bets(RID, _snapshot(), _probabilities())
    assert round(bought.closeness, 3) == 1.25                         # min(0.5 / 0.4, 1.2 / 0.95)
    near = LatePredictor(FakeModels({6: 0.5}, {6: 0.76})).bets(RID, _snapshot(), _probabilities())
    assert near.empty and round(near.closeness, 3) == 0.8             # 0.76 / 0.95
    assert LateBets.from_dict(near.to_dict()) == LateBets((), near.reason, near.announced, 0.8)
    assert LatePredictor(FakeModels({}, {})).bets(RID, pd.DataFrame(), _probabilities()).closeness is None
    assert LateBets.from_dict({"買う馬": [], "理由": "前の形のファイル"}).closeness is None


def test_断面が無い_頭数が足りないときも_なし() -> None:
    predictor = LatePredictor(FakeModels({1: 1.0}, {1: 2.0}))
    assert "断面がまだ無い" in predictor.bets(RID, pd.DataFrame(), _probabilities()).reason
    assert "5 頭未満" in predictor.bets(RID, _snapshot(4), _probabilities(4)).reason


def test_材料は今のオッズと予想のそろった馬だけ_頭数はその数() -> None:
    snapshot = _snapshot()
    snapshot.loc[0, c.ODDS_NOW] = None
    material = LatePredictor.material(RID, snapshot, _probabilities().iloc[:6])
    assert material[c.HORSE_NO].tolist() == [2, 3, 4, 5, 6] and set(material[c.FIELD_SIZE]) == {5}
    assert set(material[c.RACE_DATE]) == {"2026-11-18"} and set(c.MATERIAL_COLUMNS) <= set(material.columns)


def test_ファイルに書いて読み直せる_無ければ_None_消せる(tmp_path: Path) -> None:
    bets = LatePredictor(FakeModels({6: 0.5}, {6: 1.2})).bets(RID, _snapshot(), _probabilities())
    path = tmp_path / "日" / f"{RID}.直前.json"
    file = LateBetFile()
    assert file.read(path) is None
    file.write(path, bets)
    assert file.read(path) == bets
    file.write(path, LateBets.none("理由"))
    assert file.read(path).reason == "理由"
    file.clear(path)
    assert file.read(path) is None
