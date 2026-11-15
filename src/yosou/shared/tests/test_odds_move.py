"""オッズの動きの直し（``yosou.shared.odds_move``・``EveOddsRepository``・``OddsMoveWeightsRepository``・``OddsMoveAdjustment``）のテスト。
値は架空。DB は合成DB だけを使う。"""

from __future__ import annotations

from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import pytest

from 共通 import keys
from 合成DB import synth

from ..dataset import PredictionData
from ..dataset.column_names import HORSE_NO, RACE_ID, WIN_ODDS
from ..odds_move import TARGET_TOP3, TARGET_WIN, OddsMoveCorrection, OddsMoveFeatures, OddsMoveFitter, OddsMoveWeights
from ..repository import EveOddsRepository, OddsMoveWeightsRepository
from ..workflow.odds_move_adjustment import OddsMoveAdjustment


def test_材料は_動き_動きとlogオッズの積_前日のオッズがあるか() -> None:
    x = OddsMoveFeatures().matrix(pd.Series([5.0, 10.0, 3.0, 50.0]), pd.Series([10.0, None, 3.0, 1.0]))
    assert x[0] == pytest.approx([np.log(0.5), np.log(0.5) * np.log(5.0), 1.0])   # 前日 10倍 → 今 5倍（売れた）
    assert list(x[1]) == [0.0, 0.0, 0.0]                                            # 前日のオッズが無い
    assert list(x[2]) == pytest.approx([0.0, 0.0, 1.0])                             # 動かない
    assert x[3][0] == pytest.approx(1.5)                                            # 大きな動きは ±1.5 で切る


def test_重みで直し_1着はレースの中で合計1にそろえる() -> None:
    weights = OddsMoveWeights(0.0, -0.5, 0.0, 0.0)   # 売れた馬（動きが負）を上げる
    correction = OddsMoveCorrection({TARGET_TOP3: weights, TARGET_WIN: weights})
    probability = pd.Series([0.3, 0.3, 0.3], name="p")
    win_odds, eve_odds = pd.Series([4.0, 4.0, 4.0]), pd.Series([8.0, 4.0, 2.0])
    top3 = correction.top3(probability, win_odds, eve_odds)
    assert top3[0] > 0.3 and top3[1] == pytest.approx(0.3) and top3[2] < 0.3 and top3.name == "p"
    win = correction.win(probability, win_odds, eve_odds)
    assert win.sum() == pytest.approx(1.0) and win[0] > win[1] > win[2]


def test_重みの無い目的は直さない() -> None:
    probability = pd.Series([0.2, 0.5])
    correction = OddsMoveCorrection({})
    assert correction.top3(probability, pd.Series([2.0, 3.0]), pd.Series([4.0, 3.0])) is probability
    assert correction.win(probability, pd.Series([2.0, 3.0]), pd.Series([4.0, 3.0])).tolist() == [0.2, 0.5]


def test_学ぶと_売れた馬が来やすいデータでは動きの重みが負になる() -> None:
    rng = np.random.default_rng(0)
    eve = rng.uniform(2, 30, 20000)
    move = rng.normal(0, 0.3, 20000)
    now = eve * np.exp(move)
    base = np.clip(1 / now, 0.01, 0.9)
    truth = 1 / (1 + np.exp(-(np.log(base / (1 - base)) - 1.0 * move)))
    hits = (rng.uniform(size=20000) < truth).astype(float)
    weights = OddsMoveFitter().fit(OddsMoveFeatures().matrix(pd.Series(now), pd.Series(eve)), hits, base)
    assert weights.move + weights.move_by_log_odds * np.log(10) < -0.5


def test_重みのファイルを書いて読める(tmp_path: Path) -> None:
    repository = OddsMoveWeightsRepository(tmp_path)
    assert repository.load() == {}
    saved = {TARGET_TOP3: OddsMoveWeights(0.1, -0.2, -0.03, 0.004), TARGET_WIN: OddsMoveWeights(0.0, 0.01, -0.04, 0.0)}
    repository.save(saved)
    assert repository.load() == saved
    assert b"\r\n" not in repository.path.read_bytes()


@pytest.fixture(scope="module")
def eve_db(tmp_path_factory) -> tuple[Path, str]:
    """1レースに、前日の途中の単勝オッズを2つ（15:00 と 18:00）と、当日の途中の断面（11:00）と確定を入れた合成DB。"""
    sample = synth.simple_race()
    ra = sample.ra[0]
    day = ra["開催月日"]
    eve = f"{int(day) - 1:04d}"
    for stage, announced, tenths in (("1", f"{eve}1500", 100), ("1", f"{eve}1800", 80), ("1", f"{day}1100", 50), ("5", "00000000", 40)):
        sample.odds.append(("o1", synth.odds_header(ra, "o1", stage=stage, announced=announced)))
        sample.odds.append(("o1__単勝オッズ", synth.odds_row(ra, "o1__単勝オッズ", "03", tenths, announced=announced)))
        sample.odds.append(("o1__単勝オッズ", synth.odds_row(ra, "o1__単勝オッズ", "05", 0, seq=2, announced=announced)))  # 無投票
    path = synth.build_db(tmp_path_factory.mktemp("eve") / "eve.duckdb", sample)
    return path, "".join(ra[column] for column in keys.RACE_KEY)


def test_前日の最後の途中のオッズを読み_当日の断面と確定と無投票は使わない(eve_db) -> None:
    path, race_id = eve_db
    con = duckdb.connect(str(path), read_only=True)
    eve = EveOddsRepository(con).read(race_id)
    assert eve.to_dict("records") == [{"horse_no": 3, "eve_odds": pytest.approx(8.0)}]   # 前日 18:00 の 8.0倍
    assert EveOddsRepository(con).read("2024040601010199").empty


def test_予測用データの馬番で前日のオッズを引いて直す() -> None:
    ids = pd.DataFrame({RACE_ID: ["R1", "R1"], HORSE_NO: [3, 5]})
    data = PredictionData(ids, pd.DataFrame({WIN_ODDS: [4.0, 4.0]}), None, None)
    reader = lambda race_id: pd.DataFrame({"horse_no": [3], "eve_odds": [8.0]})   # noqa: E731
    adjustment = OddsMoveAdjustment(OddsMoveCorrection({TARGET_TOP3: OddsMoveWeights(0.0, -0.5, 0.0, 0.0)}), reader)
    corrected = adjustment.top3(pd.Series([0.3, 0.3]), data)
    assert corrected[0] > 0.3 and corrected[1] == pytest.approx(0.3)   # 5番は前日のオッズが無いので切片だけ（0）
    no_odds = PredictionData(ids, pd.DataFrame({"x": [1, 2]}), None, None)
    assert adjustment.top3(pd.Series([0.3, 0.3]), no_odds).tolist() == [0.3, 0.3]
